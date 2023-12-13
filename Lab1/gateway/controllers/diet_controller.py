from icecream import ic
from cachetools import TTLCache
from flask import jsonify, request, Blueprint, current_app
import concurrent.futures

import os
from os.path import join, dirname
from dotenv import load_dotenv

import grpc
from google.protobuf.json_format import MessageToJson
import diet_pb2_grpc
import diet_pb2
import registration_pb2_grpc
import registration_pb2
from google.protobuf import empty_pb2

import requests

from pymemcache.client import base, retrying
from pymemcache.exceptions import MemcacheUnexpectedCloseError
from uhashring import HashRing

from circuitbreaker import circuit, CircuitBreakerMonitor


dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path)

diet_controller = Blueprint('diet_controller', __name__)

# diet_host = os.environ.get('DIET_HOST')
COORDINATOR_URL = os.environ.get('COORDINATOR_URL')
cache = TTLCache(maxsize=1000, ttl=360)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)

ERROR_THRESHOLD = 3
error_count = {}


discovery_channel = grpc.insecure_channel(os.environ.get('SD_URL'))
ic(os.environ.get('SD_URL'))
discovery_stub = registration_pb2_grpc.RegistrationServiceStub(discovery_channel)


nodes = ['memcached1:11211', 'memcached2:11211', 'memcached3:11211']
hash_ring = HashRing(nodes)

def create_memcached_client(target_node):
    try:
        memcached_client = base.Client(target_node)
        ic(f'Created memcached client for {target_node}')
        return memcached_client
    except Exception as error:
        ic(error)
        hash_ring.remove_node(target_node)
        return None

def get_from_cache(key):
    target_node = hash_ring.get_node(key)
    memcached_client = create_memcached_client(target_node)
    # memcached_client = base.Client(target_node)
    if memcached_client is None:
        ic(f'The target node: {target_node} is not active')
        return None
    # ic(f'Data retrieved successfully from cache on server {target_node} for key: {key}')
    try:
        data = memcached_client.get(key)
    except Exception as error:
        ic(error)
        data = None
        hash_ring.remove_node(target_node)

    memcached_client.close()

    if data is not None:
        ic(f"Data retrieved successfully from cache on server {target_node} for key: {key}")
        ic(hash_ring.nodes)
        if 'memcached1:11211' in hash_ring.nodes:
            hash_ring.remove_node('memcached1:11211')
        return data
    else:
        ic(f"Data not found in cache on server {target_node} for key: {key}")
        return None



def set_in_cache(key, value):
    
    target_node = hash_ring.get_node(key)
    memcached_client = base.Client(target_node)

    memcached_client.set(key, value, expire=100)
    ic(f'Data set successfully in cache on server {target_node} for key: ${key}')



def delete_from_cache(key):
    target_node = hash_ring.get_node(key)
    memcached_client = base.Client(target_node)

    memcached_client.delete(key)
    ic(f'Data deleted successfully from cache on server {target_node} for key: {key}')

   
def list_registered_services():
    request = empty_pb2.Empty()

    response = discovery_stub.ListRegisteredServices(request)
    ic(response.services)
    # initialize error count for each service to 0 if not already initialized
    global error_count
    for service in response.services:
        if service.host not in error_count:
            error_count[service.host] = 0
    ic(error_count)
    return response.services

    
last_selected_index = 0

def get_round_robin_service(service_name):
    global last_selected_index
    
    services = list_registered_services()
    ic(services)
    ic(error_count)
    # Filter services based on eligibility criteria
    eligible_services = [x for x in services if x.name == service_name and error_count[x.host] < 3]
    
    ic(eligible_services)

    if len(eligible_services) == 0:
        ic('No active service instance found')
        return None

    # Use modulo to wrap around the index and achieve round-robin selection

    selected_index = last_selected_index % len(eligible_services)
    last_selected_index += 1
    
    ic(eligible_services[selected_index].host)

    return eligible_services[selected_index]



def handle_error(service, diet_id):

    if service is None:
        return {'error': 'No active service instance found'}

    # redirect the request to another service instance
    error_count[service.host] += 1
    ic(error_count)
    ic('Redirecting request to another service instance')
    get_diet_protected(diet_id)


def create_diet_object(data):
    return diet_pb2.Diet(
        id=data['diet']['id'],
        user_id=data['diet']['user_id'],
        name=data['diet']['name'],
        description=data['diet']['description'],
        foods=[
            diet_pb2.Food(
                id=food['id'],
                name=food['name'],
                description=food.get('description', ''),
                calories=food.get('calories', 0),
                repetitions=food.get('repetitions', 0),
            )
            for food in data['diet']['foods']
        ],
    )


def get_diet_status_protected():
    circuits = CircuitBreakerMonitor.get_circuits()
    ic(circuits)

    try:
        ic("--------------------")
        service = get_round_robin_service('DietPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        status_stub = diet_pb2_grpc.StatusStub(channel)

        request = diet_pb2.GetStatusRequest()
        response = status_stub.GetStatus(request, timeout=6)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        return response
    except grpc.RpcError as e:
        ic(e)

        return e.details()


@diet_controller.route('/diet_status', methods=['GET'])
def get_diet_status():
    future = executor.submit(get_diet_status_protected)

    return future.result()


def post_diet_protected(data):
    delete_from_cache(f"diets_user_{data['diet']['user_id']}")

    diet = create_diet_object(data)
    ic(diet)

    try:
        service = get_round_robin_service('DietPlan')
        
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.CreateDietRequest(diet=diet)
        response = diet_stub.CreateDiet(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        return response
    except grpc.RpcError as e:
        return e.details()


@diet_controller.route('/diet', methods=['POST'])
def post_diet():
    future = executor.submit(post_diet_protected, request.get_json())

    return future.result()


def get_diet_protected(diet_id):
    cache_key = f'diet_{diet_id}'
    # cache_value = cache.get(cache_key)
    cache_value = get_from_cache(cache_key)
    ic(cache_value)

    if cache_value:
        return cache_value
    
    ic('-------------------')
    service = get_round_robin_service('DietPlan')
    ic(f'Redirect to {service}')
    ic(service)
    if service is None:
        ic('No active service instance found')
        # return jsonify({'error': 'No active service instance found'}), 500

    try:
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadDietRequest(diet_id=diet_id)
        response = diet_stub.ReadDiet(request, timeout=3)

        response = MessageToJson(response, preserving_proto_field_name=True)

        ic('Set in cache')

        set_in_cache(cache_key, response)

        return response
    except Exception as e:
        ic(e)
        handle_error(service, diet_id)
        ic('No active service instance found')
        return "No active service instance found"



@diet_controller.route('/diet/<diet_id>', methods=['GET'])
def get_diet(diet_id):
    future = executor.submit(get_diet_protected, diet_id)
    return future.result()


def get_diets_protected(user_id):
    cache_key = f'diets_user_{user_id}'
    cache_value = get_from_cache(cache_key)
    # ic(cache)

    if cache_value:
        return cache_value

    try:
        service = get_round_robin_service('DietPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadAllDietsRequest(user_id=user_id)
        response = diet_stub.ReadAllDiets(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        set_in_cache(cache_key, response)
        # cache[cache_key] = response

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


@diet_controller.route('/diets/<user_id>', methods=['GET'])
def get_diets(user_id):
    future = executor.submit(get_diets_protected, user_id)
    return future.result()


def put_diet_protected(data):
    # ic(cache)

    delete_from_cache(f"diet_{data['diet']['id']}")

    # ic(cache)

    diet = create_diet_object(data)
    ic(diet)

    try:
        service = get_round_robin_service('DietPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.UpdateDietRequest(diet=diet)
        response = diet_stub.UpdateDiet(request, timeout=5)

        ic(response)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['PUT'])
def put_diet(diet_id):
    future = executor.submit(put_diet_protected, request.get_json())
    return future.result()


def delete_diet_protected(diet_id, data):
    ic(cache)

    user_id = data['user_id']

    keys = [f'diets_user_{user_id}', f'diet_{diet_id}']

    for key in keys:
        if key in cache:
            cache.pop(key)

    ic(cache)

    try:
        service = get_round_robin_service('DietPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.DeleteDietRequest(diet_id=diet_id)
        response = diet_stub.DeleteDiet(request, timeout=5)

        response = MessageToJson(response, preserving_proto_field_name=True)
        ic(response)

        return response
    except grpc.RpcError as e:
        return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['DELETE'])
def delete_diet(diet_id):
    future = executor.submit(delete_diet_protected, diet_id, request.get_json())
    return future.result()

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


dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path)

diet_controller = Blueprint('diet_controller', __name__)

diet_host = os.environ.get('DIET_HOST')

cache = TTLCache(maxsize=1000, ttl=360)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)

ERROR_THRESHOLD = 3
error_count = 0
error_counts = {}

discovery_channel = grpc.insecure_channel(os.environ.get('SD_URL'))
ic(os.environ.get('SD_URL'))
discovery_stub = registration_pb2_grpc.RegistrationServiceStub(discovery_channel)


def list_registered_services():
    request = empty_pb2.Empty()

    response = discovery_stub.ListRegisteredServices(request)

    return response.services


def get_min_load_service():
    services = list_registered_services()
    ic(services)
    services = [x for x in services if x.name == 'DietPlan']
    services.sort(key=lambda x: x.load)
    ic(services)

    if not services:
        return None

    return services[0]


def handle_error(service):
    error_count = +1
    error_counts[f'{service.name}:{service.port}'] = error_count
    ic(error_counts)


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


def cleanup_cache(data):
    user_id = data['diet']['user_id']
    diet_id = data['diet']['id']
    ic(user_id)
    ic(diet_id)
    keys = [f'diets_user_{user_id}', f'diet_{diet_id}']

    for key in keys:
        if key in cache:
            cache.pop(key)

    return


def get_diet_status_protected():
    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
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

    cleanup_cache(data)

    diet = create_diet_object(data)
    ic(diet)

    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.CreateDietRequest(diet=diet)
        response = diet_stub.CreateDiet(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        return response
    except grpc.RpcError as e:
        handle_error(service)
        return e.details()


@diet_controller.route('/diet', methods=['POST'])
def post_diet():
    future = executor.submit(post_diet_protected, request.get_json())

    return future.result()


def get_diet_protected(diet_id):

    cache_key = f'diet_{diet_id}'
    cache_value = cache.get(cache_key)

    if cache_value:
        return cache_value

    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadDietRequest(diet_id=diet_id)
        response = diet_stub.ReadDiet(request, timeout=3)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        cache[cache_key] = response

        return response
    except grpc.RpcError as e:
        handle_error()
        return e.details(), 500


@diet_controller.route('/diet/<diet_id>', methods=['GET'])
def get_diet(diet_id):
    future = executor.submit(get_diet_protected, diet_id)
    return future.result()


def get_diets_protected(user_id):
    cache_key = f'diets_user_{user_id}'
    cache_value = cache.get(cache_key)
    ic(cache)

    if cache_value:
        return cache_value

    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadAllDietsRequest(user_id=user_id)
        response = diet_stub.ReadAllDiets(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        cache[cache_key] = response

        ic(cache)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


@diet_controller.route('/diets/<user_id>', methods=['GET'])
def get_diets(user_id):
    future = executor.submit(get_diets_protected, user_id)
    return future.result()


def put_diet_protected(data):
    ic(cache)

    cleanup_cache(data)

    ic(cache)

    diet = create_diet_object(data)
    ic(diet)

    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
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
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{diet_host}:{service.port}')
        diet_stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.DeleteDietRequest(diet_id=diet_id)
        response = diet_stub.DeleteDiet(request, timeout=5)

        response = MessageToJson(response, preserving_proto_field_name=True)
        ic(response)

        return response
    except grpc.RpcError as e:
        handle_error(service)
        ic(service)
        return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['DELETE'])
def delete_diet(diet_id):
    future = executor.submit(delete_diet_protected, diet_id, request.get_json())
    return future.result()

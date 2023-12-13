from icecream import ic
from cachetools import TTLCache
from flask import jsonify, request, Blueprint, current_app
import concurrent.futures

import os
from os.path import join, dirname
from dotenv import load_dotenv

import grpc
from google.protobuf.json_format import MessageToJson
import workout_pb2_grpc
import workout_pb2
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

workout_controller = Blueprint('workout_controller', __name__)

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
        if 'memcached3:11211' in hash_ring.nodes:
            hash_ring.remove_node('memcached3:11211')
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



def handle_error(service, workout_id):

    if service is None:
        return {'error': 'No active service instance found'}

    # redirect the request to another service instance
    error_count[service.host] += 1
    ic(error_count)
    ic('Redirecting request to another service instance')
    get_workout_protected(workout_id)


def create_workout_object(data):
    return workout_pb2.Workout(
        id=data['workout']['id'],
        user_id=data['workout']['user_id'],
        name=data['workout']['name'],
        description=data['workout']['description'],
        exercises=[
            workout_pb2.Exercise(
                id=exercise['id'],
                name=exercise['name'],
                description=exercise.get('description', ''),
                sets=exercise.get('sets', 0),
                repetitions=exercise.get('repetitions', 0),
            )
            for exercise in data['workout']['exercises']
        ],
    )


@workout_controller.route('/workout-and-diet', methods=['POST'])
def create_workout_and_diet():

    ic('-------------------')
    # List registered services to identify service instances
    workout_service = get_round_robin_service('WorkoutPlan') 
    ic(workout_service)
    if(workout_service):
        request.json['workoutServiceAddress'] = f"{workout_service.host}:{workout_service.port}"
    else:
        request.json['workoutServiceAddress'] = f'{None}:{None}'
        
    diet_service = get_round_robin_service('DietPlan')
    ic(diet_service)
    if(diet_service):
        request.json['dietServiceAddress'] = f"{diet_service.host}:{diet_service.port}"
    else:
        request.json['workoutServiceAddress'] = f'{None}:{None}'

    try:
        # Step 1: Start the saga transaction in the coordinator
        saga_response = requests.post(f'http://{COORDINATOR_URL}/start-saga', json=request.json)

        # Step 2: Check if the saga transaction was successful
        # if saga_response.json()['message'] == 'Saga transaction completed successfully':
        #     # Step 3: Return a response to the client indicating success
        #     return jsonify({'message': 'Workout and Diet creation initiated successfully'})
        # else:
        #     # Step 4: Return a response to the client indicating failure
        #     return jsonify({'error': 'Saga transaction failed'}), 500
        return saga_response.json()
    except Exception as error:
        print('Error in gateway:', error)
        return jsonify({'error': 'Failed to initiate Workout and Diet creation'}), 500


def get_workout_status_protected():
    circuits = CircuitBreakerMonitor.get_circuits()
    ic(circuits)

    try:
        ic("--------------------")
        service = get_round_robin_service('WorkoutPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        status_stub = workout_pb2_grpc.StatusStub(channel)

        request = workout_pb2.GetStatusRequest()
        response = status_stub.GetStatus(request, timeout=6)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        return response
    except grpc.RpcError as e:
        ic(e)

        return e.details()


@workout_controller.route('/workout_status', methods=['GET'])
def get_workout_status():
    future = executor.submit(get_workout_status_protected)

    return future.result()


def post_workout_protected(data):
    delete_from_cache(f"workouts_user_{data['workout']['user_id']}")

    workout = create_workout_object(data)
    ic(workout)

    try:
        service = get_round_robin_service('WorkoutPlan')
        
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.CreateWorkoutRequest(workout=workout)
        response = workout_stub.CreateWorkout(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        return response
    except grpc.RpcError as e:
        return e.details()


@workout_controller.route('/workout', methods=['POST'])
def post_workout():
    future = executor.submit(post_workout_protected, request.get_json())

    return future.result()


def get_workout_protected(workout_id):
    cache_key = f'workout_{workout_id}'
    # cache_value = cache.get(cache_key)
    cache_value = get_from_cache(cache_key)
    ic(cache_value)

    if cache_value:
        return cache_value
    
    ic('-------------------')
    service = get_round_robin_service('WorkoutPlan')
    ic(f'Redirect to {service}')
    ic(service)
    if service is None:
        ic('No active service instance found')
        # return jsonify({'error': 'No active service instance found'}), 500

    try:
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.ReadWorkoutRequest(workout_id=workout_id)
        response = workout_stub.ReadWorkout(request, timeout=3)

        response = MessageToJson(response, preserving_proto_field_name=True)

        ic('Set in cache')

        set_in_cache(cache_key, response)

        return response
    except Exception as e:
        ic(e)
        handle_error(service, workout_id)
        ic('No active service instance found')
        return "No active service instance found"



@workout_controller.route('/workout/<workout_id>', methods=['GET'])
def get_workout(workout_id):
    future = executor.submit(get_workout_protected, workout_id)
    return future.result()


def get_workouts_protected(user_id):
    cache_key = f'workouts_user_{user_id}'
    cache_value = get_from_cache(cache_key)
    # ic(cache)

    if cache_value:
        return cache_value

    try:
        service = get_round_robin_service('WorkoutPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.ReadAllWorkoutsRequest(user_id=user_id)
        response = workout_stub.ReadAllWorkouts(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        set_in_cache(cache_key, response)
        # cache[cache_key] = response

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


@workout_controller.route('/workouts/<user_id>', methods=['GET'])
def get_workouts(user_id):
    future = executor.submit(get_workouts_protected, user_id)
    return future.result()


def put_workout_protected(data):
    # ic(cache)

    delete_from_cache(f"workout_{data['workout']['id']}")

    # ic(cache)

    workout = create_workout_object(data)
    ic(workout)

    try:
        service = get_round_robin_service('WorkoutPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.UpdateWorkoutRequest(workout=workout)
        response = workout_stub.UpdateWorkout(request, timeout=5)

        ic(response)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


@workout_controller.route('/workout/<workout_id>', methods=['PUT'])
def put_workout(workout_id):
    future = executor.submit(put_workout_protected, request.get_json())
    return future.result()


def delete_workout_protected(workout_id, data):
    ic(cache)

    user_id = data['user_id']

    keys = [f'workouts_user_{user_id}', f'workout_{workout_id}']

    for key in keys:
        if key in cache:
            cache.pop(key)

    ic(cache)

    try:
        service = get_round_robin_service('WorkoutPlan')
        channel = grpc.insecure_channel(f'{service.host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.DeleteWorkoutRequest(workout_id=workout_id)
        response = workout_stub.DeleteWorkout(request, timeout=5)

        response = MessageToJson(response, preserving_proto_field_name=True)
        ic(response)

        return response
    except grpc.RpcError as e:
        return e.details()


@workout_controller.route('/workout/<workout_id>', methods=['DELETE'])
def delete_workout(workout_id):
    future = executor.submit(delete_workout_protected, workout_id, request.get_json())
    return future.result()

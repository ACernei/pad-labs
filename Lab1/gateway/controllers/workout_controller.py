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

from pymemcache.client import base, retrying
from pymemcache.exceptions import MemcacheUnexpectedCloseError
from uhashring import HashRing

from circuitbreaker import circuit, CircuitBreakerMonitor


dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path)

workout_controller = Blueprint('workout_controller', __name__)

workout_host = os.environ.get('WORKOUT_HOST')

cache = TTLCache(maxsize=1000, ttl=360)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)

ERROR_THRESHOLD = 3
error_count = 0
error_counts = {}


discovery_channel = grpc.insecure_channel(os.environ.get('SD_URL'))
ic(os.environ.get('SD_URL'))
discovery_stub = registration_pb2_grpc.RegistrationServiceStub(discovery_channel)


nodes = ['memcached1:11211', 'memcached2:11211', 'memcached3:11211']
hash_ring = HashRing(nodes)



def get_from_cache(key):
    target_node = hash_ring.get_node(key)
    memcached_client = base.Client(target_node)

    ic(f'Data retrieved successfully from cache on server {target_node} for key: {key}')
    return memcached_client.get(key)



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

    return response.services


def get_min_load_service():
    services = list_registered_services()

    services = [x for x in services if x.name == 'WorkoutPlan']
    services.sort(key=lambda x: x.load)
    ic(services)

    if not services:
        return None

    return services[0]


# def handle_error(service):
#     error_count = error_count + 1
#     error_counts[f'{service.name}:{service.port}'] = error_count
#     ic(error_counts)


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


# def cleanup_cache(data):
#     user_id = data['workout']['user_id']
#     workout_id = data['workout']['id']
#     ic(user_id)
#     ic(workout_id)
#     keys = [f'workouts_user_{user_id}', f'workout_{workout_id}']

#     base_client.delete(keys)
#     return

@circuit
def get_workout_status_protected():
    circuits = CircuitBreakerMonitor.get_circuits()
    ic(circuits)

    # try:
    service = get_min_load_service()
    channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
    status_stub = workout_pb2_grpc.StatusStub(channel)

    request = workout_pb2.GetStatusRequest()
    response = status_stub.GetStatus(request, timeout=6)

    response = MessageToJson(response, preserving_proto_field_name=True)

    waiting_tasks = executor._work_queue.qsize()
    ic(waiting_tasks)

    return response
    # except grpc.RpcError as e:
    #     ic(e)

    #     return e.details()


@circuit
@workout_controller.route('/workout_status', methods=['GET'])
def get_workout_status():
    future = executor.submit(get_workout_status_protected)
    return future.result()


def post_workout_protected(data):
    nr_of_circuits = len(list(CircuitBreakerMonitor.get_open()))
    ic(nr_of_circuits)

    delete_from_cache(f"workouts_user_{data['workout']['user_id']}")

    workout = create_workout_object(data)
    ic(workout)

    # try:
    service = get_min_load_service()
    channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
    workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

    request = workout_pb2.CreateWorkoutRequest(workout=workout)
    response = workout_stub.CreateWorkout(request)

    response = MessageToJson(response, preserving_proto_field_name=True)

    return response
    # except grpc.RpcError as e:
    #     return e.details()


@circuit
@workout_controller.route('/workout', methods=['POST'])
def post_workout():
    future = executor.submit(post_workout_protected, request.get_json())

    return future.result()

@circuit
def get_workout_protected(workout_id):
    nr_of_circuits = len(list(CircuitBreakerMonitor.get_open()))
    ic(nr_of_circuits)

    cache_key = f'workout_{workout_id}'
    # cache_value = cache.get(cache_key)
    cache_value = get_from_cache(cache_key)

    if cache_value:
        return cache_value

    # try:
    service = get_min_load_service()
    channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
    workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

    request = workout_pb2.ReadWorkoutRequest(workout_id=workout_id)
    response = workout_stub.ReadWorkout(request, timeout=3)

    response = MessageToJson(response, preserving_proto_field_name=True)

    waiting_tasks = executor._work_queue.qsize()
    ic(waiting_tasks)
    set_in_cache(cache_key, response)
    # cache[cache_key] = response

    return response
    # except grpc.RpcError as e:
    #     handle_error()
    #     return e.details(), 500



@workout_controller.route('/workout/<workout_id>', methods=['GET'])
def get_workout(workout_id):
    ic('behehehe')
    future = executor.submit(get_workout_protected, workout_id)
    return future.result()


def get_workouts_protected(user_id):
    cache_key = f'workouts_user_{user_id}'
    cache_value = get_from_cache(cache_key)
    # ic(cache)

    if cache_value:
        return cache_value

    try:
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
        workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        request = workout_pb2.ReadAllWorkoutsRequest(user_id=user_id)
        response = workout_stub.ReadAllWorkouts(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        set_in_cache(cache_key, response)
        # cache[cache_key] = response

        # ic(cache)

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
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
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
        service = get_min_load_service()
        channel = grpc.insecure_channel(f'{workout_host}:{service.port}')
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

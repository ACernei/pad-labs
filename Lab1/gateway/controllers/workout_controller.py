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


dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path)

workout_controller = Blueprint('workout_controller', __name__)

cache = TTLCache(maxsize=1000, ttl=360)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)



discovery_channel = grpc.insecure_channel(f'localhost:{os.environ.get("SD_PORT")}')
ic(os.environ.get("SD_PORT"))
discovery_stub = registration_pb2_grpc.RegistrationServiceStub(discovery_channel)


def list_registered_services():
    request = empty_pb2.Empty()

    response = discovery_stub.ListRegisteredServices(request)

    return response.services


def get_workout_stub():

    services = list_registered_services()

    services = [x for x in services if x.name == 'WorkoutPlan']

    services.sort(key=lambda x:x.load)
    ic(services)

    if not services:
        return None

    channel = grpc.insecure_channel(f'localhost:{services[0].port}')
    workout_stub = workout_pb2_grpc.WorkoutCrudStub(channel)
    return workout_stub

def get_status_stub():
    services = list_registered_services()

    services = [x for x in services if x.name == 'WorkoutPlan']

    services.sort(key=lambda x:x.load)
    ic(services)

    if not services:
        return None
    
    channel = grpc.insecure_channel(f'localhost:{services[0].port}')
    status_stub = workout_pb2_grpc.StatusStub(channel)
    workout_crud_stub = workout_pb2_grpc.WorkoutCrudStub(channel)
    return status_stub


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
                description=exercise.get('description', ""),
                sets=exercise.get('sets', 0),
                repetitions=exercise.get('repetitions', 0)
            ) for exercise in data['workout']['exercises']
        ]
    )


def cleanup_cache(data):
    
    user_id = data['workout']['user_id']
    workout_id = data['workout']['id']
    ic(user_id)
    ic(workout_id)
    keys = [f"workouts_user_{user_id}", f'workout_{workout_id}']

    for key in keys:
        if key in cache:
            cache.pop(key)
    
    return


def get_workout_status_protected():
    try:
        stub = get_status_stub()

        request = workout_pb2.GetStatusRequest()
        response = stub.GetStatus(request, timeout=6)

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


@workout_controller.route('/workout', methods=['POST'])
def post_workout():
    ic(cache)

    workout_data = request.get_json()
    cleanup_cache(workout_data)
    
    ic(workout)
    
    workout = create_workout_object(workout_data)
 
    try:
        stub = get_workout_stub()
      
        w_request = workout_pb2.CreateWorkoutRequest(workout=workout)
        response = stub.CreateWorkout(w_request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()


def get_workout_protected(workout_id):
    cache_key = f"workout_{workout_id}"
    cache_value = cache.get(cache_key)
    # ic(cache)

    if cache_value:
        return cache_value

    try:
        stub = get_workout_stub()

        request = workout_pb2.ReadWorkoutRequest(workout_id=workout_id)        
        response = stub.ReadWorkout(request, timeout=6)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        cache[cache_key] = response

        # ic(cache)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details(), 500


@workout_controller.route('/workout/<workout_id>', methods=['GET'])
def get_workout(workout_id):
    future = executor.submit(get_workout_protected, workout_id)
    return future.result()


def get_workouts_protected(user_id):
    cache_key = f"workouts_user_{user_id}"
    cache_value = cache.get(cache_key)
    ic(cache)

    if cache_value:
        return cache_value

    try:
        stub = get_workout_stub()
        ic(stub)
        request = workout_pb2.ReadAllWorkoutsRequest(user_id=user_id)        
        response = stub.ReadAllWorkouts(request)

        response = MessageToJson(response, preserving_proto_field_name=True)

        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        cache[cache_key] = response

        ic(cache)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()

@workout_controller.route('/workouts/<user_id>', methods=['GET'])
def get_workouts(user_id):
    future = executor.submit(get_workouts_protected, user_id)
    return future.result()


def put_workout_protected(workout_id):
    
    ic(cache)

    workout_data = request.get_json()
    cleanup_cache(workout_data)

    ic(cache)

    workout = create_workout_object(workout_data)
    
    try:
        stub = get_workout_stub()

        w_request = workout_pb2.UpdateWorkoutRequest(workout=workout)
        response = stub.UpdateWorkout(w_request)

        response = MessageToJson(response, preserving_proto_field_name=True)
    
        waiting_tasks = executor._work_queue.qsize()
        ic(waiting_tasks)

        return response
    except grpc.RpcError as e:
        ic(e)
        return e.details()

@workout_controller.route('/workout/<workout_id>', methods=['PUT'])
def put_workout(workout_id):
    future = executor.submit(put_workout_protected, workout_id)
    return future.result()


def delete_workout_protected(workout_id):
    ic(cache)

    workout_data = request.get_json()
    user_id = workout_data['user_id']

    keys = [f"workouts_user_{user_id}", f'workout_{workout_id}']

    for key in keys:
        if key in cache:
            cache.pop(key)

    ic(cache)

    try:
        stub = get_workout_stub()

        w_request = workout_pb2.DeleteWorkoutRequest(workout_id=workout_id)    
        response = stub.DeleteWorkout(w_request, timeout=5)

        response = MessageToJson(response, preserving_proto_field_name=True)
        ic(response)

        return response
    except grpc.RpcError as key:
        ic(e)
        return key.details()

@workout_controller.route('/workout/<workout_id>', methods=['DELETE'])
def delete_workout(workout_id):
    future = executor.submit(delete_workout_protected, workout_id)
    return future.result()
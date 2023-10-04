import logging

import grpc
import workout_pb2_grpc
import workout_pb2
from flask import Flask, jsonify, request

app = Flask(__name__)

def check_service_status():
    try:
        # Connect to the gRPC server
        channel = grpc.insecure_channel('localhost:5135')   
        stub = workout_pb2_grpc.StatusStub(channel)

        # Create an empty request
        request = workout_pb2.Empty()

        # Make the gRPC call to check the status
        response = stub.CheckStatus(request)

        return response.status

    except Exception as e:
        return str(e)

@app.route('/gateway_status', methods=['GET'])
def get_gateway_status():
    return jsonify({"status": "Gateway is up and running"})

# @app.route('/say_hello', methods=['GET'])
# def say_hello():
#     try:
#         # Connect to the gRPC server
#         channel = grpc.insecure_channel('localhost:5135')
#         stub = workout_pb2_grpc.StatusStub(channel)

#         # Extract data from the HTTP request
#         name = 'Andrei'

#         # Make the gRPC call
#         response = stub.SayHello(workout_pb2.HelloRequest(name=name), timeout=3)
#         print(response)
#         # Return the gRPC response as JSON
#         return jsonify({"message": response.message})

#     except Exception as e:
#         return jsonify({"error": str(e)})

@app.route('/status', methods=['GET'])
def get_status():
    try:
        # Check the service status
        service_status = check_service_status()

        # Return the service status as a JSON response
        return jsonify({"status": service_status})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/workout', methods=['POST'])
def read_all_workouts_plan():
    try:
        # Connect to the gRPC server
        channel = grpc.insecure_channel('localhost:5135')
        stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        # Extract data from the HTTP request

        # Create an Exercise
        exercise = workout_pb2.Exercise(
            name='Bicep Curls',
            description='Bicep Curls description',
            sets=3,
            repetitions=12
        )

        # Create a Workout with the Exercise
        workout = workout_pb2.Workout(
            id='asd',
            user_id='fgh',
            name='Biceps',
            description='Biceps description',
            exercises=[exercise]
        )

        # Create a CreateWorkoutRequest and send it to the server
        request = workout_pb2.CreateWorkoutRequest(workout=workout)
        response = stub.CreateWorkout(request, timeout=100)
        # Make the gRPC call
        # response = stub.CreateWorkout(workout_pb2.CreateWorkoutRequest(id='asd', user_id = 'fgh', name = 'Biceps', description = 'Biceps description', exercises = [id = 'qw', na]), timeout=3)
        print(response.name)
        # Return the gRPC response as JSON
        return jsonify({"message": response.message})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/workouts', methods=['GET'])
def read_all_workouts():
    try:
        # Connect to the gRPC server
        channel = grpc.insecure_channel('localhost:5135')
        stub = workout_pb2_grpc.WorkoutCrudStub(channel)

        # Extract data from the HTTP request
        user_id = '1'

        # Make the gRPC call
        response = stub.ReadAllWorkouts(workout_pb2.ReadAllWorkoutsRequest(user_id=user_id), timeout=3)
        print(response)
        # Return the gRPC response as JSON
        return jsonify({"message": response.message})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    logging.basicConfig()
    app.run(port=8080)
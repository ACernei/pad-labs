from icecream import ic

from flask import Flask, jsonify, request
import concurrent.futures

import grpc
from google.protobuf.json_format import MessageToJson
import workout_pb2_grpc
import workout_pb2
import diet_pb2_grpc
import diet_pb2

from google.protobuf import empty_pb2

from dotenv import load_dotenv
import os
from os.path import join, dirname


dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path)

PORT = os.environ.get('PORT')
HOST = os.environ.get('HOST')

app = Flask(__name__)

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

def commit_transaction(workout_service_client, diet_service_client, transaction_id):
    workout_message = workout_pb2.Transaction(transaction_id=transaction_id)
    workout_service_client.CommitTransaction(workout_message)

    print('Workout service transaction committed successfully')

    diet_message = diet_pb2.Transaction(transaction_id=transaction_id)
    diet_service_client.CommitTransaction(diet_message)

    print('Diet service transaction committed successfully')

def rollback_transaction(workout_service_client, diet_service_client, transaction_id):
    try:
        workout_message = workout_pb2.Transaction(transaction_id=transaction_id)
        workout_service_client.RollbackTransaction(workout_message)

        ic('Workout service transaction rolled back successfully')
    except Exception as error:
        ic('Error in rolling back workout service transaction:')

    try:
        diet_message = diet_pb2.Transaction(transaction_id=transaction_id)
        diet_service_client.RollbackTransaction(diet_message)

        ic('Diet service transaction rolled back successfully')
    except Exception as error:
        ic('Error in rolling back diet service transaction:')


# @app.route('/health', methods=['POST'])
# def health():
#     print('Saga transaction started')
#     workout_service_address = request.json['workoutServiceAddress']
#     diet_service_address = request.json['dietServiceAddress']
#     print(workout_service_address)
#     print(diet_service_address)
#     return jsonify({'message': 'Saga transaction started'}), 200

@app.route('/start-saga', methods=['POST'])
def start_saga():
    ic('Saga transaction started')
    workout_service_address = request.json['workoutServiceAddress']
    diet_service_address = request.json['dietServiceAddress']
    ic(workout_service_address)
    ic(diet_service_address)

    workout_service_channel = grpc.insecure_channel(workout_service_address)
    diet_service_channel = grpc.insecure_channel(diet_service_address)

    workout_service_client = workout_pb2_grpc.WorkoutCrudStub(workout_service_channel)
    diet_service_client = diet_pb2_grpc.DietCrudStub(diet_service_channel)

    transaction_id = "789456123"

    try:
        ic(transaction_id)
        workout = create_workout_object(request.get_json())
        ic(workout)
        diet = create_diet_object(request.get_json())
        ic(diet)

        # Step 2: Make gRPC requests to the services
        workout_message = workout_pb2.ValidationRequest(transaction_id=transaction_id, workout=workout)
        workout_service_client.ValidateTransaction(workout_message)

        ic('Workout service request completed successfully')

        diet_message = diet_pb2.ValidationRequest(transaction_id=transaction_id, diet=diet)
        diet_service_client.ValidateTransaction(diet_message)

        ic('Diet service request completed successfully')

        # Step 3: Commit the transaction
        ic('Saga transaction completed successfully')
        commit_transaction(workout_service_client, diet_service_client, transaction_id)

        return jsonify({'message': 'Saga transaction completed successfully'}), 200
    except Exception as error:
        ic('Error in saga transaction:', error)

        # Step 4: Handle rollback in case of failure
        if transaction_id:
            rollback_transaction(workout_service_client, diet_service_client, transaction_id)

        return jsonify({'error': 'Saga transaction failed'}), 200

    
if __name__ == '__main__':
    app.run(port=PORT, host=HOST)

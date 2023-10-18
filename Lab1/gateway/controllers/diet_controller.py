from icecream import ic
from cachetools import TTLCache
from flask import jsonify, request, Blueprint

import grpc
from google.protobuf.json_format import MessageToJson
import diet_pb2_grpc
import diet_pb2

diet_controller = Blueprint('diet_controller', __name__)

cache = TTLCache(maxsize=1000, ttl=360)


def check_diet_service_status():
    cached_response = cache.get("diet_service_status")
    ic(cache)

    if cached_response:
        return cached_response
    
    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.StatusStub(channel)

        request = diet_pb2.GetStatusRequest()
        response = stub.GetStatus(request)

        cache["diet_service_status"] = response.status

        return response.status

    except grpc.RpcError as e:
            return e.details()


@diet_controller.route('/diet_status', methods=['GET'])
def get_diet_status():
    service_status = check_diet_service_status()

    return jsonify({"status": service_status})
    

@diet_controller.route('/diet', methods=['POST'])
def post_diet():
    diet_data = request.get_json()
    ic(diet_data)

    # Create a Diet object using the "diet" data
    diet = diet_pb2.Diet(
        id=diet_data['diet']['id'],
        user_id=diet_data['diet']['user_id'],
        name=diet_data['diet']['name'],
        description=diet_data['diet']['description'],
        foods=[
            diet_pb2.Food(
                id=food['id'],
                name=food['name'],
                description=food.get('description', ""),
                calories=food.get('calories', 0),
                repetitions=food.get('repetitions', 0)
            ) for food in diet_data['diet']['foods']
        ]
    )

    ic(diet)

    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.DietCrudStub(channel)

        d_request = diet_pb2.CreateDietRequest(diet=diet)
        d_response = stub.CreateDiet(d_request)

        return MessageToJson(d_response, preserving_proto_field_name=True)
    except grpc.RpcError as e:
        return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['GET'])
def get_diet(diet_id):
    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadDietRequest(diet_id=diet_id)        
        response = stub.ReadDiet(request)
        ic(response)

        return MessageToJson(response, preserving_proto_field_name=True)
    except grpc.RpcError as e:
            return e.details()


@diet_controller.route('/diets/<user_id>', methods=['GET'])
def get_diets(user_id):
    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.ReadAllDietsRequest(user_id=user_id)        
        response = stub.ReadAllDiets(request)
        ic(response)

        return MessageToJson(response, preserving_proto_field_name=True)
    except grpc.RpcError as e:
            return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['PUT'])
def put_diet(diet_id):
    diet_data = request.get_json()

    # Create a Diet object using the "diet" data
    diet = diet_pb2.Diet(
        id=diet_data['diet']['id'],
        user_id=diet_data['diet']['user_id'],
        name=diet_data['diet']['name'],
        description=diet_data['diet']['description'],
        foods=[
            diet_pb2.Food(
                id=food['id'],
                name=food['name'],
                description=food.get('description', ""),
                calories=food.get('calories', 0),
                repetitions=food.get('repetitions', 0)
            ) for food in diet_data['diet']['foods']
        ]
    )

    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.DietCrudStub(channel)

        d_request = diet_pb2.UpdateDietRequest(diet=diet)
        d_response = stub.UpdateDiet(d_request)

        return MessageToJson(d_response, preserving_proto_field_name=True)

    except grpc.RpcError as e:
            return e.details()


@diet_controller.route('/diet/<diet_id>', methods=['DELETE'])
def delete_diet(diet_id):
    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.DietCrudStub(channel)

        request = diet_pb2.DeleteDietRequest(diet_id=diet_id)        
        response = stub.DeleteDiet(request)
        ic(response)

        return MessageToJson(response, preserving_proto_field_name=True)
    except grpc.RpcError as e:
            return e.details()

from icecream import ic
import cachetools

import grpc
import workout_pb2_grpc
import workout_pb2
import diet_pb2_grpc
import diet_pb2
from flask import Flask, jsonify, request

app = Flask(__name__)
cache = cachetools.LRUCache(maxsize=100)


def check_workout_service_status():
    cached_response = cache.get("workout_service_status_response")
    ic(cache)

    if cached_response:
        return cached_response
    
    try:
        channel = grpc.insecure_channel('localhost:5135')   
        stub = workout_pb2_grpc.StatusStub(channel)

        request = workout_pb2.GetStatusRequest()
        response = stub.GetStatus(request)

        cache["workout_service_status_response"] = response.status

        return response.status

    except grpc.RpcError as e:
            return e.details()


def check_diet_service_status():
    cached_response = cache.get("diet_service_status_response")
    ic(cache)

    if cached_response:
        return cached_response

    try:
        channel = grpc.insecure_channel('localhost:5275')   
        stub = diet_pb2_grpc.StatusStub(channel)

        request = diet_pb2.GetStatusRequest()
        response = stub.GetStatus(request)

        cache["diet_service_status_response"] = response.status

        return response.status

    except grpc.RpcError as e:
            return e.details()


@app.route('/gateway_status', methods=['GET'])
def get_gateway_status():
    return jsonify({"status": "Gateway is up and running"})


@app.route('/workout_status', methods=['GET'])
def get_workout_status():
    service_status = check_workout_service_status()

    return jsonify({"status": service_status})


@app.route('/diet_status', methods=['GET'])
def get_diet_status():
    service_status = check_diet_service_status()

    return jsonify({"status": service_status})


if __name__ == '__main__':
    app.run(port=8080)
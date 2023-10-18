from icecream import ic

from flask import Flask, jsonify, request
import concurrent.futures

import grpc
from google.protobuf.json_format import MessageToJson
import workout_pb2_grpc
import workout_pb2

from controllers.workout_controller import workout_controller
from controllers.diet_controller import diet_controller



app = Flask(__name__)

app.register_blueprint(workout_controller)
app.register_blueprint(diet_controller)

MAX_CONCURRENT_TASKS = 5
executor = concurrent.futures.ThreadPoolExecutor(MAX_CONCURRENT_TASKS)

@app.route('/gateway_status', methods=['GET'])
def get_gateway_status():
    return jsonify({"status": "Gateway is up and running"})

# def get_workout_status_protected():
#     with app.app_context():

#         try:
#             channel = grpc.insecure_channel('localhost:5135')   
#             stub = workout_pb2_grpc.StatusStub(channel)

#             request = workout_pb2.GetStatusRequest()
#             response = stub.GetStatus(request, timeout=6)
            
#             response = MessageToJson(response, preserving_proto_field_name=True)
#             ic(response)

#             # response = jsonify({"status": response.status})

#             waiting_tasks = executor._work_queue.qsize()
#             ic(waiting_tasks)

#             # ic(response)
#             return response
#         except grpc.RpcError as e:
#             ic(e)
#             return e.details()


# @app.route('/workout_status', methods=['GET'])
# def get_workout_status():
#     future = executor.submit(get_workout_status_protected)

#     return future.result()

if __name__ == '__main__':

    app.run(port=8080, threaded=True)
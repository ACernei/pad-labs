from icecream import ic
import time
import threading
import grpc
import registration_pb2
import registration_pb2_grpc
from google.protobuf import empty_pb2

from concurrent import futures

HEARTBEAT_TIMEOUT = 6000
CRITICAL_LOAD_THRESHOLD = 60

registered_services = {}
deleted_services = {}
service_heartbeats = {}
service_load = {}

# Function to register a service
def register(name, host, port):
    service_key = f"{name}:{port}"
    if service_key not in deleted_services:
        registered_services[service_key] = {'host': host, 'port': port}
        print(f"Service {service_key} registered in the gateway")
    else:
        re_register(name, port)

# Function to deregister a service
def deregister(service_key):
    del registered_services[service_key]
    print(f"Service {service_key} deregistered from the gateway")

# Function to re-register a deleted service upon receiving a heartbeat
def re_register(service_name, port):
    service_key = f"{service_name}:{port}"
    if service_key in deleted_services:
        registered_services[service_key] = deleted_services[service_key]
        del deleted_services[service_key]
        print(f"Service {service_key} re-registered due to received heartbeat")

# Function to update service load
def update_load(service_name, port, load):
    service_key = f"{service_name}:{port}"
    if service_key not in service_load:
        service_load[service_key] = 0
    service_load[service_key] = load
    print(f"Service {service_key} load updated: {load}")

# Function to check and raise an alert for critical load
def check_critical_load(service_name, port):
    service_key = f"{service_name}:{port}"
    if service_key in service_load and service_load[service_key] > CRITICAL_LOAD_THRESHOLD:
        print(f"Critical load alert: Service {service_key} is overloaded! Load: {service_load[service_key]}")

# Function to update service heartbeat
def update_heartbeat(service_name, port):
    service_key = f"{service_name}:{port}"
    if service_key not in service_heartbeats:
        service_heartbeats[service_key] = {}
    service_heartbeats[service_key] = time.time()
    print(service_heartbeats)
    print(f"Heartbeat received for service {service_key}")

# Function to calculate the time since the last heartbeat for a service
def get_time_since_last_heartbeat(service_key):
    last_heartbeat = service_heartbeats.get(service_key)
    if last_heartbeat is not None:
        current_time = time.time()
        time_diff = current_time - last_heartbeat
        return time_diff
    else:
        return None

# Function to check if a service is active based on the time since the last heartbeat
def is_service_active(service_key):
    time_since_last_heartbeat = get_time_since_last_heartbeat(service_key)
    if time_since_last_heartbeat is not None and time_since_last_heartbeat <= HEARTBEAT_TIMEOUT:
        print(f"Time since last heartbeat for service {service_key}: {time_since_last_heartbeat}ms")
        return True
    else:
        print(f"Service {service_key} has not sent a heartbeat.")
        return False

# Function to periodically check the status of registered services
def check_service_status():
    while True:
        current_time = time.time()
        for service_key in list(registered_services.keys()):
            if not is_service_active(service_key):
                print(f"Service {service_key} is inactive.")
                deleted_services[service_key] = registered_services[service_key]
                deregister(service_key)
        time.sleep(HEARTBEAT_TIMEOUT / 1000)

# Service function for registration
class RegistrationServiceServicer(registration_pb2_grpc.RegistrationServiceServicer):
    def RegisterService(self, request, context):
        ic(request)
        registration_info = request
        register(registration_info.name, registration_info.host, registration_info.port)
        print(f"Received registration: Name: {registration_info.name}, Host: {registration_info.host}, Port: {registration_info.port}")
        return empty_pb2.Empty()

    # Service function for de-registration
    def DeregisterService(self, request, context):
        deregistration_info = request
        service_key = f"{deregistration_info.service_name}:{deregistration_info.port}"
        deregister(service_key)
        print(f"Received de-registration: Name: {deregistration_info.service_name}, Host: {deregistration_info.host}, Port: {deregistration_info.port}")
        return empty_pb2.Empty()

    # Service function for heartbeat updates
    def UpdateServiceHeartbeat(self, request, context):
        ic(request)
        update_load(request.service_name, request.port, request.load)
        check_critical_load(request.service_name, request.port)

        update_heartbeat(request.service_name, request.port)
        re_register(request.service_name, request.port)
        return empty_pb2.Empty()

    # Service function to send the list of registered services
    def ListRegisteredServices(self, request, context):
        services_list = []
        for service_key, info in registered_services.items():
            name, port = service_key.split(':')
            load = service_load.get(service_key, 0)
            services_list.append(registration_pb2.ServiceInfo(
                name=name,
                host=info['host'],
                port=int(port),
                load=load
            ))
        response = registration_pb2.ServicesList(services=services_list)
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    registration_pb2_grpc.add_RegistrationServiceServicer_to_server(RegistrationServiceServicer(), server)
    server.add_insecure_port('localhost:5001')
    server.start()
    print("Registration server running at http://0.0.0.0:5001")
    server.wait_for_termination()


if __name__ == '__main__':
    status_heartbeat_thread = threading.Thread(target=check_service_status)
    status_heartbeat_thread.daemon = True
    status_heartbeat_thread.start()
    serve()
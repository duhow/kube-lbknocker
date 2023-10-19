import os
from kubernetes import config, client
from flask import Flask, request

def terminate(message, exit_code=1):
    with open("/dev/termination-log", "w") as termination_log:
        termination_log.write(message)
    exit(exit_code)

def is_private_address(ip):
    for prefix in ["10.", "127.", "169.254.", "192.168."]:
        if ip.startswith(prefix):
            return True

    for block in range(16, 32):
        if ip.startswith(f"172.{block}."):
            return True

    return False

app = Flask(__name__)

# Load Kubernetes configuration from the default service account mounted in the pod.
config.load_incluster_config()

# Get the current namespace from the mounted ServiceAccount.
with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as namespace_file:
    current_namespace = namespace_file.read()

# Get the Service name from the environment variable.
service_name = os.environ.get("KUBERNETES_SERVICE_NAME")
if not service_name:
    terminate("Missing env KUBERNETES_SERVICE_NAME, you need to provide the value")

# Create a Kubernetes client.
api_instance = client.CoreV1Api()
# Fetch the Service object by name in the current namespace.
service = api_instance.read_namespaced_service(service_name, current_namespace)
if not service:
    terminate(f"Service {service_name} not accessible or does not exist, check Role permissions?")

@app.route('/allowme', methods=['GET'])
def allowme():
    # Get the client IP address from the request.
    client_ip = request.remote_addr + "/32"

    if is_private_address(client_ip):
        return "Invalid source address", 401

    try:
        # Refresh with current values
        service = api_instance.read_namespaced_service(service_name, current_namespace)

        # Check if the client IP address is already in loadBalancerSourceRanges.
        if service.spec.load_balancer_source_ranges:
            if client_ip in service.spec.load_balancer_source_ranges:
                return "OK", 200
            service.spec.load_balancer_source_ranges.append(client_ip)
        else:
            service.spec.load_balancer_source_ranges = [client_ip]

        # Update the Service's loadBalancerSourceRanges with the client's IP.
        api_instance.patch_namespaced_service(service_name, current_namespace, service)
        return "OK", 204
    except Exception as e:
        return f"Failed to update Service: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')

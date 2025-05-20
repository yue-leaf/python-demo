import socket

from flask import Flask, render_template
from config import Config
from k8s_tool import KubernetesClient

app = Flask(__name__)

k8s_client = KubernetesClient(Config.k8s_host, Config.k8s_token)


@app.route('/index', methods=['GET'])
def index():
    deployment_name = "edgex-kuiper"
    namespace = "edgex"
    ok, deployment = k8s_client.read_namespaced_deployment(deployment_name, namespace)
    if not ok:
        return 'get deployment failed'
    pod_num = deployment.spec.replicas
    pod_ip = socket.gethostbyname(socket.gethostname())
    return render_template('index.html', pod_num=pod_num, pod_ip=pod_ip)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

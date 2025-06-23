import base64
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from log_tool import Logger


def check_register():
    return True


def run_command(command, input_text=None, check=True):
    """Execute a shell command and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            text=True,
            input=input_text,
            capture_output=True
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        Logger.error(f"Error executing command: {command}")
        Logger.error(f"Error message: {e.stderr}")
        Logger.error(traceback.format_exc())
        return e.stdout, e.stderr, e.returncode


def check_k3s_installed():
    """Check if k3s is installed by checking systemctl status."""
    stdout, stderr, returncode = run_command("systemctl status k3s")
    if returncode == 0 or "k3s" in stdout or "k3s" in stderr:
        Logger.info("k3s is installed.")
        return True
    elif returncode == 4:  # systemctl status returns 4 if service not found
        Logger.error("k3s is not installed.")
        return False
    else:
        Logger.error(f"Error checking k3s installation: {stderr}")
        return False


def check_k3s_running():
    """Check if k3s service is running."""
    stdout, stderr, returncode = run_command("systemctl is-active k3s")
    if stdout.strip() == "active":
        Logger.info("k3s is running.")
        return True
    else:
        Logger.error("k3s is not running.")
        return False


def start_k3s():
    """Start k3s service."""
    Logger.info("Attempting to start k3s...")
    stdout, stderr, returncode = run_command("sudo systemctl start k3s")
    if returncode == 0:
        Logger.info("k3s started successfully.")
        # Wait briefly to ensure service is up
        time.sleep(5)
        return True
    else:
        Logger.error(f"Failed to start k3s: {stderr}")
        return False


def restart_k3s():
    Logger.info("Attempting to restart k3s...")
    stdout, stderr, returncode = run_command("sudo systemctl restart k3s")
    if returncode == 0:
        Logger.info("k3s restarted successfully.")
        # Wait briefly to ensure service is up
        time.sleep(5)
        return True
    else:
        Logger.error(f"Failed to restart k3s: {stderr}")
        return False


def create_configmap_tz():
    cmd = "kubectl create configmap tz --from-file=/usr/share/zoneinfo/Asia/Shanghai -n kube-system"
    stdout, stderr, returncode = run_command(cmd)
    if returncode == 0:
        Logger.info("Kubernetes YAML applied successfully:")
        Logger.info(stdout)
        return True
    else:
        if "already exists" in stderr:
            Logger.info("ConfigMap 'tz' already exists. Skipping creation.")
            return True
        Logger.error(f"Failed to apply Kubernetes YAML: {stderr}")
        return False


def apply_kubernetes_yaml(K8S_YAML):
    """Apply the provided Kubernetes YAML configuration using kubectl."""
    Logger.info("Applying Kubernetes YAML configuration...")
    # Create a temporary file to store the YAML
    # with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
    #     temp_file.write(K8S_YAML)
    #     temp_file_path = temp_file.name
    # try:
    #     # Apply the YAML using kubectl
    #     stdout, stderr, returncode = run_command(f"kubectl apply -f {temp_file_path}")
    #     if returncode == 0:
    #         print("Kubernetes YAML applied successfully:")
    #         print(stdout)
    #     else:
    #         print(f"Failed to apply Kubernetes YAML: {stderr}")
    #         return False
    # finally:
    #     # Clean up the temporary file
    #     os.unlink(temp_file_path)
    # return True

    stdout, stderr, returncode = run_command(f"kubectl apply -f -", input_text=K8S_YAML)
    if returncode == 0:
        Logger.info("Kubernetes YAML applied successfully:")
        Logger.info(stdout)
        return True
    else:
        Logger.error(f"Failed to apply Kubernetes YAML: {stderr}")
        return False


def check_kubectl():
    """Check kubectl functionality by listing nodes."""
    Logger.info("Checking kubectl functionality...")
    stdout, stderr, returncode = run_command("kubectl get nodes")
    if returncode == 0:
        Logger.info("kubectl check successful. Node output:")
        Logger.info(stdout)
        return True
    else:
        Logger.error(f"kubectl check failed: {stderr}")
        return False


def install_k3s():
    """Install k3s using the provided curl command."""
    Logger.info("Installing k3s...")
    install_cmd = (
        "curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | "
        "INSTALL_K3S_MIRROR=cn K3S_TOKEN=SECRET sh -s -"
    )
    stdout, stderr, returncode = run_command(install_cmd)
    if returncode == 0:
        Logger.info("k3s installed successfully.")
        # Wait briefly to ensure service is initialized
        time.sleep(10)
        return True
    else:
        Logger.error(f"Failed to install k3s: {stderr}")
        return False


def modify_k3s_registries():
    try:
        os.makedirs("/etc/rancher/k3s/", exist_ok=True)
        command = """cat << EOF > /etc/rancher/k3s/registries.yaml
mirrors:
  docker.io:
    endpoint:
      - "https://docker.snowballtech.com/"
  registry.k8s.io:
    endpoint:
      - "https://k8s.snowballtech.com/"
EOF
        """
        stdout, stderr, returncode = run_command(command)
        if returncode != 0:
            Logger.error(f"Failed to modify k3s registries: {stderr}")
            return False
        return True
    except Exception as e:
        Logger.error(f"Error modifying k3s registries: {e}")
        return False


def init_k3s():
    # Check if k3s is installed
    if not check_k3s_installed():
        Logger.info("Please install k3s before proceeding.")
        if not install_k3s():
            Logger.error("Could not install k3s. Exiting.")
            return "Failed to install k3s", False

    if not modify_k3s_registries():
        return "Failed to modify k3s registries", False

    # Check if k3s is running
    if not check_k3s_running():
        # Try to start k3s
        if not start_k3s():
            Logger.error("Could not start k3s. Exiting.")
            return "Failed to start k3s", False
    else:
        if not restart_k3s():
            Logger.error("Could not restart k3s. Exiting.")
            return "Failed to restart k3s", False

    # Verify k3s is now running
    if check_k3s_running():
        # Check kubectl
        if not check_kubectl():
            Logger.error("kubectl check failed. Exiting.")
            return "kubectl check failed", False
    else:
        Logger.error("k3s is still not running. Exiting.")
        return False, "k3s is not running"
    return "k3s is running and kubectl is functional", True


def get_cluster_info():
    try:

        # 获取节点信息
        nodes_cmd = "kubectl get nodes -o json"
        nodes_result = subprocess.run(nodes_cmd, shell=True, capture_output=True, text=True)
        nodes_data = json.loads(nodes_result.stdout)
        node_count = len(nodes_data['items'])

        # 获取 kube-system 命名空间创建时间作为集群 Age 的近似值
        cl_cmd = "kubectl get cluster"
        cl_result = subprocess.run(cl_cmd, shell=True, capture_output=True, text=True)
        result = cl_result.stdout.split('\n')[1].split('  ')
        cluster_name = result[0].strip()
        age = result[1].strip()

        version_cmd = "kubectl version -o json"
        version_result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
        version_data = json.loads(version_result.stdout)
        version = version_data['serverVersion']['gitVersion']
        return {
            'cluster_name': cluster_name,
            'age': age,
            'node_count': node_count,
            'version': version
        }
    except Exception as e:
        Logger.error(f"Error getting cluster info: {e}")
        return None


def get_k8s_token():
    try:
        # 运行 kubectl 命令获取 token
        command = """kubectl get secret -n snb-system snb-admin-token -o jsonpath='{.data.token}'"""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            Logger.error(f"Error getting token: {result.stderr}")
            return result.stderr, False
        token = result.stdout.strip()
        if not token:
            Logger.error("Token not found.")
            return None, False
        return base64.b64decode(token.encode('utf-8')).decode('utf-8'), True

    except Exception as e:
        Logger.error(f"Error executing kubectl command: {e}")
        return None, False


def get_k8s_svc():
    try:
        command = "kubectl get svc kubernetes -n default -o jsonpath='{.spec.clusterIP}'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            Logger.info(f"Error getting ip: {result.stderr}")
            return result.stderr, False
        ip = result.stdout.strip()
        if not ip:
            Logger.error("Cluster ip not found.")
            return None, False
        return f'https://{ip}:443', True
    except Exception as e:
        Logger.error(f"Error executing kubectl command: {e}")
        return None, False


def get_resource_path(relative_path):
    """ 获取打包后资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def cp_k3s_config():
    if not os.path.exists("/root/.kube"):
        # Create the directory if it doesn't exist
        cmd = "mkdir -p /root/.kube"
        stdout, stderr, returncode = run_command(cmd)
        if returncode != 0:
            Logger.error(f"Failed to create .kube directory: {stderr}")
            return False
    cmd = "cp  /etc/rancher/k3s/k3s.yaml /root/.kube/config"
    stdout, stderr, returncode = run_command(cmd)
    if returncode != 0:
        Logger.error(f"Failed to copy k3s config: {stderr}")
        return False
    restart_k3s()
    return True


def install_helm():
    try:
        # 检查 helm 是否已安装
        command = "helm version"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            Logger.info("Helm is already installed.")
            return True
        # 检测系统架构
        arch = platform.machine().lower()
        if arch in ["aarch64", "arm64"]:
            arch_name = "arm64"
        elif arch in ["x86_64", "amd64"]:
            arch_name = "amd64"
        else:
            Logger.error(f"Unsupported architecture: {arch}")
            return False
        package = get_resource_path('pkg')
        helm_binary = os.path.join(package, 'linux-' + arch_name, "helm")
        if not helm_binary or not os.path.exists(helm_binary):
            Logger.error(f"Helm package for {helm_binary} not found at {package}")
            return False
        shutil.copy(helm_binary, "/usr/local/bin/helm")
        os.chmod("/usr/local/bin/helm", 0o755)
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            Logger.info("Helm is already installed.")
            return True
        return False
    except Exception as e:
        Logger.error(f"Error checking Helm installation: {e}")
        return False


def install_prometheus():
    try:
        release_name = "kps"
        create_ns_cmd = "kubectl create ns monitoring"
        stdout, stderr, returncode = run_command(create_ns_cmd)
        if returncode != 0 and "already exists" not in stderr:
            Logger.info(f"Failed to create namespace: {stderr}")
            return False
        package = get_resource_path('pkg')
        prometheus_helm_file = os.path.join(package, 'kube-prometheus-stack-70.4.0.tgz')
        if not prometheus_helm_file or not os.path.exists(prometheus_helm_file):
            Logger.info(f"Helm package for {prometheus_helm_file} not found at {package}")
            return False
        filter_cmd = f"helm list --namespace monitoring --filter {release_name} -o json"
        stdout, stderr, returncode = run_command(filter_cmd, check=False)
        if returncode != 0:
            Logger.info(f"Error checking Helm release: {stderr}")
            return False
        releases = json.loads(stdout) if stdout else []
        release_exists = any(release["name"] == release_name for release in releases)
        if release_exists:
            cmd = f"helm upgrade {release_name} {prometheus_helm_file} -n monitoring"
        else:
            cmd = f"helm install {release_name} {prometheus_helm_file} -n monitoring"
        stdout, stderr, returncode = run_command(cmd)
        if returncode != 0 and "already exists" not in stderr:
            Logger.info(f"Failed to install prometheus: {stderr}")
            return False
        return True
    except Exception as e:
        Logger.info(f"Error installing prometheus: {e}")
        return False


def install_telegraf(config):
    try:
        release_name = "telegraf"
        create_ns_cmd = "kubectl create ns monitoring"
        stdout, stderr, returncode = run_command(create_ns_cmd)
        if returncode != 0 and "already exists" not in stderr:
            Logger.error(f"Failed to create namespace: {stderr}")
            return False
        package = get_resource_path('pkg')
        telegraf_helm_file = os.path.join(package, 'telegraf-1.8.57.tgz')
        if not telegraf_helm_file or not os.path.exists(telegraf_helm_file):
            Logger.error(f"Helm package for {telegraf_helm_file} not found at {package}")
            return False
        filter_cmd = f"helm list --namespace monitoring --filter {release_name} -o json"
        stdout, stderr, returncode = run_command(filter_cmd, check=False)
        if returncode != 0:
            Logger.error(f"Error checking Helm release: {stderr}")
            return False
        releases = json.loads(stdout) if stdout else []
        release_exists = any(release["name"] == release_name for release in releases)
        if release_exists:
            cmd = f"helm upgrade {release_name} {telegraf_helm_file} -n monitoring -f -"
        else:
            cmd = f"helm install {release_name} {telegraf_helm_file} -n monitoring -f -"
        stdout, stderr, returncode = run_command(cmd, input_text=config)
        if returncode != 0 and "already exists" not in stderr:
            Logger.error(f"Failed to install prometheus: {stderr}")
            return False
        return True

    except Exception as e:
        Logger.error(traceback.format_exc())
        Logger.error(f"Error installing prometheus: {e}")
        return False


if __name__ == '__main__':
    # init_k3s()
    K8S_YAML = """
apiVersion: v1
kind: Namespace
metadata:
  name: huwei-system
"""
    # apply_kubernetes_yaml(K8S_YAML)
    # get_cluster_info()
    # token, ok = get_k8s_token()
    # print(token)
    # print(get_k8s_svc())
    # create_configmap_tz()
    # install_helm()
    # install_prometheus()

    config = """
config:
    inputs:
    - prometheus:
        urls:
          - "http://kps-kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090/federate?match%5B%5D=%7B__name__%3D~%22.%2B%22%7D"   #抓取指标的URL，一般不需要更改
        metric_version: 2
        tags:
          cluster: "k3s"   #集群名称 按照k3s-项目名称的格式
    outputs:
    - influxdb:
        urls:
          - "http://47.117.87.253:8428"   #远端的victoria-metrics地址
        database: "telegraf"   #远端的victoria-metrics DB 部署时需指定 按照telegraf-项目名称的格式
service:
  enabled: false
"""
    # install_telegraf(config)

    modify_k3s_registries()

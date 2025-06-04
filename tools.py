import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path


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
        return e.stdout, e.stderr, e.returncode


def check_k3s_installed():
    """Check if k3s is installed by checking systemctl status."""
    stdout, stderr, returncode = run_command("systemctl status k3s")
    if returncode == 0 or "k3s" in stdout or "k3s" in stderr:
        print("k3s is installed.")
        return True
    elif returncode == 4:  # systemctl status returns 4 if service not found
        print("k3s is not installed.")
        return False
    else:
        print(f"Error checking k3s installation: {stderr}")
        return False


def check_k3s_running():
    """Check if k3s service is running."""
    stdout, stderr, returncode = run_command("systemctl is-active k3s")
    if stdout.strip() == "active":
        print("k3s is running.")
        return True
    else:
        print("k3s is not running.")
        return False


def start_k3s():
    """Start k3s service."""
    print("Attempting to start k3s...")
    stdout, stderr, returncode = run_command("sudo systemctl start k3s")
    if returncode == 0:
        print("k3s started successfully.")
        # Wait briefly to ensure service is up
        time.sleep(5)
        return True
    else:
        print(f"Failed to start k3s: {stderr}")
        return False


def apply_kubernetes_yaml(K8S_YAML):
    """Apply the provided Kubernetes YAML configuration using kubectl."""
    print("Applying Kubernetes YAML configuration...")
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
        print("Kubernetes YAML applied successfully:")
        print(stdout)
        return True
    else:
        print(f"Failed to apply Kubernetes YAML: {stderr}")
        return False


def check_kubectl():
    """Check kubectl functionality by listing nodes."""
    print("Checking kubectl functionality...")
    stdout, stderr, returncode = run_command("kubectl get nodes")
    if returncode == 0:
        print("kubectl check successful. Node output:")
        print(stdout)
        return True
    else:
        print(f"kubectl check failed: {stderr}")
        return False


def install_k3s():
    """Install k3s using the provided curl command."""
    print("Installing k3s...")
    install_cmd = (
        "curl -sfL https://rancher-mirror.rancher.cn/k3s/k3s-install.sh | "
        "INSTALL_K3S_MIRROR=cn K3S_TOKEN=SECRET sh -s -"
    )
    stdout, stderr, returncode = run_command(install_cmd)
    if returncode == 0:
        print("k3s installed successfully.")
        # Wait briefly to ensure service is initialized
        time.sleep(10)
        return True
    else:
        print(f"Failed to install k3s: {stderr}")
        return False


def init_k3s():
    # Check if k3s is installed
    if not check_k3s_installed():
        print("Please install k3s before proceeding.")
        if not install_k3s():
            print("Could not install k3s. Exiting.")
            return "Failed to install k3s", False

    # Check if k3s is running
    if not check_k3s_running():
        # Try to start k3s
        if not start_k3s():
            print("Could not start k3s. Exiting.")
            return "Failed to start k3s", False

    # Verify k3s is now running
    if check_k3s_running():
        # Check kubectl
        if not check_kubectl():
            print("kubectl check failed. Exiting.")
            return "kubectl check failed", False
    else:
        print("k3s is still not running. Exiting.")
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
        print(f"Error getting cluster info: {e}")
        return None


if __name__ == '__main__':
    # init_k3s()
    K8S_YAML = """
apiVersion: v1
kind: Namespace
metadata:
  name: huwei-system
"""
    # apply_kubernetes_yaml(K8S_YAML)
    get_cluster_info()

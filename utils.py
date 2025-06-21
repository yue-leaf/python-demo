import hashlib
import json
import re
import socket
import subprocess

import psutil
import netifaces
import os
import platform


def get_hostname():
    """获取本机主机名"""
    try:
        return socket.gethostname()
    except Exception as e:
        return f"获取主机名失败: {str(e)}"


def get_os_info():
    """获取操作系统信息"""
    try:
        return {
            "os_name": platform.system(),
            "os_version": platform.release(),
            "os_platform": platform.platform()
        }
    except Exception as e:
        return f"获取操作系统信息失败: {str(e)}"


def get_local_ip():
    """获取本机 IP 地址"""
    try:
        # 获取本机主机名
        hostname = socket.gethostname()
        # 获取本机 IP 地址
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception as e:
        return f"获取 IP 地址失败: {str(e)}"


def get_network_interfaces_details():
    """获取所有网络接口的详细信息"""
    interfaces = {}
    for interface in netifaces.interfaces():
        if interface.startswith('lo') or interface.startswith('docker') or interface.startswith('veth') or \
                interface.startswith('flannel') or interface.startswith('cni'):
            continue
        try:
            addrs = netifaces.ifaddresses(interface)
            interfaces[interface] = {}
            if netifaces.AF_INET in addrs:  # IPv4
                interfaces[interface]['ipv4'] = [
                    {'addr': addr['addr'], 'netmask': addr.get('netmask'), 'broadcast': addr.get('broadcast')}
                    for addr in addrs[netifaces.AF_INET]
                ]
            if netifaces.AF_INET6 in addrs:  # IPv6
                interfaces[interface]['ipv6'] = [
                    {'addr': addr['addr'], 'netmask': addr.get('netmask')}
                    for addr in addrs[netifaces.AF_INET6]
                ]
        except Exception as e:
            print(f"Error processing interface {interface}: {e}")
            continue
    return interfaces


def get_cpu_info():
    """获取 CPU 使用率"""
    cpu_percent = psutil.cpu_percent(interval=1)
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    return {
        "cpu_percent": f"{cpu_percent}%",
        "logical_cores": logical_cores,
        "physical_cores": physical_cores
    }


def get_memory_info():
    """获取内存信息"""
    memory = psutil.virtual_memory()
    return {
        "mem_total": f"{memory.total / (1024 ** 3):.2f} GB",
        "mem_used": f"{memory.used / (1024 ** 3):.2f} GB",
        "mem_available": f"{memory.available / (1024 ** 3):.2f} GB",
        "mem_percent": f"{memory.percent}%"
    }


def get_disk_info():
    """获取磁盘总容量和每个分区的详细信息"""
    try:
        total_capacity = 0
        total_used = 0
        disk_info = {}
        partitions = psutil.disk_partitions()
        for partition in partitions:
            # 过滤 Kubernetes 临时挂载点
            mountpoint = partition.mountpoint
            if 'snap' in mountpoint or '/var/lib/kubelet/pods' in mountpoint:
                continue
            try:
                disk = psutil.disk_usage(mountpoint)
                total_capacity += disk.total
                total_used += disk.used
                disk_info[mountpoint] = {
                    "total": f"{disk.total / (1024 ** 3):.2f} GB",
                    "used": f"{disk.used / (1024 ** 3):.2f} GB",
                    "free": f"{disk.free / (1024 ** 3):.2f} GB",
                    "percent": f"{disk.percent}%",
                    "device": partition.device,
                }
            except:
                disk_info[partition.mountpoint] = "无法获取详细信息"
        total_usage_percent =f"{(total_used / total_capacity) * 100 if total_capacity > 0 else 0:.2f}%"

        return {
            "total_capacity": f"{total_capacity / (1024 ** 3):.2f} GB",
            "total_used": f"{total_used / (1024 ** 3):.2f} GB",
            "total_free": f"{(total_capacity - total_used) / (1024 ** 3):.2f} GB",
            "total_usage_percent": total_usage_percent,
            "details": disk_info
        }
    except Exception as e:
        return 0, f"获取磁盘信息失败: {str(e)}"


def get_cpu_mem_disk():
    physical_cores = psutil.cpu_count(logical=False)

    memory = psutil.virtual_memory()
    mem_total = f"{memory.total / (1024 ** 3):.2f} GB"

    total_capacity = 0
    partitions = psutil.disk_partitions()
    for partition in partitions:
        # 过滤 Kubernetes 临时挂载点
        mountpoint = partition.mountpoint
        if 'snap' in mountpoint or '/var/lib/kubelet/pods' in mountpoint:
            continue
        disk = psutil.disk_usage(mountpoint)
        total_capacity += disk.total
    total_capacity = f"{total_capacity / (1024 ** 3):.2f} GB"
    return physical_cores, mem_total, total_capacity


def main():
    print("=== 本机信息 ===")
    # 操作系统信息
    print("\n1. 操作系统信息:")
    for key, value in get_os_info().items():
        print(f"  {key}: {value}")

    # 主机名
    print("\n2. 主机名:")
    print(f"  {get_hostname()}")

    # 获取 IP 地址
    print("\n1. 本机 IP 地址:")
    print(f"默认 IP: {get_local_ip()}")
    print("所有网络接口 IP:")
    interfaces = get_network_interfaces_details()
    for name, details in interfaces.items():
        print(f"接口: {name}")
        if 'ipv4' in details:
            for ipv4 in details['ipv4']:
                print(f"  IPv4: {ipv4['addr']}, 掩码: {ipv4['netmask']}, 广播: {ipv4.get('broadcast')}")
        if 'ipv6' in details:
            for ipv6 in details['ipv6']:
                print(f"  IPv6: {ipv6['addr']}, 掩码: {ipv6['netmask']}")

    # 获取 CPU 信息
    print("\n2. CPU 信息:")
    for key, value in get_cpu_info().items():
        print(f"  {key}: {value}")

    # 获取内存信息
    print("\n3. 内存信息:")
    for key, value in get_memory_info().items():
        print(f"  {key}: {value}")

    # 获取磁盘信息
    disk_info = get_disk_info()
    print(f"磁盘总容量: {disk_info['total_capacity']},总使用率: {disk_info['total_usage_percent']})")
    print("磁盘分区详细信息:")
    for mountpoint, info in disk_info['details'].items():
        print(f"  挂载点: {mountpoint}")
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {info}")


def get_hardware_info():
    system = platform.system().lower()
    hardware_info = {}

    if system == "windows":
        try:
            # 使用 wmic 获取硬件信息
            def run_wmic(query):
                result = subprocess.check_output(f'wmic {query} get /value', shell=True, text=True,
                                                 stderr=subprocess.DEVNULL)
                return re.search(r'=(.+)', result).group(1).strip() if re.search(r'=(.+)', result) else ""

            hardware_info["cpu_id"] = run_wmic("cpu") or platform.processor()
            hardware_info["bios_id"] = run_wmic("bios get serialnumber")
            hardware_info["disk_id"] = run_wmic("diskdrive get serialnumber")
            hardware_info["baseboard_id"] = run_wmic("baseboard get serialnumber")
        except Exception:
            # 回退到 platform 模块
            hardware_info["cpu_id"] = platform.processor()
            hardware_info["bios_id"] = ""
            hardware_info["disk_id"] = ""
            hardware_info["baseboard_id"] = ""

    elif system == "linux":
        try:
            # CPU ID
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
                match = re.search(r"Serial\s*:\s*(\w+)", cpuinfo) or re.search(r"model name\s*:\s*([^\n]+)", cpuinfo)
                hardware_info["cpu_id"] = match.group(1).strip() if match else platform.processor()

            # BIOS Serial Number
            bios_path = "/sys/class/dmi/id/bios_serial"
            hardware_info["bios_id"] = open(bios_path, "r").read().strip() if os.path.exists(bios_path) else ""

            # Disk Serial Number
            disk_path = "/sys/block/sda/device/serial"  # 假设主磁盘为 sda
            hardware_info["disk_id"] = open(disk_path, "r").read().strip() if os.path.exists(disk_path) else ""

            # Baseboard Serial Number
            board_path = "/sys/class/dmi/id/board_serial"
            hardware_info["baseboard_id"] = open(board_path, "r").read().strip() if os.path.exists(board_path) else ""
        except Exception:
            # 回退到 platform 模块
            hardware_info["cpu_id"] = platform.processor()
            hardware_info["bios_id"] = ""
            hardware_info["disk_id"] = ""
            hardware_info["baseboard_id"] = ""

    else:
        # 其他系统，回退到 platform
        hardware_info["cpu_id"] = platform.processor()
        hardware_info["bios_id"] = ""
        hardware_info["disk_id"] = ""
        hardware_info["baseboard_id"] = ""

    return hardware_info


def get_machine_id():
    # 获取硬件信息
    info = get_hardware_info()

    # 组合硬件信息，过滤空值
    combined = "-".join([v for v in info.values() if v])
    if not combined:
        combined = platform.node()  # 回退到主机名

    # 生成 SHA256 哈希
    return hashlib.sha256(combined.encode()).hexdigest()


if __name__ == "__main__":
    # main()
    # print(get_machine_id())
    result = get_network_interfaces_details()
    print(result)
    a = json.dumps(result)
    print(json.loads(a))
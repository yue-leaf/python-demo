import socket
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
            "操作系统名称": platform.system(),
            "版本": platform.release(),
            "详细信息": platform.platform()
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


def get_network_interfaces():
    """获取所有网络接口的 IP 地址"""
    interfaces = {}
    for interface in netifaces.interfaces():
        try:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:  # IPv4
                for addr in addrs[netifaces.AF_INET]:
                    interfaces[interface] = addr['addr']
        except:
            continue
    return interfaces


def get_cpu_info():
    """获取 CPU 使用率"""
    cpu_percent = psutil.cpu_percent(interval=1)
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    return {
        "CPU 使用率": f"{cpu_percent}%",
        "逻辑 CPU 核心数": logical_cores,
        "physical_cores": physical_cores
    }


def get_memory_info():
    """获取内存信息"""
    memory = psutil.virtual_memory()
    return {
        "总内存": f"{memory.total / (1024 ** 3):.2f} GB",
        "已用内存": f"{memory.used / (1024 ** 3):.2f} GB",
        "可用内存": f"{memory.available / (1024 ** 3):.2f} GB",
        "内存使用率": f"{memory.percent}%"
    }


def get_disk_info():
    """获取磁盘总容量和每个分区的详细信息"""
    try:
        total_capacity = 0
        total_used = 0
        disk_info = {}
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                disk = psutil.disk_usage(partition.mountpoint)
                total_capacity += disk.total
                total_used += disk.used
                disk_info[partition.mountpoint] = {
                    "总大小": f"{disk.total / (1024 ** 3):.2f} GB",
                    "已用": f"{disk.used / (1024 ** 3):.2f} GB",
                    "可用": f"{disk.free / (1024 ** 3):.2f} GB",
                    "使用率": f"{disk.percent}%"
                }
            except:
                disk_info[partition.mountpoint] = "无法获取详细信息"
        total_usage_percent = (total_used / total_capacity) * 100 if total_capacity > 0 else 0
        return f"{total_capacity / (1024 ** 3):.2f} GB", total_usage_percent, disk_info
    except Exception as e:
        return 0, f"获取磁盘信息失败: {str(e)}"


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
    for iface, ip in get_network_interfaces().items():
        print(f"  {iface}: {ip}")

    # 获取 CPU 信息
    print("\n2. CPU 信息:")
    for key, value in get_cpu_info().items():
        print(f"  {key}: {value}")

    # 获取内存信息
    print("\n3. 内存信息:")
    for key, value in get_memory_info().items():
        print(f"  {key}: {value}")

    # 获取磁盘信息
    total_capacity, total_usage_percent, disk_info = get_disk_info()
    print(f"磁盘总容量: {total_capacity},总使用率: {total_usage_percent:.2f}%)")
    print("磁盘分区详细信息:")
    for mountpoint, info in disk_info.items():
        print(f"  挂载点: {mountpoint}")
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {info}")


if __name__ == "__main__":
    main()

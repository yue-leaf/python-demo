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


if __name__ == "__main__":
    main()

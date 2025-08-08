#!/usr/bin/env python3
import asyncio
import argparse
import csv
import ipaddress
import os
import platform
import re
import socket
import subprocess
import time

def get_local_ip():
    """获取本地IP地址"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 不需要连接成功，只是为了获取本地IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_network_range(local_ip, subnet_mask='255.255.255.0'):
    """根据本地IP和子网掩码获取网络范围"""
    # 计算网络地址和广播地址
    ip = ipaddress.IPv4Address(local_ip)
    mask = ipaddress.IPv4Address(subnet_mask)
    network = ipaddress.IPv4Network(f'{ip}/{mask}', strict=False)
    return network

async def ping_host(ip):
    os_type = platform.system().lower()
    if os_type == 'windows':
        command = ['ping', '-n', '1', '-w', '1000', str(ip)]  # 缩短超时时间
    elif os_type == 'linux':
        command = ['ping', '-c', '1', '-W', '1', str(ip)]  # 缩短等待时间
    else:
        return False

    try:
        # 设置子进程超时为2秒
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=2.0
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        return proc.returncode == 0
    except (asyncio.TimeoutError, subprocess.SubprocessError, Exception):
        return False

async def get_hostname(ip):
    """根据IP地址获取主机名(异步版)"""
    ip_str = str(ip)

    # 方法1: 标准DNS解析（异步）
    try:
        loop = asyncio.get_event_loop()
        hostname, _, _ = await loop.run_in_executor(None, socket.gethostbyaddr, ip_str)
        return hostname
    except (socket.herror, socket.gaierror):
        pass

    # Linux系统专用多重fallback
    if platform.system().lower() == 'linux':
        # 方法2: 异步执行getent命令
        try:
            proc = await asyncio.create_subprocess_exec(
                'getent', 'hosts', ip_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            result = stdout.decode().strip()
            parts = result.split()
            if len(parts) >= 2 and parts[0] == ip_str:
                return parts[1]
        except (asyncio.TimeoutError, subprocess.SubprocessError):
            pass

        # 方法3: 异步读取/etc/hosts文件
        try:
            loop = asyncio.get_event_loop()
            with await loop.run_in_executor(None, open, '/etc/hosts', 'r') as f:
                content = await loop.run_in_executor(None, f.read)
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    columns = line.split()
                    if columns and columns[0] == ip_str and len(columns) >= 2:
                        return columns[1]
        except IOError:
            pass

        # 方法4: 异步FQDN解析
        try:
            loop = asyncio.get_event_loop()
            fqdn = await loop.run_in_executor(None, socket.getfqdn, ip_str)
            if fqdn != ip_str:
                return fqdn
        except socket.error:
            pass

        # 方法5: 异步执行dig命令
        try:
            proc = await asyncio.create_subprocess_exec(
                'dig', '-x', ip_str, '+short',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            hostname = stdout.decode().strip()
            if hostname:
                return hostname.rstrip('.')
        except (asyncio.TimeoutError, subprocess.SubprocessError, FileNotFoundError):
            pass

    return 'Unknown'

async def get_mac_address(ip):
    """根据IP地址获取MAC地址(异步版)"""
    if platform.system().lower() == 'windows':
        command = ['arp', '-a', str(ip)]
    else:
        command = ['arp', '-n', str(ip)]

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()
        mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
        match = re.search(mac_pattern, output)
        return match.group(0) if match else 'Unknown'
    except Exception:
        return 'Unknown'

async def scan_ip(ip):
    """扫描单个IP地址，返回结果(异步版)"""
    if await ping_host(ip):
        hostname = await get_hostname(ip)
        mac = await get_mac_address(ip)
        return {'ip': str(ip), 'hostname': hostname, 'mac': mac}
    return None

async def get_arp_table():
    """获取系统ARP表"""
    if platform.system().lower() == 'windows':
        proc = await asyncio.create_subprocess_exec(
            'arp', '-a',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            'arp', '-n',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    stdout, _ = await proc.communicate()
    return stdout.decode('utf-8', errors='ignore')

async def scan_network(exclude_ips=None, network_range=None):
    """扫描网络并返回在线主机列表(结合ARP表和主动扫描)"""
    # 获取本地IP和网络范围
    local_ip = get_local_ip()
    if network_range:
        try:
            network = ipaddress.IPv4Network(network_range, strict=False)
        except ValueError:
            print(f"无效的网络范围: {network_range}")
            network = get_network_range(local_ip)
    else:
        network = get_network_range(local_ip)

    # 获取ARP表中的设备
    arp_output = await get_arp_table()
    arp_hosts = set()

    # 解析ARP表输出
    for line in arp_output.split('\n'):
        if platform.system().lower() == 'windows':
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
        else:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
        if match:
            ip = match.group(1)
            try:
                ip_obj = ipaddress.IPv4Address(ip)
                if ip_obj in network:
                    arp_hosts.add(ip)
            except ValueError:
                continue

    # 准备要扫描的所有主机
    all_hosts = list(network.hosts())
    if exclude_ips:
        exclude_set = set(str(ip) for ip in exclude_ips)
        all_hosts = [ip for ip in all_hosts if str(ip) not in exclude_set]

    # 优先扫描ARP表中的设备
    online_hosts = []
    semaphore = asyncio.Semaphore(100)

    async def process_host(ip):
        async with semaphore:
            try:
                if await ping_host(str(ip)):
                    hostname = await get_hostname(str(ip))
                    mac = await get_mac_address(str(ip))
                    return {'ip': str(ip), 'hostname': hostname, 'mac': mac}
            except Exception:
                pass
        return None

    # 先扫描ARP表中的设备
    print("正在扫描ARP表中的设备...")
    arp_tasks = [process_host(ipaddress.IPv4Address(ip)) for ip in arp_hosts if ip not in (exclude_ips or [])]
    arp_results = await asyncio.gather(*arp_tasks)
    online_hosts.extend([r for r in arp_results if r])

    # 再扫描网络中的其他设备
    print("正在扫描网络中的其他设备...")
    other_hosts = [ip for ip in all_hosts if str(ip) not in arp_hosts]
    other_tasks = [process_host(ip) for ip in other_hosts]
    other_results = await asyncio.gather(*other_tasks)
    online_hosts.extend([r for r in other_results if r])

    return online_hosts, local_ip, network

def export_to_csv(online_hosts, csv_file='online_hosts.csv'):
    """将在线主机列表导出到CSV文件"""
    if not online_hosts:
        print("未发现在线主机，不导出CSV文件。")
        return

    # 按主机名排序（Unknown放最后）
    online_hosts.sort(key=lambda x: (x['hostname'] == 'Unknown', x['hostname']))

    try:
        # 使用UTF-8编码打开文件，确保中文显示正常
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(['序号', '主机名', 'IP地址', 'MAC地址'])
            # 写入数据
            for idx, host in enumerate(online_hosts, 1):
                writer.writerow([idx, host['hostname'], host['ip'], host['mac']])
        print(f"\n在线主机列表已导出到: {os.path.abspath(csv_file)}")
    except Exception as e:
        print(f"导出CSV文件时出错: {e}")

def print_results(online_hosts, csv_file=None):
    """以表格形式打印在线主机结果，并可选导出到CSV文件"""
    if not online_hosts:
        print("未发现在线主机。")
        return

    # 按主机名排序（Unknown放最后）
    online_hosts.sort(key=lambda x: (x['hostname'] == 'Unknown', x['hostname']))

    # 准备表格数据
    table_data = []
    for idx, host in enumerate(online_hosts, 1):
        table_data.append([idx, host['hostname'], host['ip'], host['mac']])

    # 打印表格
    print("\n在线主机列表:")
    print(tabulate(table_data, headers=['序号', '主机名', 'IP地址', 'MAC地址'], tablefmt='grid'))
    print(f"\n共发现 {len(online_hosts)} 台在线主机")

    # 导出到CSV文件
    if csv_file:
        export_to_csv(online_hosts, csv_file)
    else:
        # 默认不导出，除非指定了文件路径
        pass

async def main():
    print("局域网主机扫描工具")
    print("====================")

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='局域网主机扫描工具')
    parser.add_argument('-t', '--interval', type=int, help='定时执行间隔（秒），0表示只执行一次')
    parser.add_argument('-o', '--output', help='CSV文件输出路径，例如: online_hosts.csv')
    parser.add_argument('-e', '--exclude', nargs='+', help='要排除的IP地址列表，例如: 192.168.1.1 192.168.1.100')
    args = parser.parse_args()

    interval = args.interval if args.interval is not None else 0
    csv_file = args.output
    exclude_ips = args.exclude if args.exclude is not None else []

    first_run = True
    while True:
        if first_run and interval > 0:
            # 如果是第一次运行且设置了interval，则等待interval秒后再扫描
            print(f"\n将在 {interval} 秒后开始第一次扫描...")
            time.sleep(interval)
            first_run = False
        
        print("\n开始扫描，请稍候...")
        try:
            online_hosts, local_ip, network = await scan_network(exclude_ips)
            print(f"扫描完成，发现{len(online_hosts)}台在线主机")
        except Exception as e:
            print(f"扫描出错: {e}")
            return

        print(f"\n本地IP地址: {local_ip}")
        print(f"扫描网络范围: {network}")
        print_results(online_hosts, csv_file)

        if interval <= 0:
            break

        print(f"\n将在 {interval} 秒后再次扫描...")
        time.sleep(interval)

if __name__ == "__main__":
    try:
        # 检查tabulate是否已安装
        from tabulate import tabulate
    except ImportError:
        print("错误: 缺少必要的依赖包 'tabulate'。")
        print("请运行: pip install tabulate")
        exit(1)

    # 使用asyncio.run()来运行主函数
    asyncio.run(main())

#!/usr/bin/env python3
"""
Synology NAS MQTT数据发布器
适用于Synology DSM系统的NAS状态监控数据发布
"""

import json
import time
import subprocess
import re
import paho.mqtt.client as mqtt
from datetime import datetime

class SynologyPublisher:
    def __init__(self, mqtt_host="localhost", mqtt_port=1883, mqtt_user="", mqtt_password="", topic="nas/stats"):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.topic = topic
        self.client = None
        
    def connect_mqtt(self):
        """连接MQTT服务器"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT broker")
            else:
                print(f"Failed to connect, return code {rc}")
        
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        
        if self.mqtt_user and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_user, self.mqtt_password)
        
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
    
    def run_command(self, command):
        """执行系统命令"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return ""
    
    def get_cpu_info(self):
        """获取CPU信息"""
        # CPU使用率
        cpu_usage = self.run_command("cat /proc/stat | grep '^cpu ' | awk '{usage=($2+$4)*100/($2+$3+$4+$5)} END {print usage}'")
        
        # CPU温度
        cpu_temp = self.run_command("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
        if cpu_temp:
            cpu_temp = float(cpu_temp) / 1000
        else:
            cpu_temp = 0
        
        return {
            "usage": float(cpu_usage) if cpu_usage else 0,
            "temperature": cpu_temp
        }
    
    def get_memory_info(self):
        """获取内存信息"""
        meminfo = self.run_command("cat /proc/meminfo")
        
        total = 0
        available = 0
        
        for line in meminfo.split('\n'):
            if 'MemTotal:' in line:
                total = int(re.findall(r'\d+', line)[0]) * 1024
            elif 'MemAvailable:' in line:
                available = int(re.findall(r'\d+', line)[0]) * 1024
        
        used = total - available
        usage_percent = (used / total) * 100 if total > 0 else 0
        
        return {
            "usage": usage_percent,
            "temperature": 35.0,  # 模拟温度
            "total": total,
            "used": used,
            "available": available
        }
    
    def get_storage_info(self):
        """获取存储信息"""
        # 获取根分区信息
        df_output = self.run_command("df -B1 /")
        lines = df_output.split('\n')
        
        if len(lines) > 1:
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])
        else:
            total = used = free = 0
        
        # 获取磁盘状态（模拟）
        disks = []
        for i in range(1, 7):
            # 在真实环境中，这里应该查询实际的磁盘状态
            status = "normal"  # 可以是 "normal", "warning", "error"
            disks.append({"id": f"hdd{i}", "status": status})
        
        return {
            "capacity": total,
            "used": used,
            "free": free,
            "disks": disks
        }
    
    def get_network_info(self):
        """获取网络信息"""
        # 获取网络接口统计
        net_stats = self.run_command("cat /proc/net/dev | grep eth0")
        
        if net_stats:
            parts = net_stats.split()
            rx_bytes = int(parts[1])  # 接收字节
            tx_bytes = int(parts[9])  # 发送字节
            
            # 这里应该计算速率，简化处理返回固定值
            return {
                "upload": tx_bytes,
                "download": rx_bytes
            }
        
        return {
            "upload": 0,
            "download": 0
        }
    
    def get_system_info(self):
        """获取系统信息"""
        hostname = self.run_command("hostname")
        ip = self.run_command("hostname -I | awk '{print $1}'")
        
        return {
            "hostname": hostname or "Synology-NAS",
            "ip": ip or "192.168.1.100"
        }
    
    def collect_data(self):
        """收集所有数据"""
        system_info = self.get_system_info()
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        storage_info = self.get_storage_info()
        network_info = self.get_network_info()
        
        return {
            "hostname": system_info["hostname"],
            "ip": system_info["ip"],
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_info,
            "memory": memory_info,
            "storage": storage_info,
            "network": network_info
        }
    
    def publish_data(self):
        """发布数据"""
        data = self.collect_data()
        json_data = json.dumps(data)
        
        result = self.client.publish(self.topic, json_data)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Published: CPU {data['cpu']['usage']:.1f}%, RAM {data['memory']['usage']:.1f}%")
        else:
            print(f"Publish failed: {result.rc}")
    
    def run(self, interval=5):
        """运行发布器"""
        print("Starting Synology NAS Publisher...")
        self.connect_mqtt()
        
        try:
            while True:
                self.publish_data()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()

if __name__ == "__main__":
    # 配置参数
    MQTT_HOST = "192.168.1.10"  # 替换为您的MQTT服务器IP
    MQTT_PORT = 1883
    MQTT_USER = ""  # 如果需要认证
    MQTT_PASSWORD = ""  # 如果需要认证
    TOPIC = "nas/stats"
    INTERVAL = 5  # 发布间隔（秒）
    
    publisher = SynologyPublisher(MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, TOPIC)
    publisher.run(INTERVAL)
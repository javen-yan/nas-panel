#!/usr/bin/env python3
"""
NAS数据MQTT发布器
用于发布NAS系统状态数据到MQTT服务器，供ESP32 NAS面板订阅显示
"""

import json
import time
import random
import psutil
import socket
import paho.mqtt.client as mqtt
from datetime import datetime
import argparse

class NASPublisher:
    def __init__(self, mqtt_host="localhost", mqtt_port=1883, mqtt_user="", mqtt_password="", topic="nas/stats"):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.topic = topic
        self.client = None
        self.hostname = socket.gethostname()
        self.ip = self.get_local_ip()
        
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def connect_mqtt(self):
        """连接MQTT服务器"""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            else:
                print(f"Failed to connect to MQTT broker, return code {rc}")
        
        def on_disconnect(client, userdata, rc):
            print("Disconnected from MQTT broker")
        
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        
        if self.mqtt_user and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_user, self.mqtt_password)
        
        try:
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Error connecting to MQTT: {e}")
            return False
    
    def get_system_stats(self):
        """获取系统状态信息"""
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_temp = 45 + random.uniform(-5, 15)  # 模拟温度
        
        # 内存信息
        memory = psutil.virtual_memory()
        ram_usage = memory.percent
        ram_temp = 35 + random.uniform(-3, 10)  # 模拟温度
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        capacity = disk.total
        used = disk.used
        
        # 网络信息
        net_io = psutil.net_io_counters()
        upload_speed = random.uniform(1024*1024, 10*1024*1024)  # 1MB-10MB/s
        download_speed = random.uniform(5*1024*1024, 50*1024*1024)  # 5MB-50MB/s
        
        # 磁盘状态（模拟）
        disk_statuses = []
        for i in range(6):
            status = random.choice(["normal", "normal", "normal", "warning", "error"])
            disk_statuses.append({"id": f"hdd{i+1}", "status": status})
        
        return {
            "hostname": self.hostname,
            "ip": self.ip,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage": round(cpu_percent, 1),
                "temperature": round(cpu_temp, 1)
            },
            "memory": {
                "usage": round(ram_usage, 1),
                "temperature": round(ram_temp, 1),
                "total": memory.total,
                "used": memory.used,
                "available": memory.available
            },
            "storage": {
                "capacity": capacity,
                "used": used,
                "free": disk.free,
                "disks": disk_statuses
            },
            "network": {
                "upload": upload_speed,
                "download": download_speed
            }
        }
    
    def publish_data(self):
        """发布数据到MQTT"""
        if not self.client:
            print("MQTT client not connected")
            return False
        
        try:
            data = self.get_system_stats()
            json_data = json.dumps(data)
            
            result = self.client.publish(self.topic, json_data)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published data: CPU {data['cpu']['usage']}%, RAM {data['memory']['usage']}%")
                return True
            else:
                print(f"Failed to publish data, error code: {result.rc}")
                return False
        except Exception as e:
            print(f"Error publishing data: {e}")
            return False
    
    def run(self, interval=5):
        """运行发布器"""
        print(f"Starting NAS Publisher...")
        print(f"Hostname: {self.hostname}")
        print(f"IP: {self.ip}")
        print(f"MQTT: {self.mqtt_host}:{self.mqtt_port}")
        print(f"Topic: {self.topic}")
        print(f"Update interval: {interval} seconds")
        
        if not self.connect_mqtt():
            return
        
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

def main():
    parser = argparse.ArgumentParser(description='NAS MQTT Publisher')
    parser.add_argument('--host', default='localhost', help='MQTT broker host')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--user', default='', help='MQTT username')
    parser.add_argument('--password', default='', help='MQTT password')
    parser.add_argument('--topic', default='nas/stats', help='MQTT topic')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    publisher = NASPublisher(
        mqtt_host=args.host,
        mqtt_port=args.port,
        mqtt_user=args.user,
        mqtt_password=args.password,
        topic=args.topic
    )
    
    publisher.run(args.interval)

if __name__ == "__main__":
    main()
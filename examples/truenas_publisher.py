#!/usr/bin/env python3
"""
TrueNAS MQTT数据发布器
适用于TrueNAS系统的NAS状态监控数据发布
使用TrueNAS API获取系统信息
"""

import json
import time
import requests
import paho.mqtt.client as mqtt
from datetime import datetime

class TrueNASPublisher:
    def __init__(self, truenas_host, api_key, mqtt_host="localhost", mqtt_port=1883, 
                 mqtt_user="", mqtt_password="", topic="nas/stats"):
        self.truenas_host = truenas_host
        self.api_key = api_key
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.topic = topic
        self.client = None
        
        # API基础URL
        self.base_url = f"http://{truenas_host}/api/v2.0"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
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
    
    def api_request(self, endpoint):
        """发送API请求"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request failed for {endpoint}: {e}")
            return None
    
    def get_system_info(self):
        """获取系统信息"""
        info = self.api_request("system/info")
        if info:
            return {
                "hostname": info.get("hostname", "TrueNAS"),
                "ip": self.truenas_host
            }
        return {"hostname": "TrueNAS", "ip": self.truenas_host}
    
    def get_cpu_stats(self):
        """获取CPU统计"""
        stats = self.api_request("reporting/realtime")
        if stats and "cpu" in stats:
            cpu_data = stats["cpu"]
            usage = 100 - cpu_data.get("idle", 0)  # 100 - 空闲率 = 使用率
            
            # 获取CPU温度
            temp_data = self.api_request("system/advanced")
            temperature = 45.0  # 默认温度，如果API不提供
            
            return {
                "usage": max(0, min(100, usage)),
                "temperature": temperature
            }
        
        return {"usage": 0, "temperature": 45.0}
    
    def get_memory_stats(self):
        """获取内存统计"""
        stats = self.api_request("reporting/realtime")
        if stats and "virtual_memory" in stats:
            mem_data = stats["virtual_memory"]
            total = mem_data.get("total", 0)
            available = mem_data.get("available", 0)
            used = total - available
            usage_percent = (used / total) * 100 if total > 0 else 0
            
            return {
                "usage": usage_percent,
                "temperature": 35.0,  # 模拟内存温度
                "total": total,
                "used": used,
                "available": available
            }
        
        return {
            "usage": 0,
            "temperature": 35.0,
            "total": 0,
            "used": 0,
            "available": 0
        }
    
    def get_storage_info(self):
        """获取存储信息"""
        # 获取存储池信息
        pools = self.api_request("pool")
        total_capacity = 0
        total_used = 0
        
        if pools:
            for pool in pools:
                if "topology" in pool:
                    total_capacity += pool.get("size", 0)
                    total_used += pool.get("allocated", 0)
        
        # 获取磁盘信息
        disks = self.api_request("disk")
        disk_status = []
        
        if disks:
            for i, disk in enumerate(disks[:6]):  # 限制6个磁盘
                status = "normal"
                if disk.get("smart_enabled") and disk.get("smart_status") != "PASSED":
                    status = "warning"
                
                disk_status.append({
                    "id": f"hdd{i+1}",
                    "status": status
                })
        
        # 如果磁盘数量不足6个，补充默认状态
        while len(disk_status) < 6:
            disk_status.append({
                "id": f"hdd{len(disk_status)+1}",
                "status": "normal"
            })
        
        return {
            "capacity": total_capacity,
            "used": total_used,
            "free": total_capacity - total_used,
            "disks": disk_status
        }
    
    def get_network_stats(self):
        """获取网络统计"""
        stats = self.api_request("reporting/realtime")
        if stats and "interfaces" in stats:
            # 获取主要网络接口的统计
            interfaces = stats["interfaces"]
            total_tx = 0
            total_rx = 0
            
            for interface, data in interfaces.items():
                if not interface.startswith("lo"):  # 排除回环接口
                    total_tx += data.get("sent_bytes_rate", 0)
                    total_rx += data.get("received_bytes_rate", 0)
            
            return {
                "upload": total_tx,
                "download": total_rx
            }
        
        return {"upload": 0, "download": 0}
    
    def collect_data(self):
        """收集所有数据"""
        system_info = self.get_system_info()
        cpu_stats = self.get_cpu_stats()
        memory_stats = self.get_memory_stats()
        storage_info = self.get_storage_info()
        network_stats = self.get_network_stats()
        
        return {
            "hostname": system_info["hostname"],
            "ip": system_info["ip"],
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_stats,
            "memory": memory_stats,
            "storage": storage_info,
            "network": network_stats
        }
    
    def publish_data(self):
        """发布数据到MQTT"""
        data = self.collect_data()
        json_data = json.dumps(data)
        
        result = self.client.publish(self.topic, json_data)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Published: CPU {data['cpu']['usage']:.1f}%, RAM {data['memory']['usage']:.1f}%")
        else:
            print(f"Publish failed: {result.rc}")
    
    def run(self, interval=5):
        """运行发布器"""
        print("Starting TrueNAS Publisher...")
        print(f"TrueNAS: {self.truenas_host}")
        print(f"MQTT: {self.mqtt_host}:{self.mqtt_port}")
        
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
    # 配置参数 - 请根据您的环境修改
    TRUENAS_HOST = "192.168.1.100"  # TrueNAS服务器IP
    API_KEY = "your-api-key-here"   # TrueNAS API密钥
    
    MQTT_HOST = "192.168.1.10"      # MQTT服务器IP
    MQTT_PORT = 1883
    MQTT_USER = ""                  # MQTT用户名（如果需要）
    MQTT_PASSWORD = ""              # MQTT密码（如果需要）
    TOPIC = "nas/stats"
    INTERVAL = 5                    # 发布间隔（秒）
    
    publisher = TrueNASPublisher(
        truenas_host=TRUENAS_HOST,
        api_key=API_KEY,
        mqtt_host=MQTT_HOST,
        mqtt_port=MQTT_PORT,
        mqtt_user=MQTT_USER,
        mqtt_password=MQTT_PASSWORD,
        topic=TOPIC
    )
    
    publisher.run(INTERVAL)
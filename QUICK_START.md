# NAS Panel 快速开始指南

## 项目概述

这是一个基于ESP32和TFT显示屏的NAS监控面板项目，通过MQTT协议实时显示NAS系统状态。界面设计仿照现代化的NAS监控界面，支持显示：

- 📊 实时系统状态（CPU、内存使用率和温度）
- 💾 存储容量和磁盘状态
- 🌐 网络上下行速率
- 🏠 主机信息（名称、IP地址）

## 快速部署

### 1. 硬件准备

**必需组件：**
- ESP32开发板
- 2.8寸/3.2寸 ILI9341 TFT显示屏 (240x320)
- 杜邦线若干

**接线对照：**
```
ESP32    →    TFT屏幕
GPIO23   →    MOSI
GPIO18   →    SCK  
GPIO19   →    MISO
GPIO15   →    CS
GPIO2    →    DC
GPIO4    →    RST
3.3V     →    VCC
GND      →    GND
```

### 2. 软件环境

**选项A：使用PlatformIO（推荐）**
```bash
# 安装PlatformIO
pip install platformio

# 编译并上传
pio run --target upload

# 监视串口输出
pio device monitor
```

**选项B：使用Arduino IDE**
1. 安装ESP32开发板支持
2. 安装所需库（见platformio.ini中的lib_deps）
3. 打开src/main.cpp编译上传

### 3. 首次配置

**步骤1：WiFi配网**
1. ESP32启动后创建热点"NAS-Panel"
2. 手机连接热点，访问192.168.4.1
3. 选择WiFi网络并输入密码

**步骤2：MQTT配置**
1. 记录ESP32获得的IP地址
2. 浏览器访问该IP地址
3. 配置MQTT服务器信息：
   - 服务器IP地址
   - 端口号（默认1883）
   - 用户名密码（可选）
   - 主题名称（默认"nas/stats"）

### 4. 数据发布设置

**方式1：使用通用Python脚本**
```bash
# 安装依赖
pip install psutil paho-mqtt

# 运行数据发布器
python mqtt_publisher.py --host YOUR_MQTT_IP --topic nas/stats
```

**方式2：使用Docker部署**
```bash
# 启动MQTT服务器和数据发布器
docker-compose up -d
```

**方式3：集成到现有NAS系统**
- Synology NAS: 使用 `examples/synology_publisher.py`
- TrueNAS: 使用 `examples/truenas_publisher.py`

## 数据格式

MQTT消息采用JSON格式：
```json
{
  "hostname": "My-NAS",
  "ip": "192.168.1.100",
  "cpu": {"usage": 35.5, "temperature": 45.2},
  "memory": {"usage": 67.8, "temperature": 38.1},
  "storage": {"capacity": 32000000000000, "used": 18000000000000},
  "network": {"upload": 2812000, "download": 9400000}
}
```

## 故障排除

### 常见问题

**显示屏无显示**
- 检查接线是否正确
- 确认显示屏型号为ILI9341
- 检查电源供应是否稳定

**WiFi连接失败**
- 确认WiFi密码正确
- 检查信号强度
- 尝试重启设备重新配网

**MQTT无数据**
- 确认MQTT服务器地址正确
- 检查主题名称是否匹配
- 验证数据发布端是否正常运行

**性能优化**
- 调整数据更新频率（默认5秒）
- 根据需要修改显示刷新间隔
- 优化MQTT消息大小

### 调试模式

查看详细日志：
```bash
pio device monitor --baud 115200
```

## 自定义配置

### 修改显示样式
编辑 `src/main.cpp` 中的颜色定义：
```cpp
#define COLOR_PRIMARY       0x1E3A8A  // 主色调
#define COLOR_SUCCESS       0x10B981  // 成功色
#define COLOR_WARNING       0xF59E0B  // 警告色
#define COLOR_DANGER        0xEF4444  // 危险色
```

### 调整更新频率
修改 `displayUpdateInterval` 变量：
```cpp
const unsigned long displayUpdateInterval = 1000; // 毫秒
```

### 自定义MQTT主题
在Web配置界面或代码中修改主题名称。

## 技术支持

- 项目文档：README.md
- 示例代码：examples/ 目录
- 配置文件：platformio.ini

## 许可证

MIT License - 详见 LICENSE 文件
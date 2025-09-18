# NAS Panel - ESP32 NAS监控显示屏

基于ESP32和xtouch显示屏的NAS系统监控面板，通过MQTT协议实时显示NAS系统状态。

![NAS Panel Interface](design.png)

## 功能特性

- ✅ WiFi配网功能（基于WiFiManager）
- ✅ MQTT客户端连接
- ✅ 实时显示NAS系统信息：
  - 主机名称和IP地址
  - CPU使用率和温度
  - 内存使用率和温度
  - 存储容量和使用情况
  - 磁盘状态指示（HDD1-6, M.2 1-2）
  - 网络上下行速率
- ✅ Web配置界面
- ✅ 现代化UI设计

## 硬件要求

### ESP32开发板
- ESP32-WROOM-32或兼容开发板
- 至少4MB Flash存储

### 显示屏
- 2.8寸或3.2寸ILI9341 TFT显示屏
- 分辨率：240x320像素
- 支持SPI接口

### 接线图

| ESP32引脚 | TFT显示屏 | 功能 |
|-----------|-----------|------|
| GPIO23    | MOSI      | SPI数据 |
| GPIO18    | SCK       | SPI时钟 |
| GPIO19    | MISO      | SPI数据 |
| GPIO15    | CS        | 片选 |
| GPIO2     | DC        | 数据/命令 |
| GPIO4     | RST       | 复位 |
| 3.3V      | VCC       | 电源 |
| GND       | GND       | 地线 |

## 软件环境

### 开发环境
- [PlatformIO](https://platformio.org/) + VSCode
- 或者 [Arduino IDE](https://www.arduino.cc/en/software)

### 依赖库
- TFT_eSPI - 显示屏驱动
- WiFiManager - WiFi配网
- PubSubClient - MQTT客户端
- ArduinoJson - JSON解析
- ESPAsyncWebServer - Web服务器

## 安装和配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd nas-panel
```

### 2. 使用PlatformIO编译上传
```bash
# 安装PlatformIO
pip install platformio

# 编译项目
pio run

# 上传到ESP32
pio run --target upload

# 查看串口输出
pio device monitor
```

### 3. 首次配置

1. **WiFi配置**：
   - ESP32启动后会创建热点"NAS-Panel"
   - 连接热点，浏览器访问192.168.4.1
   - 选择WiFi网络并输入密码

2. **MQTT配置**：
   - WiFi连接成功后，访问ESP32的IP地址
   - 配置MQTT服务器信息：
     - MQTT服务器IP
     - 端口（默认1883）
     - 用户名和密码（可选）
     - 主题（默认"nas/stats"）

### 4. 服务端数据发布

#### 方式一：使用Python脚本
```bash
# 安装依赖
pip install -r requirements.txt

# 运行数据发布器
python mqtt_publisher.py --host YOUR_MQTT_SERVER --topic nas/stats
```

#### 方式二：集成到现有NAS系统
根据您的NAS系统（如Synology、QNAP、TrueNAS等），创建脚本定期发布以下JSON格式数据：

```json
{
  "hostname": "NAS-Server",
  "ip": "192.168.1.100",
  "timestamp": "2023-12-01T22:58:00",
  "cpu": {
    "usage": 35.5,
    "temperature": 45.2
  },
  "memory": {
    "usage": 67.8,
    "temperature": 38.1,
    "total": 17179869184,
    "used": 11659091968
  },
  "storage": {
    "capacity": 32000000000000,
    "used": 18000000000000,
    "disks": [
      {"id": "hdd1", "status": "normal"},
      {"id": "hdd2", "status": "normal"},
      {"id": "hdd3", "status": "warning"},
      {"id": "hdd4", "status": "normal"},
      {"id": "hdd5", "status": "error"},
      {"id": "hdd6", "status": "normal"}
    ]
  },
  "network": {
    "upload": 2812000,
    "download": 9400000
  }
}
```

## 配置文件

### platformio.ini
项目已预配置所有必要的库依赖和编译选项。如需修改显示屏引脚，请调整`build_flags`部分。

### 显示屏配置
默认配置适用于ILI9341驱动的240x320显示屏。如使用其他显示屏，请修改：
- `TFT_WIDTH` 和 `TFT_HEIGHT`
- 相应的驱动宏定义
- 引脚配置

## 故障排除

### 常见问题

1. **显示屏无显示**
   - 检查接线是否正确
   - 确认显示屏驱动型号
   - 检查电源供应

2. **WiFi连接失败**
   - 确认WiFi密码正确
   - 检查信号强度
   - 重启设备重新配网

3. **MQTT连接失败**
   - 确认MQTT服务器地址和端口
   - 检查网络连通性
   - 验证用户名密码

4. **数据不更新**
   - 检查MQTT主题是否匹配
   - 确认数据发布端正常运行
   - 查看串口输出调试信息

### 调试模式
通过串口监视器查看详细日志：
```bash
pio device monitor --baud 115200
```

## 自定义开发

### 修改显示界面
主要显示函数位于`src/main.cpp`：
- `drawNASPanel()` - 主界面绘制
- `drawProgressBar()` - 进度条绘制
- `drawDiskStatus()` - 磁盘状态显示
- `drawNetworkSpeed()` - 网络速度显示

### 添加新功能
1. 修改NAS数据结构 `struct NASData`
2. 更新MQTT解析逻辑 `mqttCallback()`
3. 添加相应的显示函数
4. 更新数据发布脚本

### 颜色主题
在`main.cpp`顶部定义了颜色常量，可根据需要修改：
```cpp
#define COLOR_PRIMARY       0x1E3A8A  // 深蓝色
#define COLOR_SECONDARY     0x3B82F6  // 蓝色
#define COLOR_SUCCESS       0x10B981  // 绿色
// ...
```

## 许可证

MIT License - 详见 LICENSE 文件

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 更新日志

### v1.0.0
- 初始版本发布
- 基础NAS监控功能
- WiFi配网和MQTT连接
- 现代化UI设计
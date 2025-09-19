#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <SPIFFS.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>
#include <ESPmDNS.h>

// 显示屏相关
TFT_eSPI tft = TFT_eSPI();

// WiFi和MQTT客户端
WiFiClient espClient;
PubSubClient mqttClient(espClient);
AsyncWebServer server(80);

// NAS数据结构
struct NASData {
    String hostname;
    String ip;
    float cpuUsage;
    float cpuTemp;
    float ramUsage;
    float ramTemp;
    float capacity;
    float usedSpace;
    String diskStatus[6];
    float networkUpload;
    float networkDownload;
    unsigned long lastUpdate;
};

NASData nasData;

// 配置参数
String mqttServer = "";
int mqttPort = 1883;
String mqttUser = "";
String mqttPassword = "";
String mqttTopic = "nas/panel/data";

// 显示相关变量
unsigned long lastDisplayUpdate = 0;
const unsigned long displayUpdateInterval = 1000; // 1秒更新一次显示
bool dataReceived = false;

// 颜色定义
#define COLOR_BACKGROUND    0x0000  // 黑色
#define COLOR_PRIMARY       0x1E3A8A  // 深蓝色
#define COLOR_SECONDARY     0x3B82F6  // 蓝色
#define COLOR_SUCCESS       0x10B981  // 绿色
#define COLOR_WARNING       0xF59E0B  // 橙色
#define COLOR_DANGER        0xEF4444  // 红色
#define COLOR_TEXT_PRIMARY  0xFFFF   // 白色
#define COLOR_TEXT_SECONDARY 0xD1D5DB // 灰色
#define COLOR_CARD_BG       0x1F2937  // 深灰色

void initDisplay();
void initWiFi();
void initMQTT();
void initWebServer();
bool validateMQTTConfig();
void connectMQTT();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void updateDisplay();
void drawNASPanel();
void drawProgressBar(int x, int y, int w, int h, float percentage, uint16_t color);
void drawDiskStatus();
void drawNetworkSpeed();
void saveConfig();
void loadConfig();
String formatBytes(float bytes);

void setup() {
    Serial.begin(115200);
    Serial.println("NAS Panel Starting...");
    
    // 初始化SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS Mount Failed");
        // 显示错误信息
        tft.fillScreen(COLOR_BACKGROUND);
        tft.setTextColor(COLOR_DANGER);
        tft.setTextSize(1);
        tft.drawString("SPIFFS Error", 80, 100);
        tft.drawString("Restarting...", 70, 120);
        delay(3000);
        ESP.restart();
    }
    
    // 加载配置
    loadConfig();
    
    // 初始化显示屏
    initDisplay();
    
    // 显示启动画面
    tft.fillScreen(COLOR_BACKGROUND);
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.setTextSize(2);
    tft.drawString("NAS Panel", 60, 100);
    tft.setTextSize(1);
    tft.drawString("Initializing...", 80, 140);
    
    // 初始化WiFi
    initWiFi();
    
    // 初始化Web服务器
    initWebServer();
    
    // 初始化MQTT
    initMQTT();
    
    Serial.println("Setup complete");
    
    // 清屏准备显示主界面
    tft.fillScreen(COLOR_BACKGROUND);
}

void loop() {
    // 维持MQTT连接
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();
    
    // 更新显示
    if (millis() - lastDisplayUpdate > displayUpdateInterval) {
        updateDisplay();
        lastDisplayUpdate = millis();
    }
    
    delay(100);
}

void initDisplay() {
    tft.init();
    tft.setRotation(0); // 竖屏模式
    tft.fillScreen(COLOR_BACKGROUND);
    
    Serial.println("Display initialized");
}

void initWiFi() {
    WiFiManager wm;
    
    // 显示WiFi配置状态
    tft.fillScreen(COLOR_BACKGROUND);
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.setTextSize(1);
    tft.drawString("WiFi Configuration", 50, 80);
    tft.drawString("Connect to: NAS-Panel", 30, 100);
    tft.drawString("to configure WiFi", 50, 120);
    
    // 设置WiFiManager
    wm.setAPCallback([](WiFiManager *myWiFiManager) {
        Serial.println("Entered config mode");
        tft.fillRect(0, 140, 240, 20, COLOR_BACKGROUND);
        tft.drawString("Config mode active", 50, 140);
    });
    
    wm.setSaveConfigCallback([]() {
        Serial.println("Should save config");
    });
    
    // 自动连接WiFi，如果失败则启动配置门户
    if (!wm.autoConnect("NAS-Panel")) {
        Serial.println("Failed to connect and hit timeout");
        // 显示连接失败信息
        tft.fillScreen(COLOR_BACKGROUND);
        tft.setTextColor(COLOR_DANGER);
        tft.setTextSize(1);
        tft.drawString("WiFi Connection Failed", 40, 100);
        tft.drawString("Restarting...", 80, 120);
        delay(3000);
        ESP.restart();
    }
    
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // 显示连接成功
    tft.fillScreen(COLOR_BACKGROUND);
    tft.drawString("WiFi Connected!", 60, 100);
    tft.drawString("IP: " + WiFi.localIP().toString(), 40, 120);
    delay(2000);
}

void initMQTT() {
    if (mqttServer.length() > 0) {
        mqttClient.setServer(mqttServer.c_str(), mqttPort);
        mqttClient.setCallback(mqttCallback);
        connectMQTT();
    }
}

bool validateMQTTConfig() {
    if (mqttServer.length() == 0) return false;
    if (mqttPort < 1 || mqttPort > 65535) return false;
    return true;
}

void connectMQTT() {
    if (!validateMQTTConfig()) {
        Serial.println("Invalid MQTT configuration");
        return;
    }
    
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        String clientId = "NASPanel-";
        clientId += String(random(0xffff), HEX);
        
        if (mqttClient.connect(clientId.c_str(), mqttUser.c_str(), mqttPassword.c_str())) {
            Serial.println("connected");
            mqttClient.subscribe(mqttTopic.c_str());
            Serial.println("Subscribed to: " + mqttTopic);
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" try again in 5 seconds");
            delay(5000);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    
    Serial.println("Received: " + message);
    
    // 解析JSON数据
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, message);
    
    if (error) {
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
        return;
    }
    
    // 更新NAS数据
    nasData.hostname = doc["hostname"].as<String>();
    nasData.ip = doc["ip"].as<String>();
    nasData.cpuUsage = doc["cpu"]["usage"];
    nasData.cpuTemp = doc["cpu"]["temperature"];
    nasData.ramUsage = doc["memory"]["usage"];
    nasData.ramTemp = doc["memory"]["temperature"];
    nasData.capacity = doc["storage"]["capacity"];
    nasData.usedSpace = doc["storage"]["used"];
    nasData.networkUpload = doc["network"]["upload"];
    nasData.networkDownload = doc["network"]["download"];
    
    // 更新磁盘状态
    JsonArray disks = doc["storage"]["disks"];
    for (int i = 0; i < min(6, (int)disks.size()); i++) {
        nasData.diskStatus[i] = disks[i]["status"].as<String>();
    }
    
    nasData.lastUpdate = millis();
    dataReceived = true;
}

void updateDisplay() {
    if (!dataReceived) {
        // 显示等待数据
        tft.fillScreen(COLOR_BACKGROUND);
        tft.setTextColor(COLOR_TEXT_SECONDARY);
        tft.setTextSize(1);
        tft.drawString("Waiting for data...", 60, 150);
        if (mqttServer.length() == 0) {
            tft.drawString("Please configure MQTT", 40, 170);
            tft.drawString("via web interface", 60, 190);
        }
        return;
    }
    
    drawNASPanel();
}

void drawNASPanel() {
    tft.fillScreen(COLOR_BACKGROUND);
    
    // 绘制标题栏
    tft.fillRect(0, 0, 240, 40, COLOR_PRIMARY);
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.setTextSize(1);
    tft.drawString("NAS Monitor", 10, 10);
    tft.drawString(nasData.hostname, 10, 25);
    
    // 绘制时间和IP
    tft.setTextColor(COLOR_TEXT_SECONDARY);
    // 显示当前时间
    unsigned long currentTime = millis() / 1000;
    int hours = (currentTime / 3600) % 24;
    int minutes = (currentTime / 60) % 60;
    String timeStr = String(hours) + ":" + (minutes < 10 ? "0" : "") + String(minutes);
    tft.drawString(timeStr, 180, 10);
    tft.drawString(nasData.ip, 140, 25);
    
    // 绘制容量信息
    int yPos = 50;
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.setTextSize(2);
    
    // 容量百分比
    float capacityPercent = (nasData.usedSpace / nasData.capacity) * 100;
    tft.drawString(String((int)capacityPercent) + "%", 30, yPos);
    
    tft.setTextSize(1);
    tft.drawString("Capacity", 30, yPos + 25);
    tft.drawString(formatBytes(nasData.capacity), 30, yPos + 40);
    tft.drawString("/ " + formatBytes(nasData.usedSpace), 30, yPos + 55);
    
    // CPU使用率条
    yPos = 120;
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.drawString("CPU", 30, yPos);
    tft.drawString(String((int)nasData.cpuUsage) + "%", 180, yPos);
    tft.drawString(String((int)nasData.cpuTemp) + "°C", 210, yPos);
    drawProgressBar(30, yPos + 15, 180, 8, nasData.cpuUsage, COLOR_SECONDARY);
    
    // RAM使用率条
    yPos = 150;
    tft.drawString("RAM", 30, yPos);
    tft.drawString(String((int)nasData.ramUsage) + "%", 180, yPos);
    tft.drawString(String((int)nasData.ramTemp) + "°C", 210, yPos);
    drawProgressBar(30, yPos + 15, 180, 8, nasData.ramUsage, COLOR_SECONDARY);
    
    // 绘制磁盘状态
    drawDiskStatus();
    
    // 绘制网络速度
    drawNetworkSpeed();
}

void drawProgressBar(int x, int y, int w, int h, float percentage, uint16_t color) {
    // 背景
    tft.fillRect(x, y, w, h, COLOR_CARD_BG);
    
    // 进度条
    int fillWidth = (w * percentage) / 100;
    uint16_t barColor = color;
    
    if (percentage > 80) barColor = COLOR_DANGER;
    else if (percentage > 60) barColor = COLOR_WARNING;
    else barColor = COLOR_SUCCESS;
    
    tft.fillRect(x, y, fillWidth, h, barColor);
    
    // 边框
    tft.drawRect(x, y, w, h, COLOR_TEXT_SECONDARY);
}

void drawDiskStatus() {
    int yPos = 190;
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    
    // 磁盘状态网格 - 只显示6个磁盘，避免数组越界
    String diskLabels[] = {"HDD 1", "HDD 2", "HDD 3", "HDD 4", "HDD 5", "HDD 6"};
    
    for (int i = 0; i < 6; i++) {
        int col = i % 2;
        int row = i / 2;
        int x = 30 + col * 90;
        int y = yPos + row * 25;
        
        // 绘制磁盘标签
        tft.setTextSize(1);
        tft.drawString(diskLabels[i], x, y);
        
        // 绘制状态指示器
        uint16_t statusColor = COLOR_SUCCESS;
        if (nasData.diskStatus[i] == "error") {
            statusColor = COLOR_DANGER;
        } else if (nasData.diskStatus[i] == "warning") {
            statusColor = COLOR_WARNING;
        }
        
        tft.fillCircle(x + 50, y + 5, 3, statusColor);
    }
}

void drawNetworkSpeed() {
    int yPos = 290;
    tft.setTextColor(COLOR_TEXT_PRIMARY);
    tft.setTextSize(1);
    
    // 上传速度
    tft.drawString("↑ " + formatBytes(nasData.networkUpload) + "/s", 30, yPos);
    
    // 下载速度  
    tft.drawString("↓ " + formatBytes(nasData.networkDownload) + "/s", 130, yPos);
}

String formatBytes(float bytes) {
    if (bytes < 1024) return String((int)bytes) + " B";
    else if (bytes < 1024 * 1024) return String(bytes / 1024, 1) + " KB";
    else if (bytes < 1024 * 1024 * 1024) return String(bytes / (1024 * 1024), 1) + " MB";
    else if (bytes < 1024L * 1024 * 1024 * 1024) return String(bytes / (1024 * 1024 * 1024), 1) + " GB";
    else return String(bytes / (1024L * 1024 * 1024 * 1024), 1) + " TB";
}

void initWebServer() {
    // 配置页面
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
        String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>NAS Panel Configuration</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        input, button { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; cursor: pointer; }
        button:hover { background: #0056b3; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NAS Panel Configuration</h1>
        <form id="configForm">
            <h3>MQTT Settings</h3>
            <input type="text" id="mqttServer" placeholder="MQTT Server IP" value=")" + mqttServer + R"(">
            <input type="number" id="mqttPort" placeholder="MQTT Port" value=")" + String(mqttPort) + R"(">
            <input type="text" id="mqttUser" placeholder="MQTT Username" value=")" + mqttUser + R"(">
            <input type="password" id="mqttPassword" placeholder="MQTT Password" value=")" + mqttPassword + R"(">
            <input type="text" id="mqttTopic" placeholder="MQTT Topic" value=")" + mqttTopic + R"(">
            <button type="submit">Save Configuration</button>
        </form>
        <div id="status"></div>
    </div>
    
    <script>
        document.getElementById('configForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const config = {
                mqttServer: document.getElementById('mqttServer').value,
                mqttPort: parseInt(document.getElementById('mqttPort').value),
                mqttUser: document.getElementById('mqttUser').value,
                mqttPassword: document.getElementById('mqttPassword').value,
                mqttTopic: document.getElementById('mqttTopic').value
            };
            
            fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            })
            .then(response => response.text())
            .then(data => {
                document.getElementById('status').innerHTML = '<div class="success">Configuration saved! Device will restart...</div>';
                setTimeout(() => location.reload(), 3000);
            })
            .catch(error => {
                document.getElementById('status').innerHTML = '<div class="error">Error saving configuration</div>';
            });
        });
    </script>
</body>
</html>
        )";
        request->send(200, "text/html", html);
    });
    
    // 保存配置
    server.on("/config", HTTP_POST, [](AsyncWebServerRequest *request){}, NULL, 
        [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total){
            DynamicJsonDocument doc(1024);
            DeserializationError error = deserializeJson(doc, (char*)data);
            
            if (error) {
                Serial.print("Config JSON parsing failed: ");
                Serial.println(error.c_str());
                request->send(400, "text/plain", "Invalid JSON");
                return;
            }
            
            mqttServer = doc["mqttServer"].as<String>();
            mqttPort = doc["mqttPort"];
            mqttUser = doc["mqttUser"].as<String>();
            mqttPassword = doc["mqttPassword"].as<String>();
            mqttTopic = doc["mqttTopic"].as<String>();
            
            saveConfig();
            request->send(200, "text/plain", "OK");
            
            delay(1000);
            ESP.restart();
        });
    
    server.begin();
    Serial.println("Web server started");
    Serial.println("Open http://" + WiFi.localIP().toString() + " to configure");
}

void saveConfig() {
    DynamicJsonDocument doc(1024);
    doc["mqttServer"] = mqttServer;
    doc["mqttPort"] = mqttPort;
    doc["mqttUser"] = mqttUser;
    doc["mqttPassword"] = mqttPassword;
    doc["mqttTopic"] = mqttTopic;
    
    File configFile = SPIFFS.open("/config.json", "w");
    if (configFile) {
        serializeJson(doc, configFile);
        configFile.close();
        Serial.println("Config saved");
    }
}

void loadConfig() {
    if (SPIFFS.exists("/config.json")) {
        File configFile = SPIFFS.open("/config.json", "r");
        if (configFile) {
            DynamicJsonDocument doc(1024);
            deserializeJson(doc, configFile);
            
            mqttServer = doc["mqttServer"].as<String>();
            mqttPort = doc["mqttPort"];
            mqttUser = doc["mqttUser"].as<String>();
            mqttPassword = doc["mqttPassword"].as<String>();
            mqttTopic = doc["mqttTopic"].as<String>();
            
            configFile.close();
            Serial.println("Config loaded");
        }
    }
}
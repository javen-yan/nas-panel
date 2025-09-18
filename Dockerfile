FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY mqtt_publisher.py .

# 设置环境变量
ENV MQTT_HOST=localhost
ENV MQTT_PORT=1883
ENV MQTT_TOPIC=nas/stats
ENV UPDATE_INTERVAL=5

# 启动命令
CMD python mqtt_publisher.py \
    --host ${MQTT_HOST} \
    --port ${MQTT_PORT} \
    --topic ${MQTT_TOPIC} \
    --interval ${UPDATE_INTERVAL}
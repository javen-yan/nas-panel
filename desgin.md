基于 xtouch 的显示屏和esp32 的联网配置, 制作一个 nas 显示屏幕， nas-panel 是可以烧录到esp32的程序， 程序除了xtouch的配网逻辑，关于nas-panel的显示，通过发现局域网或者配置ip和端口，连接到mqtt server 然后通过订阅 topic 显示一些内容

1. 主机的信息，名称，ip
2. cpu/内存 的使用情况，温度
3. 磁盘的使用情况， hdd/ssd 的磁盘状态
4. 网络上下行速率



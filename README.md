# HomeLab Infrastructure & IoT Edge Platform

A unified, containerized homelab architecture featuring edge routing, comprehensive observability, IoT sensor telemetry, and an on-premise audio machine learning detection pipeline designed for local area network (LAN) operations.

---

## 1. High-Level Architecture

```text
                          Incoming LAN Traffic
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        │                      Traefik v3                       │
        │    (Ingress Router, TLS Termination, Service Proxy)   │
        └───────────────────────────┬───────────────────────────┘
                                    │
       ┌────────────────────────────┼───────────────────────────┐
       │                            │                           │
       ▼                            ▼                           ▼
 [ Core Services ]          [ Observability ]            [ IoT & Edge AI ]
 • Homarr Dashboard         • Prometheus Engine          • ESP32 Audio AI Server
 • Home Assistant           • Grafana Dashboards         • ESP32 Temp Monitor
 • Pi-hole DNS Sinkhole     • Alertmanager               • Tuya Energy Exporters
 • Uptime Kuma Monitor      • Gotify Push Relay          • SmartTube ADB Bridge
 • MantisBT + MariaDB       • System Exporters           • AriaNg Web Client
 • Nginx HTTP/3 QUIC
```

---

## 2. Core Subsystems

### Edge Networking & Ingress
* **Traefik v3**: Primary LAN ingress controller managing HTTP/HTTPS reverse proxying, TLS termination, and path-based routing via Docker labels.
* **Nginx**: Fast static asset serving and system services dashboard configured with HTTP/3 QUIC and TLS 1.3 listeners.
* **Pi-hole**: Network-wide DNS sinkhole providing recursive DNS filtering, ad blocking, and local `.lan` resolution.

### Observability & Incident Pipeline
* **Prometheus**: Time-series metrics aggregator scraping host and container endpoints.
* **Grafana**: Dashboards for host utilization, container health, network latency, and energy metrics.
* **Alertmanager & Gotify**: Automated alerting pipeline dispatching notification webhooks to an on-premise Gotify push server.
* **Exporters**: Node Exporter, Ping Exporter, WireGuard Exporter, Speedtest Exporter.

### Embedded IoT & Edge Machine Learning
* **Doorbell Audio Detection**:
  * **Hardware**: ESP32-S3 with an INMP441 I2S MEMS microphone streaming raw audio via WebSocket.
  * **Inference Pipeline**: Python server running Google YAMNet AI classification alongside SciPy cross-correlation matching.
  * **Dispatch**: Triggers push alerts via Gotify and increments Prometheus telemetry counters.
* **Environmental Telemetry**: ESP32 DS18B20 1-Wire temperature monitoring scraped by a dedicated Prometheus client.
* **Tuya Exporters**: Standalone Prometheus exporters implemented in both Go and Python for smart plug power telemetry.

### Automation & Application Services
* **Home Assistant**: Local home automation engine.
* **SmartTube ADB Bridge**: Flask ADB relay service and Chrome extension for casting video intents directly to Android TV.
* **Aria2 & AriaNg**: Distributed multi-connection download daemon with AriaNg web client.
* **Portainer CE**: Docker container and network management web UI.
* **Uptime Kuma & Homarr**: Service health monitoring and homelab launchpad dashboard.
* **MantisBT**: Issue tracker backed by MariaDB configured with Docker Secrets.

---

## 3. Security & Secret Management

* **Docker Secrets**: Relational database credentials (MariaDB) are mounted via container tmpfs at `/run/secrets/`, keeping passwords out of process tables and `docker inspect` metadata.
* **Environment Variable Decoupling**: Services requiring runtime variables use local `.env` files with version-controlled `.env.example` templates.
* **Portable Submodules**: Relative submodule paths (`../aria2.git`) allow seamless anonymous cloning over HTTPS and authenticated cloning over SSH.

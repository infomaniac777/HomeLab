# HomeLab Infrastructure & IoT Edge Platform

<p align="left">
  <img src="https://img.shields.io/badge/Docker_Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/Traefik_v3-24A1C1?style=flat-square&logo=traefik&logoColor=white" alt="Traefik" />
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white" alt="Prometheus" />
  <img src="https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white" alt="Grafana" />
  <img src="https://img.shields.io/badge/Nginx_HTTP%2F3-009639?style=flat-square&logo=nginx&logoColor=white" alt="Nginx" />
  <img src="https://img.shields.io/badge/ESP32_S3-E7352C?style=flat-square&logo=espressif&logoColor=white" alt="ESP32" />
  <img src="https://img.shields.io/badge/Python_3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Go_1.23-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go" />
  <img src="https://img.shields.io/badge/MariaDB_Secrets-003545?style=flat-square&logo=mariadb&logoColor=white" alt="MariaDB" />
  <img src="https://img.shields.io/badge/Home_Assistant-41BDF5?style=flat-square&logo=homeassistant&logoColor=white" alt="Home Assistant" />
  <img src="https://img.shields.io/badge/Pi--hole-96060C?style=flat-square&logo=pi-hole&logoColor=white" alt="Pi-hole" />
</p>

A containerized, security-hardened homelab platform featuring dynamic LAN routing, end-to-end telemetry and observability, embedded microcontrollers, and real-time audio machine learning inference.

---

## Architecture Overview

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
 • Homarr Portal            • Prometheus Engine          • ESP32 Audio AI Server
 • Home Assistant           • Grafana Dashboards         • ESP32 Temp Telemetry
 • Pi-hole DNS Sinkhole     • Alertmanager Pipeline      • Tuya Energy Exporters
 • Uptime Kuma Health       • Gotify Push Webhooks       • SmartTube ADB Bridge
 • MantisBT + MariaDB       • System Metric Exporters    • AriaNg Web Client
 • Nginx HTTP/3 QUIC
```

---

## Service Catalog

| Tier | Service | Technology Stack | Transport / Ports | Role & Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Ingress** | **Traefik v3** | Go / Reverse Proxy | `:80`, `:443` (TCP) | LAN gateway, TLS termination, Docker label-driven dynamic service discovery |
| **Ingress** | **Nginx** | C / Web Server | `:443` (QUIC / UDP) | Static services portal with HTTP/3 QUIC and TLS 1.3 optimization |
| **Ingress** | **Pi-hole** | C / FTLDNS | `:53` (TCP/UDP) | Network-wide ad blocking, privacy sinkhole, and custom local `.lan` resolution |
| **Telemetry** | **Prometheus** | Go / Time Series DB | `:9090` | Metrics scraping engine with multi-target polling and alerting rule triggers |
| **Telemetry** | **Grafana** | TypeScript / Go | `:3000` | Unified visualization dashboards for host, containers, network, and power |
| **Telemetry** | **Alertmanager** | Go / Incident Router | `:9093` | Alert grouping, rate-limiting, and dispatch routing |
| **Telemetry** | **Gotify** | Go / WebSockets | `:3004` | On-premise self-hosted push notification server for mobile and desktop |
| **Edge AI** | **Doorbell Detect** | ESP32-S3 / C++ | WebSocket `:3003` | 16kHz PCM streaming from INMP441 I2S microphone to processing daemon |
| **Edge AI** | **Inference Engine** | Python / NumPy / SciPy | Port `:8000` | Real-time classification via Google YAMNet AI and cross-correlation matching |
| **IoT** | **Temp Telemetry** | ESP32 / C++ / Python | Port `:8700` | DS18B20 1-Wire temperature sensing with dedicated Prometheus exporter |
| **IoT** | **Tuya Exporters** | Go / Python | `:9999` / `:9091` | Prometheus exporters for local Tuya smart plug power and voltage scraping |
| **Platform** | **MantisBT** | PHP / Apache | Port `:4000` | Task and bug tracking backed by MariaDB using Docker Secrets |
| **Platform** | **Home Assistant** | Python | Port `:12000` | Local home automation orchestration and entity management |
| **Platform** | **AriaNg** | Apache / aria2c | `:6800` (JSON-RPC) | Distributed multi-protocol download acceleration engine with web frontend |
| **Platform** | **SmartTube ADB** | Python / Flask / Chrome | Port `:8123` | Chrome extension bridge dispatching video playback intents to Android TV |
| **Platform** | **Uptime Kuma** | Node.js / Vue | Port `:3002` | High-frequency uptime health checks and incident alerting |

---

## Technical Highlights

### 1. Ingress & Transport Optimization
* **Traefik v3 Dynamic Routing**: Automatic service discovery via container metadata labels—no manual upstream proxy configuration required when deploying new containers.
* **HTTP/3 QUIC on Nginx**: Configured with `listen 443 quic reuseport`, TLS 1.3 0-RTT session resumption, and Alt-Svc advertisement headers for high-efficiency mobile client connections.

### 2. End-to-End Incident Pipeline
```text
[ Exporters / Services ] ──scrape──> [ Prometheus ] ──alert──> [ Alertmanager ] ──webhook──> [ Gotify Bridge ] ──push──> [ Mobile Devices ]
```
* **Host & Protocol Exporters**:
  * Node Exporter: Host OS kernel metrics, memory utilization, disk I/O, and CPU states.
  * Ping Exporter: ICMP latency probing across gateway and upstream DNS resolvers.
  * WireGuard Exporter: Real-time cryptographic tunnel throughput and peer handshakes.
  * Speedtest Exporter: Automated periodic bandwidth benchmarking.

### 3. Embedded Edge AI & Audio Signal Processing
* **Hardware Interfacing**: ESP32-S3 firmware utilizes the ESP-IDF I2S peripheral driver in RX master mode to sample an INMP441 omnidirectional microphone at 16,000 Hz (16-bit mono).
* **Dual Inference Pipeline**:
  * **Deep Learning Mode**: Feeds incoming audio segments into Google YAMNet (MobileNet architecture trained on AudioSet) for sound classification.
  * **Signal Processing Mode**: Executes normalized cross-correlation against a calibrated template wave signal using SciPy, enabling sub-second signature detection with minimal latency.
* **Incident Dispatch**: Upon positive classification meeting confidence thresholds, the engine increments Prometheus counters and dispatches an emergency priority push alert via Gotify.

---

## Security Architecture

> [!NOTE]
> This repository demonstrates a production-grade container security posture suitable for sensitive on-premise environments.

* **Docker Secrets Implementation**:
  Database passwords (e.g. MariaDB in MantisBT) utilize Docker Compose secrets:
  ```yaml
  services:
    mysql:
      image: mariadb:latest
      secrets:
        - mysql_root_password
        - mysql_password
      environment:
        MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
        MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
  ```
  Secrets are mounted exclusively into memory (`/run/secrets/`), completely preventing credential leakage in `docker inspect` inspect JSON metadata and system environment tables.
* **Environment Variable Decoupling**: All tokens and application credentials are kept strictly out of source control using `.env.example` templates and comprehensive `.gitignore` rules.
* **Submodule Portability**: Uses relative Git submodule paths (`../aria2.git`) to support anonymous read access over HTTPS alongside authenticated SSH workflows.

---

## Quickstart & Local Setup

### 1. Environment Configuration
Initialize your local environment files from the committed templates:
```bash
cp Prometheus/.env.example Prometheus/.env
cp gotify/.env.example gotify/.env
cp piehole/.env.example piehole/.env
cp SmartTubeADBExtension/server/.env.example SmartTubeADBExtension/server/.env
cp ESP32/Doorbelldetect/server/.env.example ESP32/Doorbelldetect/server/.env
```

### 2. Docker Secrets Initialization
Populate your local database secret files:
```bash
cp mantis/secrets/mysql_root_password.txt.example mantis/secrets/mysql_root_password.txt
cp mantis/secrets/mysql_password.txt.example mantis/secrets/mysql_password.txt
```

### 3. Deploy Stack
```bash
# Launch Ingress Controller
docker compose -f traefik/docker-compose.yml up -d

# Launch Observability & Monitoring
docker compose -f Prometheus/docker-compose.yml up -d
docker compose -f grafana/docker-compose.yml up -d
docker compose -f uptime-kuma/docker-compose.yml up -d
```

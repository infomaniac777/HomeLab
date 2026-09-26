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

Production homelab infrastructure powering day-to-day containerized workloads, telemetry pipelines, embedded IoT sensor networks, and real-time edge audio AI on a dedicated, security-hardened Linux host on-prem.

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

## Key Engineering Pillars

### 1. Ingress & Edge Networking
* **Traefik v3 Reverse Proxy**: Label-driven dynamic container discovery with automated TLS termination and path-based routing.
* **HTTP/3 QUIC Gateway**: High-throughput Nginx reverse proxy with TLS 1.3 0-RTT session resumption for modern mobile clients.
* **DNS Sinkholing**: Pi-hole deployment handling network-wide ad blocking, privacy filtering, and internal `.lan` domain routing.

### 2. Full-Stack Observability & Incident Pipeline
* **Host & Network Telemetry**: Continuous monitoring across CPU, memory, disk I/O, ICMP round-trip latency, WireGuard VPN throughput, and network bandwidth.
* **Automated Alerting**: Alertmanager pipeline delivering instant push notifications to mobile devices via self-hosted Gotify instances.
* **Unified Visuals**: Grafana dashboards offering real-time visibility into infrastructure health and energy consumption.

### 3. Embedded Systems & Edge AI
* **Real-Time Audio Event Detection**:
  * **Microcontroller Layer**: ESP32-S3 firmware streaming 16kHz PCM audio from an INMP441 I2S MEMS microphone over WebSockets.
  * **Dual Inference Pipeline**: Python daemon evaluating incoming streams using **Google YAMNet deep learning** and sub-second **SciPy cross-correlation signature matching**.
  * **Autonomous Action**: Immediate dispatch of priority push notifications and Prometheus counter updates upon detection.
* **Custom Hardware Exporters**:
  * Standalone Prometheus exporters written in **Go** and **Python** to extract live power, voltage, and energy statistics from local Tuya smart plugs.
  * 1-Wire temperature sensing using DS18B20 microchips connected to an ESP32 with Prometheus scraping.

### 4. Container Security & Best Practices
* **Docker Secrets by Design**: Critical credentials (such as database passwords in MariaDB) are mounted as in-memory tmpfs files (`/run/secrets/`), completely preventing leakage via `docker inspect` metadata or process environment dumps.
* **Zero Credential Exposure**: Completely decoupled environment templates (`.env.example`) and comprehensive Git ignore hygiene.
* **Submodule Portability**: Uses relative Git submodule paths (`../aria2.git`) for universal anonymous and authenticated cloning.

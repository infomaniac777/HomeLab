const express = require('express');
const WebSocket = require('ws');
const promClient = require('prom-client');
const path = require('path');

// Initialize prometheus metrics
const tempGauge = new promClient.Gauge({
    name: 'esp32_temperature_celsius',
    help: 'Temperature reading from ESP32 sensor'
});

const connectedDevicesGauge = new promClient.Gauge({
    name: 'esp32_connected_devices',
    help: 'Number of ESP32 devices connected'
});

// Set initial value
connectedDevicesGauge.set(0);

// Setup Express and WebSocket
const app = express();
const wss = new WebSocket.Server({ noServer: true });

// Track state
let lastTemperature = null;
let lastUpdate = null;
let connectedClients = new Set();

// Connection handler
wss.on('connection', (ws, req) => {
    const clientIP = req.socket.remoteAddress;
    connectedClients.add(ws);
    connectedDevicesGauge.set(connectedClients.size);
    
    console.log(`[${new Date().toLocaleString()}] New connection from ${clientIP}`);
    console.log(`Connected clients: ${connectedClients.size}`);

    // Message handler
    ws.on('message', (data) => {
        try {
            const message = JSON.parse(data);
            if (message.temperature !== undefined) {
                lastTemperature = message.temperature;
                lastUpdate = new Date().toLocaleString();
                tempGauge.set(message.temperature);
                console.log(`[${lastUpdate}] Temperature: ${lastTemperature}°C`);
            }
        } catch (error) {
            console.error(`[${new Date().toLocaleString()}] Failed to parse message:`, error);
            tempGauge.remove();  // Remove metric instead of NaN
        }
    });

    // Disconnect handler
    ws.on('close', () => {
        connectedClients.delete(ws);
        connectedDevicesGauge.set(connectedClients.size);
        if (connectedClients.size === 0) {
            tempGauge.remove();  // Remove metric instead of NaN
        }
        console.log(`[${new Date().toLocaleString()}] Client disconnected`);
        console.log(`Connected clients: ${connectedClients.size}`);
    });

    // Error handler
    ws.on('error', (error) => {
        console.error(`[${new Date().toLocaleString()}] WebSocket error:`, error);
        tempGauge.remove();  // Remove metric instead of NaN
        connectedDevicesGauge.set(connectedClients.size);
    });
});

// Prometheus metrics endpoint
app.get('/metrics', async (_, res) => {
    res.set('Content-Type', promClient.register.contentType);
    res.send(await promClient.register.metrics());
});

// WebSocket endpoint
app.get('/esp32_temp', (req, res) => {
    wss.handleUpgrade(req, req.socket, Buffer.alloc(0), (ws) => {
        wss.emit('connection', ws, req);
    });
});

// Server error handler
wss.on('error', (error) => {
    console.error(`[${new Date().toISOString()}] Server error:`, error);
});

// Start server
app.listen(3100, () => {
    console.log('Server running on http://localhost:3100');
});
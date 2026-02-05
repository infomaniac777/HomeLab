/*
Copyright 2022 Richard Kosegi

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package exporter

import (
	"log/slog"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/rkosegi/tuya-smartplug-exporter/pkg/proto"
)

type exporter struct {
	m       GlobalMetrics
	devs    *[]Device
	l       *slog.Logger
	clients map[string]proto.Proto // Changed from proto.Client to proto.Proto
	mu      sync.Mutex
}

func (e *exporter) Describe(ch chan<- *prometheus.Desc) {
	e.m.Error.Describe(ch)
	e.m.TotalScrapes.Describe(ch)
}

func (e *exporter) Collect(ch chan<- prometheus.Metric) {
	e.m.Error.Set(0)
	startAny := time.Now()
	var wg sync.WaitGroup
	defer func() {
		wg.Wait()
		e.m.TotalScrapes.Observe(time.Since(startAny).Seconds())
		e.m.Error.Collect(ch)
		e.m.TotalScrapes.Collect(ch)
	}()
	for _, dev := range *e.devs {
		wg.Add(1)
		device := dev
		go func() {
			defer wg.Done()
			m := newDeviceMetrics()
			start := time.Now()
			labels := prometheus.Labels{"device": device.Name}
			timeout := device.GetTimeout()
			e.l.Debug("Processing device", "device", device.Name, "address", device.Ip, "timeout", timeout)

			e.mu.Lock()
			client, ok := e.clients[device.Id]
			if !ok {
				e.l.Debug("No existing client found, creating new one.", "device", device.Name, "id", device.Id) // Changed address to id
				client = proto.NewClient(device.Ip, device.Id, []byte(device.Key), timeout)
				e.clients[device.Id] = client 
			} else {
				e.l.Debug("Using existing client.", "device", device.Name, "id", device.Id) // Changed address to id
			}
			e.mu.Unlock()

			status, err := client.Status()
			e.l.Debug("Status of device", "device", device.Name, "status", status)
			if err != nil {
				e.l.Warn("error during scrape", "device", device.Name, "error", err)
				m.ScrapeErrors.With(labels).Inc()
				e.m.Error.Set(1)
				e.mu.Lock()
				if cl, ok := e.clients[device.Id]; ok {
					cl.Close() 
					delete(e.clients, device.Id)
					e.l.Debug("Removed and closed client due to error.", "device", device.Name, "id", device.Id)
				} else {
					e.l.Debug("Client not found in cache for removal, might have been removed by another goroutine.", "device", device.Name, "id", device.Id)
				}
				e.mu.Unlock()
			} else {
				ison := 0
				m.Current.With(labels).Set(float64(status.Dps.Current) / 1000)
				m.Voltage.With(labels).Set(float64(status.Dps.Voltage) / 10)
				m.Power.With(labels).Set(float64(status.Dps.Power) / 10)
				if status.Dps.SwitchOn {
					ison = 1
				}
				m.SwitchOn.With(labels).Set(float64(ison))
			}
			m.ScrapeDuration.With(labels).Observe(time.Since(start).Seconds())

			m.SwitchOn.Collect(ch)
			m.Current.Collect(ch)
			m.Voltage.Collect(ch)
			m.Power.Collect(ch)
			m.ScrapeDuration.Collect(ch)
		}()
	}
}

// CloseClients iterates over all active clients and closes their connections.
func (e *exporter) CloseClients() {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.l.Info("Closing all client connections...")
	for id, client := range e.clients {
		if err := client.Close(); err != nil {
			e.l.Warn("Error closing client connection", "id", id, "error", err)
		} else {
			e.l.Debug("Closed client connection", "id", id)
		}
	}
	e.l.Info("All client connections closed.")
}

func New(devices *[]Device, logger *slog.Logger) prometheus.Collector {
	return &exporter{
		m:       newCommonMetrics(),
		devs:    devices,
		l:       logger,
		clients: make(map[string]proto.Proto),
	}
}

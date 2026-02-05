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

package proto

import (
	"crypto/aes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"hash/crc32"
	"net"
	"sync"
	"time"
)

var (
	prefix = []byte{0x00, 0x00, 0x55, 0xaa, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
	infix  = []byte{0x0a, 0x00, 0x00, 0x00}
	suffix = []byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xaa, 0x55}
)

type Dps struct {
	SwitchOn bool `json:"1"`
	Current  int  `json:"18"`
	Power    int  `json:"19"`
	Voltage  int  `json:"20"`
}

type Response struct {
	Dps Dps `json:"dps"`
}

type Req struct {
	GwId  string `json:"gwId,omitempty"`
	DevId string `json:"devId,omitempty"`
}

type Proto interface {
	Status() (*Response, error)
	Close() error
}

type proto struct {
	key     []byte
	ip      string
	id      string
	timeout time.Duration
	conn    net.Conn
	mu      sync.Mutex
}

func (p *proto) Status() (resp *Response, err error) {
	defer func() {
		if x := recover(); x != nil {
			err = fmt.Errorf("protocol error: %s, check device key", x)
		}
	}()

	var r Response
	data, err := p.exchange()
	if err != nil {
		return nil, err
	}
	data, err = p.decryptResponse(data[20 : len(data)-8])
	if err != nil {
		return nil, err
	}
	err = json.Unmarshal(unpad(data), &r)
	if err != nil {
		return nil, err
	}
	resp = &r
	return resp, nil
}

func NewClient(ip string, id string, key []byte, timeout time.Duration) Proto {
	return &proto{
		key:     key,
		ip:      ip,
		id:      id,
		timeout: timeout,
		conn:    nil,
	}
}

// Close closes the persistent connection.
func (p *proto) Close() error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.conn != nil {
		err := p.conn.Close()
		p.conn = nil
		return err
	}
	return nil
}

func (p *proto) decryptResponse(data []byte) ([]byte, error) {
	cipher, err := aes.NewCipher(p.key)
	if err != nil {
		return nil, err
	}
	out := make([]byte, len(data))
	for i, j := 0, 16; i < len(data); i, j = i+16, j+16 {
		cipher.Decrypt(out[i:j], data[i:j])
	}
	return out, nil
}

func pad(text []byte) []byte {
	pad := 16 - (len(text) % 16)
	if pad == 0 {
		pad = 16
	}
	for i := 0; i < pad; i++ {
		text = append(text, byte(pad))
	}
	return text
}

func unpad(text []byte) []byte {
	padding := text[len(text)-1]
	return text[:len(text)-int(padding)]
}

func (p *proto) encryptRequest() ([]byte, error) {
	r := &Req{
		GwId:  p.id,
		DevId: p.id,
	}
	data, err := json.Marshal(r)
	if err != nil {
		return nil, err
	}
	data = pad(data)
	block, err := aes.NewCipher(p.key)
	if err != nil {
		return nil, err
	}
	encrypted := make([]byte, len(data))
	for i, j := 0, 16; i < len(data); i, j = i+16, j+16 {
		block.Encrypt(encrypted[i:j], data[i:j])
	}
	encrypted = append(encrypted, suffix...)
	result := make([]byte, 0)
	result = append(result, prefix...)
	result = append(result, infix...)
	result = append(result, byte(len(encrypted)))
	result = append(result, encrypted...)
	crc := crc32.ChecksumIEEE(result[:len(result)-8])
	result2 := result[:len(result)-8]
	crcbytes := make([]byte, 4)
	binary.BigEndian.PutUint32(crcbytes, crc)
	result2 = append(result2, crcbytes...)
	result2 = append(result2, result[len(result)-4:]...)
	return result2, nil
}

func (p *proto) closeConnOnError() {
	if p.conn != nil {
		p.conn.Close()
		p.conn = nil
	}
}

func (p *proto) exchange() ([]byte, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	reqData, err := p.encryptRequest()
	if err != nil {
		return nil, err
	}

	if p.conn == nil {
		conn, dialErr := net.DialTimeout("tcp", net.JoinHostPort(p.ip, "6668"), p.timeout)
		if dialErr != nil {
			return nil, fmt.Errorf("failed to connect to %s: %w", p.ip, dialErr)
		}
		p.conn = conn
	}

	deadline := time.Now().Add(p.timeout)

	if err := p.conn.SetWriteDeadline(deadline); err != nil {
		p.closeConnOnError()
		return nil, fmt.Errorf("failed to set write deadline: %w", err)
	}

	_, err = p.conn.Write(reqData) 
	if err != nil {
		p.closeConnOnError()
		return nil, fmt.Errorf("failed to write data: %w", err)
	}

	if err := p.conn.SetReadDeadline(deadline); err != nil {
		p.closeConnOnError()
		return nil, fmt.Errorf("failed to set read deadline: %w", err)
	}

	inbuffer := make([]byte, 256)
	bytesRead, err := p.conn.Read(inbuffer)
	if err != nil {
		p.closeConnOnError()
		return nil, fmt.Errorf("failed to read data: %w", err)
	}

	if bytesRead == 0 {
		p.closeConnOnError()
		return nil, fmt.Errorf("no data read from device %s (IP: %s), connection might have been closed by peer", p.id, p.ip)
	}

	return inbuffer[:bytesRead], nil
}

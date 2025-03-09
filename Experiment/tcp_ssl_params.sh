#!/bin/bash
# tcp_ssl_params.sh - Check current TCP/network parameters for SSL optimization

# Format output with colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}TCP/Network Parameters for SSL Performance${NC}\n"

# Function to check and display parameter value
check_param() {
  local param=$1
  local expected=$2
  local current=$(sysctl -n $param 2>/dev/null)
  
  if [ -z "$current" ]; then
    echo -e "${param}: ${RED}Parameter not found${NC}"
    return
  fi
  
  echo -n "$param = $current"
  
  if [ ! -z "$expected" ]; then
    if [ "$current" == "$expected" ]; then
      echo -e " ${GREEN}[OK]${NC}"
    else
      echo -e " ${YELLOW}[Expected: $expected]${NC}"
    fi
  else
    echo ""
  fi
}

# Buffer sizes
echo -e "\n${BOLD}TCP Buffer Size Parameters:${NC}"
check_param "net.core.rmem_max" "16777216"
check_param "net.core.wmem_max" "16777216"
check_param "net.ipv4.tcp_rmem" "4096 87380 16777216"
check_param "net.ipv4.tcp_wmem" "4096 65536 16777216"

# Congestion control
echo -e "\n${BOLD}TCP Congestion Control:${NC}"
check_param "net.core.default_qdisc" "fq"
check_param "net.ipv4.tcp_congestion_control" "bbr"

# TCP optimizations
echo -e "\n${BOLD}TCP Protocol Optimizations:${NC}"
check_param "net.ipv4.tcp_sack" "1"
check_param "net.ipv4.tcp_window_scaling" "1"
check_param "net.ipv4.tcp_timestamps" "1"
check_param "net.ipv4.tcp_fastopen" "3"

# SSL-relevant additional parameters
echo -e "\n${BOLD}Additional SSL-Relevant Parameters:${NC}"
check_param "net.ipv4.tcp_slow_start_after_idle" "0"
check_param "net.ipv4.tcp_no_metrics_save" "1"
check_param "net.ipv4.tcp_mtu_probing" "1"

# Check OpenSSL version for SSL performance context
echo -e "\n${BOLD}OpenSSL Version:${NC}"
openssl version

# Check current SSL-related file descriptors limit
echo -e "\n${BOLD}File Descriptor Limits (affects max SSL connections):${NC}"
echo "Current file descriptor limit (ulimit -n): $(ulimit -n)"
echo "System-wide file descriptor limit: $(sysctl -n fs.file-max)"

# Additional info for SSL performance in aria2
echo -e "\n${BOLD}Memory Parameters (affect SSL buffer performance):${NC}"
check_param "vm.swappiness" "10"
check_param "vm.dirty_ratio" "30"
check_param "vm.dirty_background_ratio" "5"

# SSL-specific suggestions for aria2
echo -e "\n${BOLD}Recommendations for aria2 SSL Performance:${NC}"
echo -e "✓ Run aria2 with: ${YELLOW}--max-connection-per-server=16${NC} to leverage increased TCP buffers"
echo -e "✓ Consider: ${YELLOW}--disk-cache=64M${NC} to reduce disk I/O during SSL operations"
echo -e "✓ For HTTPS downloads: ${YELLOW}--min-split-size=8M${NC} balances SSL overhead with parallelism"

# Explain how to apply changes if needed
echo -e "\n${BOLD}To Apply Parameters Temporarily:${NC}"
echo "sudo sysctl -w parameter.name=value"

echo -e "\n${BOLD}To Apply Parameters Permanently:${NC}"
echo "Add parameters to /etc/sysctl.conf or /etc/sysctl.d/99-network-tuning.conf"
echo "Then run: sudo sysctl -p"

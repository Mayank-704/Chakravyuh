"""
Test Payload Generator: Creates malicious network traffic patterns for testing.
Used to verify detector accuracy on known attack patterns.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from enum import Enum
import random
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AttackType(Enum):
    """Common network attack patterns."""
    PORT_SCAN = "port_scan"
    DOS_FLOOD = "dos_flood"
    SLOW_EXFILTRATION = "slow_exfiltration"
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"
    STEALTH_SCANNING = "stealth_scanning"
    ANOMALOUS_PROTOCOL = "anomalous_protocol"
    COMMAND_INJECTION = "command_injection"


class TestPayloadGenerator:
    """
    Generates synthetic attack traffic patterns for testing the detector.
    Each attack type has distinct statistical signatures.
    """
    
    def __init__(self, seed: int = 42):
        """Initialize payload generator."""
        random.seed(seed)
        np.random.seed(seed)
    
    def _random_ip(self) -> str:
        """Generate random IP address."""
        return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    
    def _random_port(self, privileged: bool = False) -> int:
        """Generate random port."""
        if privileged:
            return random.randint(1, 1023)
        return random.randint(1024, 65535)
    
    def generate_port_scan(self, n_flows: int = 50) -> Tuple[pd.DataFrame, str]:
        """
        Port scan attack: rapid connections to many ports on target.
        Signature: many flows, common dest IP, varied dest_port, short duration
        """
        flows = []
        src_ip = self._random_ip()
        dst_ip = self._random_ip()
        
        for i in range(n_flows):
            flows.append({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': self._random_port(),
                'dst_port': random.randint(1, 1000),  # Scanning common ports
                'protocol': 'TCP',
                'packet_count': random.randint(2, 5),
                'total_bytes': random.randint(40, 200),
                'duration': random.uniform(0.01, 0.1),
                'inter_arrival_time': np.random.exponential(0.001),
                'payload_size_variance': random.uniform(0, 100),
                'flag_pattern': 'TCP',
                'window_size': 1024
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated PORT_SCAN attack: {len(df)} flows from {src_ip} to {dst_ip}")
        return df, AttackType.PORT_SCAN.value
    
    def generate_dos_flood(self, n_flows: int = 200) -> Tuple[pd.DataFrame, str]:
        """
        DoS/DDoS flood: massive volume of packets.
        Signature: huge packet counts, large bytes, very short inter-arrival times
        """
        flows = []
        src_ips = [self._random_ip() for _ in range(random.randint(1, 10))]
        dst_ip = self._random_ip()
        
        for i in range(n_flows):
            flows.append({
                'src_ip': random.choice(src_ips),
                'dst_ip': dst_ip,
                'src_port': self._random_port(),
                'dst_port': random.choice([80, 443, 53, 123]),
                'protocol': random.choice(['TCP', 'UDP']),
                'packet_count': random.randint(5000, 50000),  # HUGE
                'total_bytes': random.randint(1000000, 50000000),  # HUGE
                'duration': random.uniform(0.1, 5),
                'inter_arrival_time': np.random.exponential(0.0001),  # Very fast
                'payload_size_variance': random.uniform(0, 1000),
                'flag_pattern': 'TCP',
                'window_size': 65535
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated DOS_FLOOD attack: {len(df)} flows to {dst_ip}")
        return df, AttackType.DOS_FLOOD.value
    
    def generate_slow_exfiltration(self, n_flows: int = 100) -> Tuple[pd.DataFrame, str]:
        """
        Slow data exfiltration: stealthy, low-rate, long duration.
        Signature: long duration, moderate bytes, consistent inter-arrival
        """
        flows = []
        src_ip = self._random_ip()
        dst_ip = self._random_ip()
        
        for i in range(n_flows):
            flows.append({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': self._random_port(),
                'dst_port': random.choice([443, 80, 22, 3389]),
                'protocol': 'TCP',
                'packet_count': random.randint(100, 1000),
                'total_bytes': random.randint(100000, 5000000),  # Medium-large
                'duration': random.uniform(600, 3600),  # Very long (10-60 min)
                'inter_arrival_time': np.random.exponential(5),  # Slow, regular
                'payload_size_variance': random.uniform(1000, 10000),
                'flag_pattern': 'TCP',
                'window_size': 65535
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated SLOW_EXFILTRATION attack: {len(df)} flows ({src_ip} -> {dst_ip})")
        return df, AttackType.SLOW_EXFILTRATION.value
    
    def generate_brute_force(self, n_flows: int = 150) -> Tuple[pd.DataFrame, str]:
        """
        Brute force SSH/RDP: many connection attempts.
        Signature: many flows to same port (22/3389), rapid pace, same src/dst pair
        """
        flows = []
        src_ip = self._random_ip()
        dst_ip = self._random_ip()
        target_port = random.choice([22, 3389, 21])  # SSH, RDP, or FTP
        
        for i in range(n_flows):
            flows.append({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': self._random_port(),
                'dst_port': target_port,
                'protocol': 'TCP',
                'packet_count': random.randint(5, 20),
                'total_bytes': random.randint(500, 5000),
                'duration': random.uniform(0.5, 5),
                'inter_arrival_time': np.random.exponential(0.1),
                'payload_size_variance': random.uniform(100, 1000),
                'flag_pattern': 'TCP',
                'window_size': 2048
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated BRUTE_FORCE attack: {len(df)} attempts on {dst_ip}:{target_port}")
        return df, AttackType.BRUTE_FORCE.value
    
    def generate_command_injection(self, n_flows: int = 80) -> Tuple[pd.DataFrame, str]:
        """
        Command injection / web attack: malformed requests with payloads.
        Signature: multiple flows, varied payload sizes, unusual protocols/ports
        """
        flows = []
        src_ip = self._random_ip()
        web_servers = [self._random_ip() for _ in range(random.randint(1, 3))]
        
        for i in range(n_flows):
            flows.append({
                'src_ip': src_ip,
                'dst_ip': random.choice(web_servers),
                'src_port': self._random_port(),
                'dst_port': random.choice([80, 443, 8080, 8443]),
                'protocol': 'TCP',
                'packet_count': random.randint(10, 100),
                'total_bytes': random.randint(10000, 100000),
                'duration': random.uniform(1, 30),
                'inter_arrival_time': np.random.exponential(0.5),
                'payload_size_variance': random.uniform(5000, 50000),  # Variable payloads
                'flag_pattern': 'TCP',
                'window_size': 32768
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated COMMAND_INJECTION attack: {len(df)} malicious HTTP flows")
        return df, AttackType.COMMAND_INJECTION.value
    
    def generate_stealth_scanning(self, n_flows: int = 30) -> Tuple[pd.DataFrame, str]:
        """
        Stealth scanning with fragmentation/spoofing hints.
        Signature: unusual packet patterns, low packet counts, varied protocols
        """
        flows = []
        src_ip = self._random_ip()
        dst_subnet = '.'.join(self._random_ip().split('.')[:3])
        
        for i in range(n_flows):
            flows.append({
                'src_ip': src_ip,
                'dst_ip': f"{dst_subnet}.{random.randint(1,254)}",
                'src_port': self._random_port(),
                'dst_port': random.choice([22, 80, 443, 3306, 5432, 8080]),
                'protocol': random.choice(['TCP', 'UDP', 'ICMP']),
                'packet_count': 1,  # Single packet = stealthy
                'total_bytes': random.randint(20, 60),
                'duration': 0.001,
                'inter_arrival_time': np.random.exponential(0.01),
                'payload_size_variance': 0,
                'flag_pattern': 'SYN',  # SYN scan
                'window_size': 512
            })
        
        df = pd.DataFrame(flows)
        logger.info(f"Generated STEALTH_SCANNING attack: {len(df)} stealthy probes")
        return df, AttackType.STEALTH_SCANNING.value
    
    def generate_random_attack(self) -> Tuple[pd.DataFrame, str]:
        """Generate a random attack type."""
        attack_type = random.choice(list(AttackType))
        
        if attack_type == AttackType.PORT_SCAN:
            return self.generate_port_scan()
        elif attack_type == AttackType.DOS_FLOOD:
            return self.generate_dos_flood()
        elif attack_type == AttackType.SLOW_EXFILTRATION:
            return self.generate_slow_exfiltration()
        elif attack_type == AttackType.BRUTE_FORCE:
            return self.generate_brute_force()
        elif attack_type == AttackType.COMMAND_INJECTION:
            return self.generate_command_injection()
        elif attack_type == AttackType.STEALTH_SCANNING:
            return self.generate_stealth_scanning()
        else:
            return self.generate_port_scan()
    
    def generate_malicious_script(self, attack_type: str = "port_scan", filename: str = "payload.sh") -> str:
        """
        Generate sample malicious script for demonstration.
        NOTE: These are harmless demonstrations - they won't actually execute attacks.
        """
        scripts = {
            "port_scan": """#!/bin/bash
# Network reconnaissance script
TARGET=$1
for port in {1..1000}; do
  timeout 0.1 bash -c "echo >/dev/tcp/$TARGET/$port" 2>/dev/null && echo "Port $port open"
done""",
            
            "dos_flood": """#!/bin/bash
# Simulated flood script (non-functional for demo)
# This would require elevated privileges and isn't actually executed
TARGET=$1
PORT=$2
echo "Simulating flood to $TARGET:$PORT..."
for i in {1..10000}; do
  echo "Packet $i" > /dev/null
done""",
            
            "brute_force": """#!/bin/bash
# SSH brute force attempt (demo - won't actually run)
TARGET=$1
WORDLIST="password123\nadmin\nroot\ntest"
echo "$WORDLIST" | while read pass; do
  echo "Trying: $pass"
done""",
            
            "exfiltration": """#!/bin/bash
# Data collection script (demo - simulates exfiltration)
OUTFILE="data.txt"
echo "Collecting system info..." > $OUTFILE
uname -a >> $OUTFILE
whoami >> $OUTFILE
echo "Data ready for transmission"
""",
            
            "web_attack": """#!/bin/bash
# Web attack payload (demo - SQL injection simulation)
TARGET=$1
PAYLOAD="' OR '1'='1"
curl -X POST "$TARGET/login.php" -d "user=$PAYLOAD&pass=$PAYLOAD"
echo "Attack payload sent"
"""
        }
        
        script_content = scripts.get(attack_type, scripts["port_scan"])
        
        filepath = f"./payloads/{filename}"
        Path(filepath).parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(script_content)
        
        logger.info(f"Generated malicious script: {filepath} ({attack_type})")
        return filepath
    
    def get_attack_info(self, attack_type: str) -> Dict:
        """Get information about an attack type."""
        info = {
            "port_scan": {
                'name': 'Port Scanning',
                'severity': 'MEDIUM',
                'description': 'Rapid probe to many ports to find open services',
                'indicators': ['Many flows same src/dst', 'Sequential ports', 'Short duration each'],
                'common_tools': ['nmap', 'masscan', 'zmap']
            },
            "dos_flood": {
                'name': 'DoS/DDoS Flood',
                'severity': 'CRITICAL',
                'description': 'Massive volume attack to overwhelm target',
                'indicators': ['Huge packet counts', 'Large byte volumes', 'Fast inter-arrival times'],
                'common_tools': ['hping3', 'UDP Flooder', 'Syn Flooder']
            },
            "brute_force": {
                'name': 'Brute Force Attack',
                'severity': 'HIGH',
                'description': 'Many auth attempts to compromise credentials',
                'indicators': ['Many flows same dst_port', 'Rapid pace', 'Variable payloads'],
                'common_tools': ['hydra', 'medusa', 'OpenSSH'],
            },
            "slow_exfiltration": {
                'name': 'Data Exfiltration',
                'severity': 'CRITICAL',
                'description': 'Stealthy extraction of sensitive data',
                'indicators': ['Long duration flows', 'Regular pattern', 'Medium-large bytes'],
                'common_tools': ['scp', 'DNS tunneling', 'HTTPS proxies']
            },
            "command_injection": {
                'name': 'Command Injection',
                'severity': 'CRITICAL',
                'description': 'Injected commands in web requests',
                'indicators': ['Malformed payloads', 'Variable sizes', 'Web server ports'],
                'common_tools': ['sqlmap', 'Burp Suite']
            },
            "stealth_scanning": {
                'name': 'Stealth Scanning',
                'severity': 'MEDIUM',
                'description': 'Fragmented/spoofed probes to avoid detection',
                'indicators': ['Single packet flows', 'Various protocols', 'Subnet sweep'],
                'common_tools': ['Nmap -sF', 'scapy']
            }
        }
        
        return info.get(attack_type, {})


if __name__ == "__main__":
    from pathlib import Path
    
    logger.info("Testing TestPayloadGenerator...")
    
    gen = TestPayloadGenerator()
    
    # Generate all attack types
    attacks = [
        AttackType.PORT_SCAN,
        AttackType.DOS_FLOOD,
        AttackType.BRUTE_FORCE,
        AttackType.SLOW_EXFILTRATION,
        AttackType.COMMAND_INJECTION,
        AttackType.STEALTH_SCANNING
    ]
    
    for attack in attacks:
        if attack == AttackType.PORT_SCAN:
            df, name = gen.generate_port_scan()
        elif attack == AttackType.DOS_FLOOD:
            df, name = gen.generate_dos_flood()
        elif attack == AttackType.BRUTE_FORCE:
            df, name = gen.generate_brute_force()
        elif attack == AttackType.SLOW_EXFILTRATION:
            df, name = gen.generate_slow_exfiltration()
        elif attack == AttackType.COMMAND_INJECTION:
            df, name = gen.generate_command_injection()
        elif attack == AttackType.STEALTH_SCANNING:
            df, name = gen.generate_stealth_scanning()
        
        info = gen.get_attack_info(name)
        print(f"\n{info['name']} (Severity: {info['severity']})")
        print(f"  Generated: {len(df)} flows")
        print(f"  Description: {info['description']}")
    
    logger.info("\n✓ TestPayloadGenerator test passed!")

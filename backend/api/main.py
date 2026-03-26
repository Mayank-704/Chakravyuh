from fastapi import FastAPI, WebSocket
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

app = FastAPI()

# Placeholder data
stats_data = {
    "total_threats": 100,
    "critical_count": 10,
    "honeypot_trapped_count": 5,
    "federated_node_count": 3
}

alerts_data = [
    {"id": 1, "severity": "critical", "description": "DDoS attack detected"},
    {"id": 2, "severity": "high", "description": "SQL injection attempt"},
    {"id": 3, "severity": "medium", "description": "Port scanning"},
]

honeypots_data = [
    {"id": "h-01", "name": "honey-ssh", "status": "active"},
    {"id": "h-02", "name": "honey-ftp", "status": "active"},
]

threat_map_data = {
    "nodes": [
        {"id": "node-1", "location": [28.6139, 77.2090]}, # Delhi
        {"id": "node-2", "location": [19.0760, 72.8777]}, # Mumbai
    ],
    "attacks": [
        {"source": "node-1", "target": "node-2"}
    ]
}

federated_status_data = [
    {"id": "node-1", "status": "online", "sample_count": 1000},
    {"id": "node-2", "status": "online", "sample_count": 1500},
    {"id": "node-3", "status": "offline", "sample_count": 0},
]

# Emergency Response Data
actions_history: List[Dict[str, Any]] = []
blocked_ips: List[Dict[str, Any]] = [
    {"ip": "203.168.1.1", "threat_count": 45, "first_seen": "2026-03-24T08:30:00", "last_blocked": "2026-03-24T10:15:00", "country": "China"},
    {"ip": "185.220.101.45", "threat_count": 12, "first_seen": "2026-03-24T06:20:00", "last_blocked": "2026-03-24T09:45:00", "country": "Russia"},
]

# Request Models
class IsolateNodeRequest(BaseModel):
    node_id: str

class BlockIPRequest(BaseModel):
    attacker_ip: str

class LockdownRequest(BaseModel):
    node_id: str

class QuarantineRequest(BaseModel):
    node_id: str

class RotateCredsRequest(BaseModel):
    node_id: str

class EscalateRequest(BaseModel):
    severity: str

# ============ EXISTING ENDPOINTS ============

@app.get("/api/stats")
async def get_stats() -> Dict[str, int]:
    """
    Returns total threats, critical count, honeypot-trapped count, and federated node count.
    """
    return stats_data

@app.get("/api/alerts")
async def get_alerts(severity: str = None) -> List[Dict[str, Any]]:
    """
    Returns a list of detected threats, with optional filtering by severity.
    """
    if severity:
        return [alert for alert in alerts_data if alert["severity"] == severity]
    return alerts_data

@app.get("/api/honeypots")
async def get_honeypots() -> List[Dict[str, str]]:
    """
    Returns a list of active honeypot trap containers.
    """
    return honeypots_data

@app.get("/api/threat-map")
async def get_threat_map() -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns node locations and attack vectors for map visualization.
    """
    return threat_map_data

@app.get("/api/federated/status")
async def get_federated_status() -> List[Dict[str, Any]]:
    """
    Returns all federated nodes, their sync status, and sample counts.
    """
    return federated_status_data

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint to stream new alerts to the dashboard in real time.
    """
    await websocket.accept()
    try:
        while True:
            import asyncio
            await asyncio.sleep(10)
            new_alert = {"id": len(alerts_data) + 1, "severity": "high", "description": "New threat detected"}
            alerts_data.append(new_alert)
            await websocket.send_json(new_alert)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# ============ EMERGENCY RESPONSE ENDPOINTS ============

@app.post("/api/emergency/isolate-node")
async def isolate_node(request: IsolateNodeRequest) -> Dict[str, str]:
    """
    Isolate a specific node from network traffic.
    Blocks all incoming and outgoing connections except for emergency comms.
    """
    action = {
        "id": f"isolate-{datetime.now().timestamp()}",
        "type": "isolate",
        "node_id": request.node_id,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    return {
        "action_id": action["id"],
        "action_type": "isolate",
        "node_id": request.node_id,
        "status_message": f"✅ Node {request.node_id} successfully isolated from network. All external connections blocked.",
        "executed_at": action["timestamp"],
    }


@app.post("/api/emergency/block-ip")
async def block_ip(request: BlockIPRequest) -> Dict[str, str]:
    """
    Block an attacker IP globally via firewall rules.
    """
    # Check if already blocked
    already_blocked = any(ip["ip"] == request.attacker_ip for ip in blocked_ips)
    
    if not already_blocked:
        blocked_ips.append({
            "ip": request.attacker_ip,
            "threat_count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_blocked": datetime.now().isoformat(),
            "country": "Unknown",
        })
    
    action = {
        "id": f"block-{datetime.now().timestamp()}",
        "type": "block-ip",
        "attacker_ip": request.attacker_ip,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    
    return {
        "action_id": action["id"],
        "action_type": "block-ip",
        "node_id": request.attacker_ip,
        "affected_ips": [request.attacker_ip],
        "status_message": f"✅ IP {request.attacker_ip} added to global blocklist. Firewall rules updated.",
        "executed_at": action["timestamp"],
    }


@app.post("/api/emergency/lockdown")
async def activate_lockdown(request: LockdownRequest) -> Dict[str, str]:
    """
    Full emergency lockdown: disable all outbound connections, enable monitoring.
    """
    action = {
        "id": f"lockdown-{datetime.now().timestamp()}",
        "type": "lockdown",
        "node_id": request.node_id,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    
    return {
        "action_id": action["id"],
        "action_type": "lockdown",
        "node_id": request.node_id,
        "status_message": f"🔒 FULL LOCKDOWN ACTIVATED for {request.node_id}. All outbound traffic blocked. Enhanced monitoring enabled.",
        "executed_at": action["timestamp"],
    }


@app.post("/api/emergency/quarantine")
async def quarantine_node(request: QuarantineRequest) -> Dict[str, str]:
    """
    Quarantine a node: move to isolated VLAN, disable all user access.
    """
    action = {
        "id": f"quarantine-{datetime.now().timestamp()}",
        "type": "quarantine",
        "node_id": request.node_id,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    
    return {
        "action_id": action["id"],
        "action_type": "quarantine",
        "node_id": request.node_id,
        "status_message": f"⛔ {request.node_id} moved to isolated VLAN. User access revoked. Forensic analysis initiated.",
        "executed_at": action["timestamp"],
    }


@app.post("/api/emergency/rotate-credentials")
async def rotate_credentials(request: RotateCredsRequest) -> Dict[str, str]:
    """
    Immediately rotate all credentials (API keys, passwords) for a node.
    """
    action = {
        "id": f"rotate-{datetime.now().timestamp()}",
        "type": "rotate",
        "node_id": request.node_id,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    
    return {
        "action_id": action["id"],
        "action_type": "rotate-credentials",
        "node_id": request.node_id,
        "status_message": f"🔄 All credentials for {request.node_id} rotated successfully. New keys issued to authorized personnel.",
        "executed_at": action["timestamp"],
    }


@app.post("/api/emergency/escalate")
async def auto_escalate(request: EscalateRequest) -> Dict[str, str]:
    """
    Auto-escalate threat: mark as critical and notify government officials.
    """
    action = {
        "id": f"escalate-{datetime.now().timestamp()}",
        "type": "escalate",
        "severity": request.severity,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
    }
    actions_history.append(action)
    stats_data["critical_count"] = (stats_data.get("critical_count", 0) or 0) + 1
    
    return {
        "action_id": action["id"],
        "action_type": "escalate",
        "node_id": "SYSTEM",
        "status_message": f"⚡ CRITICAL threat escalated. Emergency notifications sent to CERT-In and NCIIPC. Government officials alerted.",
        "executed_at": action["timestamp"],
    }


@app.get("/api/emergency/actions-history")
async def get_actions_history() -> List[Dict[str, Any]]:
    """
    Retrieve full history of emergency actions taken.
    """
    return actions_history[-20:] if actions_history else []


@app.get("/api/emergency/blocked-ips")
async def get_blocked_ips() -> List[Dict[str, Any]]:
    """
    Retrieve list of currently blocked attacker IPs.
    """
    return blocked_ips


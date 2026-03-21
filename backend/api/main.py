from fastapi import FastAPI, WebSocket
from typing import List, Dict, Any

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
            # In a real application, you would have a mechanism to push new alerts here.
            # For this example, we'll just send a dummy alert every 10 seconds.
            import asyncio
            await asyncio.sleep(10)
            new_alert = {"id": len(alerts_data) + 1, "severity": "high", "description": "New threat detected"}
            alerts_data.append(new_alert)
            await websocket.send_json(new_alert)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

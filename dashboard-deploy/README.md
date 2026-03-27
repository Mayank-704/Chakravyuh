# Project Chakravyuh

Chakravyuh is a cybersecurity defense project that combines deception, real-time monitoring, and federated intelligence ideas into one demo platform.

In simple terms, this project does three things:
1. Detects and tracks suspicious attacker behavior.
2. Shows live threat activity in a SOC-style dashboard.
3. Simulates realistic attacks for demos and testing.

## Project Aim

The goal is to build an automated cyber defense system for critical sectors (healthcare, banking, government) that is:
1. Proactive (trap and observe attackers, not just block them).
2. Explainable (human-friendly dashboard and alert stream).
3. Privacy-aware (designed around decentralized/federated patterns).

## What Is In This Repository

Main parts:
1. `backend/`:
  FastAPI backend, threat data APIs, WebSocket streaming, attack simulator, and related modules.
2. `dashboard-deploy/`:
  React + Vite frontend SOC dashboard (the main UI you see in browser).
3. `dashboard-deploy-ready/`:
  Clean copy of frontend files for manual repo push/deployment.
4. `docker-compose.yml`:
  Container orchestration template for local multi-service runs.

## Architecture Overview

High-level flow:
1. Simulated or real trap telemetry is produced.
2. Backend processes telemetry into normalized alerts.
3. Backend stores in-memory state for stats, alerts, honeypots, and map data.
4. Backend exposes REST APIs for full snapshots.
5. Backend pushes live events over WebSocket.
6. Frontend renders dashboard cards, map, feed, charts, and ticker in real time.

## Backend Overview

Backend stack:
1. Python + FastAPI.
2. Optional Kafka (if available).
3. WebSocket broadcast for live alert updates.

Important backend capabilities:
1. REST endpoints for dashboard data.
2. Real-time WebSocket endpoint for live alert events.
3. Attack simulation endpoint support.
4. Graceful fallback if Kafka is missing.

Key API endpoints used by frontend:
1. `GET /api/stats`
2. `GET /api/alerts`
3. `GET /api/honeypots`
4. `GET /api/threat-map`
5. `GET /api/federated/status`
6. `WS /ws/alerts`

## Frontend Overview (How It Works)

Frontend stack:
1. React + TypeScript.
2. Vite build/dev tooling.
3. Tailwind CSS + custom CSS theming.
4. Recharts for analytics charts.
5. React Leaflet for India-focused map rendering.

Main dashboard sections:
1. Header with branding and live telemetry indicator.
2. Stats cards (total alerts, critical incidents, honeypots, nodes).
3. Auto-SOC alert feed panel.
4. India defense grid map with node status and links.
5. Honeypot terminal-style log panel.
6. Analytics row:
  24-hour timeline, attack type distribution, top targeted institutions.
7. Bottom ticker for high-severity alerts.

Real-time behavior:
1. Initial load fetches all datasets via REST APIs.
2. Frontend opens WebSocket connection to receive alert events.
3. On new events, alert list updates and data re-sync happens.
4. Auto-reconnect and polling fallback keep dashboard alive during network hiccups.

## Theme System (Current + Light + Clean)

The frontend includes a theme system with a mini settings button:
1. `Current` theme: original dark SOC look.
2. `Light` theme: bright neutral variant.
3. `Clean Theme`: poster-inspired neo-brutal clean design.

Theme implementation summary:
1. Theme value stored in local storage (`chakravyuh-theme`).
2. Root `data-theme` attribute switches CSS variable sets.
3. Shared component styles react to theme variables.
4. Theme menu is compact and non-overlapping.

## Attack Simulation (Demo Mode)

`backend/simulate_attack.py` sends a realistic attacker session.

Simulation flow:
1. Try Kafka producer mode first.
2. If Kafka is unavailable, fallback to HTTP simulation endpoint.
3. Emit sequence of events (session start, commands, session end).
4. Dashboard receives and displays updates in near real time.

## Quick Start (Local)

Prerequisites:
1. Python 3.10+ (or your configured venv).
2. Node.js 18+.
3. npm.

### 1) Backend

From project root:

```bash
cd backend/api
python main.py
```

If you prefer uvicorn directly:

```bash
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

### 2) Frontend

From project root:

```bash
cd dashboard-deploy
npm install
npm run dev
```

Open:
`http://localhost:5173`

### 3) Run Attack Simulation

From project root:

```bash
python backend/simulate_attack.py
```

You should see alert feed, chart values, and counters update.

## Build and Deployment

Frontend build:

```bash
cd dashboard-deploy
npm run build
```

Deployable output:
1. Built static files in `dashboard-deploy/dist`.
2. Curated source package in `dashboard-deploy-ready` for manual push.

## Environment and Configuration Notes

Current defaults in frontend are localhost URLs:
1. API base: `http://localhost:8000/api`
2. WebSocket: `ws://localhost:8000/ws/alerts`

For production, move these to environment variables and set per environment.

## Known Limitations (Demo Scope)

1. Backend state is in-memory (not persistent DB).
2. Optional Kafka mode depends on local broker availability.
3. Map marker HTML rendering is optimized for visual control, not hardened for untrusted external text.
4. Frontend currently emphasizes demo speed and visual clarity over production-level state normalization.

## Recommended Next Improvements

1. Add persistent storage (PostgreSQL/Redis) for alert history.
2. Add authentication and role-based dashboard access.
3. Move API/WS URLs to env vars in frontend.
4. Harden rendering/sanitization for any user-controlled text.
5. Add end-to-end tests for real-time event flow.

## Troubleshooting

If dashboard is blank:
1. Ensure backend is running on port 8000.
2. Ensure frontend is running on port 5173.
3. Hard refresh browser (`Ctrl + F5`).

If updates are not live:
1. Check browser console for WebSocket errors.
2. Confirm `WS /ws/alerts` is reachable.
3. Run simulator and verify `GET /api/alerts` count increases.

If theme looks stale:
1. Clear local storage key `chakravyuh-theme`.
2. Hard refresh browser.

## License

Hackathon/demo project. Add your preferred license file for production/open-source distribution.


# Chakravyuh Execution Roadmap (Mar 20 - Mar 26, 2026)

To pull this off, we need absolute parallel execution.

## Team Ownership and Focus

### Member 1: AI/Data Engineer
- Focus: Module 1 (ML Threat Detector) and Module 2 (Federated Learning Aggregator)
- Core Stack: PyTorch, Flower (`flwr`)
- Goal: Build the autoencoder, generate synthetic network flows, and ensure `run_mock_federation()` runs flawlessly
- Constraint: Do not use the real CICIDS dataset right now; use synthetic data only

### Member 2: Infra/Security Specialist
- Focus: Module 3 (Generative Trap Controller) and Module 4 (GenAI Honeypot Server)
- Core Stack: Docker SDK, Ollama/Mistral, Kafka
- Goal: Ensure Docker containers spin up instantly and hook up Ollama so the fake SSH shell responds dynamically to attacker commands

### Member 3: API and Integration Lead
- Focus: Module 5 (Auto-SOC API) and the central nervous system
- Core Stack: FastAPI, WebSockets
- Goal: Build REST endpoints and fix the missing Kafka consumer so telemetry flows from trap to API
- Responsibility: Bridge the Honeypot and the Dashboard

### Member 4: Frontend Ninja and Pitch Owner
- Focus: Module 6 (SOC Dashboard) and final presentation deck
- Core Stack: React, D3.js
- Goal: Replace mock UI data with a real WebSocket connection to `ws://localhost:8000/ws/alerts`
- Quality Bar: Make visuals (especially Federated Node Map and Threat Timeline) sophisticated and government-ready

## 7-Day Sprint Schedule

We have exactly one week. Adhere strictly to these daily milestones.

| Date | Phase | Critical Deliverables |
|---|---|---|
| Fri, Mar 20 | Scaffolding | Initialize Git repo. Set up `docker-compose.yml`. Add `docker` and `kafka-python` to `requirements.txt`. API Lead builds dummy FastAPI endpoints. |
| Sat, Mar 21 | The Brain and The Trap | AI Lead trains the PyTorch autoencoder on generated data. Infra Specialist gets `DockerTrapSpawner` working to isolate attackers. |
| Sun, Mar 22 | The Illusion | Infra Specialist integrates the Ollama/Mistral LLM so the honeypot shell responds realistically. Frontend Ninja finishes the static React UI layout. |
| Mon, Mar 23 | Integration (Hardest Day) | API Lead consumes Kafka telemetry from the trap. Frontend Ninja connects the React dashboard to the FastAPI WebSocket. |
| Tue, Mar 24 | Federation and Refinement | AI Lead finalizes the `ChakravyuhAggregator` for the mock federation demo. Map attacker commands to MITRE ATT&CK TTPs. |
| Wed, Mar 25 | The Pitch Deck | Frontend/Pitch Owner finalizes slides. Narrative must emphasize DPDP Act compliance and sovereign zero-foreign-cloud dependency. |
| Thu, Mar 26 | Dry Runs | Freeze all code. Run end-to-end demo: start attack, show anomaly score, redirect to honeypot, and watch D3.js dashboard light up. Rehearse the pitch 5 times. |

## Non-Negotiables
- Parallel execution across all four members from day 1
- No scope creep beyond the sprint goals
- Synthetic-data-first delivery for ML/federation demo reliability
- End-to-end demo readiness by Mar 26

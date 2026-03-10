# Chakravyuh — Project Roadmap & Build Timeline

> **Showcase Date: March 28, 2026**
> **Build Window: March 10 – March 27, 2026 (18 days)**
> **Code Freeze & Full Testing Buffer: March 25 – March 27 (3 days)**

---

## Timeline Overview

| Phase | Description | Dates | Duration |
|-------|-------------|-------|----------|
| **Phase 0** | Foundation & Dev Environment | Mar 10 | 1 day |
| **Phase 1** | Edge Node — Local Anomaly Detection | Mar 11 – Mar 12 | 2 days |
| **Phase 2** | Federated Aggregation Engine | Mar 13 – Mar 14 | 2 days |
| **Phase 3** | Generative Trap Controller (Honeypot) | Mar 15 – Mar 17 | 3 days |
| **Phase 4** | Auto-SOC: LLM Security Analyst | Mar 18 – Mar 20 | 3 days |
| **Phase 5** | Graph Threat Intelligence Engine | Mar 20 – Mar 21 | 2 days |
| **Phase 6** | SOC Dashboard (UI) | Mar 21 – Mar 23 | 3 days |
| **Phase 7** | Hardening, Compliance & Demo Prep | Mar 24 – Mar 25 | 2 days |
| **Buffer** | Final Testing, Red Team & Rehearsal | Mar 25 – Mar 27 | 3 days |
| 🎯 **Showcase** | **India Innovates 2026** | **Mar 28** | — |

---

## Phase 0 — Foundation & Dev Environment
**Dates: March 10 | Duration: 1 day**

**Goal:** Reproducible local dev environment that mirrors the full production topology.

**Steps:**
1. Scaffold the monorepo structure:

chakravyuh/
├── edge-node/ # Python — Federated Learning client
├── aggregator/ # Python — Flower/PySyft server
├── trap-controller/ # Go — Honeypot orchestrator
├── auto-soc/ # Python — LLM analyst agent
├── streaming/ # Kafka config + Avro schema registry
├── graph-engine/ # Python — Neo4j + GNN pipeline
├── dashboard/ # Next.js — SOC UI
└── infra/ # Docker Compose + K8s manifests

2. Set up **Docker Compose** dev stack: Kafka + Zookeeper, Neo4j, Ollama (Llama-3 8B), Flower server, one simulated edge node.
3. Define shared **Avro/Protobuf schemas** for all inter-service messages (threat events, model weight diffs, alert payloads).
4. Establish CI pipeline (GitHub Actions): lint, unit tests, Docker image builds.

**Verification:** `docker compose up` brings all services healthy; schemas validate against sample payloads.

---

## Phase 1 — Edge Node: Local Anomaly Detection
**Dates: March 11 – March 12 | Duration: 2 days**

**Goal:** Lightweight ML model detecting network anomalies on raw traffic at edge (hospital/bank node), sharing only learned patterns — never raw data.

**Steps:**
1. Build a **PyTorch Autoencoder** (+ Isolation Forest baseline) trained on synthetic benign network flow data (CICIDS2017/NSL-KDD datasets).
2. Wrap the model in a **Flower `fl.client.NumPyClient`** — accepts and returns gradient weight diffs only, never raw traffic samples.
3. Implement a **local log parser in Rust** (`edge-node/parser/`) using `tokio` async I/O to ingest pcap/syslog, extract feature vectors (packet rate, entropy, port distribution), and feed the model in real-time.
4. Emit anomaly events to local Kafka topic `edge.anomalies` with severity scores and feature hashes (zero raw payload).
5. Unit test: replay a PCAP file through the parser, verify anomaly scores exceed threshold for known attack signatures.

**Verification:** Known attack PCAP → anomaly score > 0.85; benign traffic → score < 0.3.

---

## Phase 2 — Federated Aggregation Engine
**Dates: March 13 – March 14 | Duration: 2 days**

**Goal:** Central hub (simulating CERT-In/NCIIPC) aggregating model weights from all edge nodes using Federated Averaging — updating a global defense model with zero raw data transfer.

**Steps:**
1. Stand up a **Flower `fl.server.Server`** in `aggregator/` with `FedAvg` strategy.
2. Implement **differential privacy noise injection** (using `opacus` library) on incoming weight updates — the cryptographic DPDP compliance guarantee.
3. Configure minimum **client quorum** (≥3 edge nodes must report) before a global round triggers.
4. After each federated round, serialize the updated global model and push a `model.updated` event to Kafka topic `hub.model-updates`.
5. Store round history and per-node contribution metrics in **Neo4j** as a provenance graph.
6. Integration test: 3 simulated edge nodes in Docker, 5 federated rounds, verify global model loss decreases.

**Verification:** Global loss decreases monotonically across 5 rounds; Neo4j shows round provenance graph populated correctly.

---

## Phase 3 — Generative Trap Controller (Honeypot Deception)
**Dates: March 15 – March 17 | Duration: 3 days**

**Goal:** On breach detection, auto-provision isolated fake environments populated with GenAI-generated synthetic data — indistinguishable from real production systems.

**Steps:**
1. Build a **Go microservice** (`trap-controller/`) subscribing to Kafka topic `hub.breach-detected`.
2. On event receipt, use the **Kubernetes Go client (`client-go`)** to dynamically create an isolated `Namespace` + `Pod` running a fake SSH/HTTP/database service (templates in `infra/honeypot-templates/`).
3. Integrate **Ollama API** (local, no external calls) to generate synthetic realistic file systems, database rows, and config files inside the honeypot container.
4. Deploy a **network tap** (`libpcap` Go bindings) inside each honeypot namespace to capture all attacker TTPs (tools, techniques, procedures).
5. Stream captured attacker telemetry to Kafka topic `trap.telemetry` using Avro schema.
6. Implement **honeypot lifecycle management**: auto-destroy after 30 minutes or attacker exit; archive telemetry to cold storage.

**Verification:** Simulated attacker (`nmap` probe in isolated lab) enters honeypot → TTPs appear in Kafka within 500ms; honeypot auto-destroys on schedule.

---

## Phase 4 — Auto-SOC: LLM Security Analyst
**Dates: March 18 – March 20 | Duration: 3 days**

**Goal:** Localized LLM that processes threat telemetry, auto-resolves L1/L2 alerts, and generates human-readable incident reports — targeting 80% alert fatigue reduction.

**Steps:**
1. Set up **Ollama** serving `llama3:8b` locally in `auto-soc/` — zero external API dependency.
2. Build a **Python consumer** (`auto-soc/agent.py`) reading Kafka topics `edge.anomalies` + `trap.telemetry`.
3. Design a structured **prompt chain** (raw Ollama API or LangChain):
- Stage 1: Classify alert severity (P1/P2/P3) + map to MITRE ATT&CK framework.
- Stage 2: P3 (low) → auto-resolve with tagged remediation script. P1/P2 → escalate.
- Stage 3: Generate plain-English incident brief ("At 14:32 IST, SSH brute-force from IP X targeted edge node Y...").
4. Write auto-remediation playbooks (Python/Bash) for top 10 alert types: port scan, brute force, DNS tunneling, etc. — stored in `auto-soc/playbooks/`.
5. Push resolved/escalated incidents to Kafka topic `soc.incidents`; write to **Neo4j** linking attacker IP → techniques → affected nodes.

**Verification:** 10,000 synthetic alerts/min → ≥80% P3 auto-resolved; average LLM response latency <2s per alert.

---

## Phase 5 — Graph Threat Intelligence Engine
**Dates: March 20 – March 21 | Duration: 2 days**

**Goal:** Visualize lateral attacker movement and cross-sector threat correlation using Neo4j + Graph Neural Networks.

**Steps:**
1. Define **Neo4j graph schema**: Nodes = `IPAddress`, `EdgeNode`, `Sector`, `ThreatActor`, `Technique` (MITRE ATT&CK). Relationships = `ATTACKED`, `USES_TECHNIQUE`, `LATERAL_MOVE_TO`, `SHARES_PATTERN_WITH`.
2. Build a **Python ETL pipeline** (`graph-engine/ingest.py`) consuming `soc.incidents` from Kafka and writing entities/relationships to Neo4j via Bolt protocol.
3. Implement a **Graph Neural Network** (PyTorch Geometric / `PyG`) on Neo4j exports to predict: *"given attacker's current node, what is the likely next lateral movement target?"*
4. Expose GNN predictions via a **FastAPI endpoint** (`/api/threat/predict-lateral`) consumed by the dashboard.
5. Write **Cypher queries** for dashboard views: top threat actors, cross-sector attack correlations, most-targeted node types.

**Verification:** Lateral movement prediction accuracy >70% on held-out test graph; Neo4j browser shows correct attacker path visualization.

---

## Phase 6 — SOC Dashboard (UI)
**Dates: March 21 – March 23 | Duration: 3 days**

**Goal:** Non-technical official-facing dashboard showing real-time threat status, incident reports, and live threat graph.

**Steps:**
1. Bootstrap a **Next.js 14** app in `dashboard/` with Tailwind CSS.
2. Build 5 key views:
- **Live Threat Map** — D3.js force-directed graph rendering the Neo4j threat graph via WebSocket (real-time attacker path visualization).
- **Alert Feed** — Real-time stream from `soc.incidents` via Server-Sent Events.
- **Auto-SOC Log** — LLM-generated incident briefs, auto-resolution outcomes, escalation queue.
- **Federated Model Health** — Active edge nodes, last round timestamp, global model accuracy trend.
- **Honeypot Activity** — Active traps, attacker dwell time, captured TTPs summary.
3. All data fetched from a **Go API Gateway** (`backend-gateway/`) in front of Kafka, Neo4j, and Auto-SOC.
4. Auth: **Keycloak (OIDC)** with role-based access — CERT-In analyst vs. sector node admin.

**Verification:** Dashboard renders live threat graph; SSE alert feed updates in <100ms; all 5 views load correctly.

---

## Phase 7 — Hardening, Compliance & Demo Prep
**Dates: March 24 – March 25 | Duration: 2 days**

**Goal:** Production-grade security posture, DPDP compliance documentation, and a polished showcase demo.

**Steps:**
1. **Zero-Trust networking**: Istio service mesh with mutual TLS between all microservices — no east-west traffic without policy.
2. **Supply-chain security**: Sign all container images with Cosign (Sigstore); generate SBOM via `syft` in CI pipeline.
3. **DPDP Compliance Document**: Formal data-flow diagram confirming no raw PII/institutional data leaves edge nodes — only DP-noised model weights transit.
4. **Demo scenario scripting**: Stage the full end-to-end attack path:
- Adversary scans "hospital edge node" → anomaly detected
- Honeypot spun up → attacker lured in
- TTPs captured → Auto-SOC generates incident brief
- Dashboard shows lateral movement prediction graph
5. Record a **3-minute demo video** as a backup for the live showcase.

**Verification:** Istio policies block unauthorized inter-service calls; demo scenario runs end-to-end without manual intervention.

---

## Final Buffer — Testing, Red Team & Rehearsal
**Dates: March 25 – March 27 | Duration: 3 days**

**Goal:** Full system validation, adversarial stress testing, and showcase rehearsal.

| Day | Activity |
|-----|----------|
| **Mar 25** | Full end-to-end integration test — run complete attack scenario across all 7 phases. Bug fixes. |
| **Mar 26** | **Red Team exercise**: Simulate APT attack using [Caldera framework](https://github.com/mitre/caldera). Measure Time-to-Detect (TTD) and Time-to-Contain (TTC). Target: TTD <30s. |
| **Mar 27** | Showcase rehearsal — full dry run of live demo. Finalize slide deck. Verify all Docker containers start cleanly on showcase machine. Prepare offline fallback (recorded demo video). |

---

## Showcase Day — March 28, 2026

**Demo Script (5-minute live walkthrough):**

1. **[0:00]** Introduce the 3 gaps in India's current cyber defense (reactive, privacy roadblock, talent deficit).
2. **[0:45]** Show live edge node detecting an anomaly on the dashboard.
3. **[1:30]** Trigger a simulated breach — watch the honeypot spin up in real-time (K8s namespace creation).
4. **[2:30]** Show the attacker exploring the GenAI-generated fake environment; TTPs appearing in the Auto-SOC log.
5. **[3:15]** Auto-SOC LLM generates a plain-English incident brief — highlight "no human analyst needed."
6. **[4:00]** Show the live threat graph in Neo4j/dashboard — lateral movement prediction lighting up.
7. **[4:30]** Close with DPDP compliance slide — "zero raw data ever left the edge node."

---

## Verification Checkpoints

| Phase | Test | Target |
|-------|------|--------|
| Phase 1 | Replay PCAP → anomaly score on known attacks | Score > 0.85 |
| Phase 2 | 5 federated rounds, 3 nodes | Global loss decreases monotonically |
| Phase 3 | Attacker enters honeypot → Kafka TTPs | Within 500ms |
| Phase 4 | 10K alerts/min load test | ≥80% P3 auto-resolved, <2s latency |
| Phase 5 | Lateral movement GNN on held-out graph | Prediction accuracy >70% |
| Phase 6 | Live dashboard SSE refresh | <100ms update latency |
| Phase 7 | End-to-end red team (Caldera) | TTD <30s, full incident brief generated |

---

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| FL Framework | **Flower** over PySyft | More production-tested; active community; better K8s integration |
| Trap Controller language | **Go** | `client-go` K8s library + goroutine concurrency for spinning up 100s of honeypots under load |
| LLM size | **Llama-3 8B** over 70B | Fits single GPU; <2s inference; upgradeable post-showcase |
| Message bus | **Kafka** over RabbitMQ | Log-compaction and replay semantics critical for forensic reconstruction |
| Repo structure | **Monorepo** | Shared Protobuf schemas and CI; prevents contract drift across 6+ services |
| Privacy mechanism | **Differential Privacy (opacus)** | Mathematical guarantee for DPDP compliance — not just policy, but provable |

---

*Built for India Innovates 2026 — Defending India's Digital Borders.*
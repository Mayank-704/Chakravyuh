# Chakravyuh — The Sovereign AI Defense Grid

> **An automated, proactive cyber defense framework — India's "Iron Dome" for its digital borders.**

[![Stack: Federated AI](https://img.shields.io/badge/Stack-Federated%20AI-green)](#tech-stack)
[![DPDP Compliant](https://img.shields.io/badge/DPDP%202023-Compliant%20by%20Design-orange)](#why-chakravyuh-stands-out)

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Why Chakravyuh Stands Out](#why-chakravyuh-stands-out)
- [References & Links](#references--links)

---

## Problem Statement

### The Vulnerability of India's Digital Core

India's **Critical Information Infrastructure (CII)** — spanning power grids, healthcare systems (e.g., AIIMS), and massive digital public goods like **UPI** — faces unprecedented, state-sponsored cyber threats. The existing defense posture has three foundational gaps:

| Gap | Description |
|-----|-------------|
| **Reactive & Siloed Defense** | An attack on a telecom network in Mumbai does not automatically protect a hospital in Delhi. Threat intelligence remains isolated across institutions and sectors. |
| **The Privacy Roadblock** | Under the **DPDP Act 2023**, sharing raw network or user data between public and private sector entities to hunt threats is legally complex and high-risk. |
| **The Talent Deficit** | India faces a severe shortage of skilled **Security Operations Center (SOC) analysts**, leaving systems overwhelmed by millions of daily alerts with no scalable resolution. |

---

## Solution

### Project Chakravyuh

Chakravyuh is an automated, proactive defense framework that shifts the paradigm from **merely blocking threats** to **predicting, trapping, and neutralizing them**.

**How it solves the problem:**

- **Decentralized Intelligence**
  AI models are trained locally at each institution (bank, hospital, power node). Only the *learned patterns* — never raw data — are shared with the government hub. This completely bypasses privacy and compliance risks.

- **Active GenAI Deception**
  Instead of relying on static firewalls, Chakravyuh uses **Generative AI** to instantly spin up highly realistic, fake server environments. When attackers breach the perimeter, they are lured into and studied within these controlled traps.

- **Autonomous Auto-SOC**
  A localized **Large Language Model (LLM)** acts as an AI security analyst — automatically resolving low-level alerts and translating complex threat data into plain-language dashboards accessible to non-technical officials.

---

## Architecture

### System Design & Data Flow

Chakravyuh is designed for **zero-trust, high-speed threat mitigation** across geographically distributed edge nodes.

```
┌─────────────────────────────────┐
│  Edge Nodes (Hospitals / Banks) │
│  Local Anomaly Detection Model  │
└────────────────┬────────────────┘
                 │ Cryptographic Weights Only
                 ▼
┌─────────────────────────────────────────┐
│  Federated Aggregation Engine           │
│  (CERT-In / NCIIPC Hub)                 │
│  Updates Global Defense Model           │
└──────────┬──────────────────────────────┘
           │ Breach Detected
           ▼
┌───────────────────────────────────────┐
│  Generative Trap Controller           │
│  Spins up isolated Docker containers  │
│  filled with synthetic GenAI data     │
└──────────┬────────────────────────────┘
           │ Threat Telemetry (Kafka Stream)
           ▼
┌───────────────────────────────────────┐
│  Response Microservices / Auto-SOC    │
│  Automated Isolation + LLM Analysis   │
└───────────────────────────────────────┘
```

**Core Flow:**

1. **Edge Nodes** — Lightweight anomaly detection models run locally on incoming network traffic at hospitals, banks, and critical infrastructure.
2. **Federated Aggregation Engine** — Only cryptographic model weights (threat patterns) are transmitted to the central CERT-In/NCIIPC hub, updating a shared global defense model *without moving any sensitive raw data*.
3. **Generative Trap Controller** — On detecting a breach, the controller automatically provisions isolated Docker containers populated with synthetic, GenAI-crafted data to distract and study the malware.
4. **Response Microservices** — Threat data captured from the trap is streamed via messaging queues to the Auto-SOC, which triggers automated isolation scripts and escalates critical threats.

---

## Tech Stack

### The Chakravyuh Stack

Built entirely on **open-source, locally hosted tools** to ensure performance, sovereignty, and zero dependency on foreign commercial APIs.

| Domain | Technologies |
|--------|-------------|
| **Federated Learning & ML** | [Flower (flower.ai)](https://flower.ai) / [PySyft](https://github.com/OpenMined/PySyft), PyTorch for deep learning anomaly detection |
| **Graph Threat Mapping** | [Neo4j](https://neo4j.com) (Graph Database) + Graph Neural Networks (GNNs) to visualize lateral attacker movement across infrastructure |
| **GenAI & Auto-SOC** | [Ollama](https://ollama.com) / [vLLM](https://github.com/vllm-project/vllm) running open-weight models (Llama-3, Mistral) — fully local, no external API calls |
| **Backend & Streaming** | Rust / Go for ultra-fast, memory-safe network log parsing; [Apache Kafka](https://kafka.apache.org) for real-time telemetry streaming |
| **Deception Infrastructure** | [Kubernetes](https://kubernetes.io) + [Docker](https://www.docker.com) for dynamic orchestration of honeypot environments |

---

## Why Chakravyuh Stands Out

### Key Differentiators

**1. 100% DPDP Compliant by Design**
Federated Learning ensures that zero raw personal or institutional data ever leaves its host network. Chakravyuh shares intelligence, not data — making it legally sound under the Digital Personal Data Protection Act 2023.

**2. Dynamic, Not Static, Defense**
Traditional honeypots are easily identified and bypassed by modern malware. Chakravyuh's **GenAI deception grids** adapt in real-time, generating environments that are indistinguishable from production systems.

**3. Force Multiplier for Cyber Teams**
The localized Auto-SOC autonomously handles up to **80% of alert fatigue**, freeing human security experts to focus exclusively on zero-day and high-level strategic threats.

**4. Sovereign Architecture**
Designed entirely on open-source, locally hosted infrastructure. The core defense logic has **no reliance on foreign cloud APIs**, ensuring national data sovereignty and resilience against supply-chain attacks.

---

## References & Links

### Project Resources

| Resource | Link |
|----------|------|
| **Live Demo Video** | Coming soon — Demo of the GenAI Trap working in action |

### Frameworks & Tools

- **Flower Federated Learning Framework** — [flower.ai](https://flower.ai)
- **Local LLM Deployment** — [ollama.com](https://ollama.com)

### Regulatory Alignment

This project's architecture and data-handling design has been conceptually mapped to:

- **CERT-In Cyber Security Directions (2022)** — Compliance with mandatory incident reporting and infrastructure protection guidelines issued by the Indian Computer Emergency Response Team.
- **Digital Personal Data Protection Act (2023)** — Federated Learning ensures no raw personal or institutional data is transmitted, aligning with DPDP's data minimization and purpose limitation principles.


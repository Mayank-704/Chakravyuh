from __future__ import annotations

import threading
import time
import flwr as fl

from .federated_aggregator import ChakravyuhAggregator
from .federated_client import ChakravyuhClient


def run_mock_federation(host="127.0.0.1", port=8080, rounds=5, dim=16) -> None:
    address = f"{host}:{port}"
    agg = ChakravyuhAggregator(host=host, port=port, num_rounds=rounds)

    def _start_client(name: str, seed: int):
        time.sleep(1.0)
        client = ChakravyuhClient(institution=name, dim=dim, seed=seed)
        fl.client.start_numpy_client(server_address=address, client=client)

    client_threads = [
        threading.Thread(target=_start_client, args=("AIIMS", 101), daemon=False),
        threading.Thread(target=_start_client, args=("SBI", 202), daemon=False),
        threading.Thread(target=_start_client, args=("GOV", 303), daemon=False),
    ]

    print("[Simulation] Starting clients: AIIMS, SBI, GOV")
    for t in client_threads:
        t.start()

    # Run server in main thread (good)
    agg.start()

    # IMPORTANT: wait for clients to exit cleanly
    for t in client_threads:
        t.join(timeout=10)

    print("[Simulation] Done.")

if __name__ == "__main__":
    run_mock_federation()
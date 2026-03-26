from __future__ import annotations

from dataclasses import dataclass

import flwr as fl

from .federated_strategy import ChakravyuhFedAvg


@dataclass
class ChakravyuhAggregator:
    """CERT-In-like central hub that aggregates client weights via FedAvg."""

    host: str = "127.0.0.1"
    port: int = 8080
    num_rounds: int = 5
    min_fit_clients: int = 3
    min_available_clients: int = 3

    def start(self) -> fl.server.history.History:
        address = f"{self.host}:{self.port}"
        strategy = ChakravyuhFedAvg(
            fraction_fit=1.0,
            min_fit_clients=self.min_fit_clients,
            min_available_clients=self.min_available_clients,
        )

        print(f"[Aggregator] Starting server at {address} for {self.num_rounds} rounds")
        history = fl.server.start_server(
            server_address=address,
            config=fl.server.ServerConfig(num_rounds=self.num_rounds),
            strategy=strategy,
        )
        print("[Aggregator] Finished.")
        return history
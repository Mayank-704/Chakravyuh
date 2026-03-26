from __future__ import annotations

from typing import Dict, Optional

import flwr as fl


class ChakravyuhFedAvg(fl.server.strategy.FedAvg):
    """
    Custom strategy hook.

    Today: just FedAvg.
    Later: you can add DP, anomaly detection, client weighting rules, etc.
    """

    def __init__(
        self,
        fraction_fit: float = 1.0,
        min_fit_clients: int = 3,
        min_available_clients: int = 3,
    ):
        super().__init__(
            fraction_fit=fraction_fit,
            fraction_evaluate=0.0,
            min_fit_clients=min_fit_clients,
            min_evaluate_clients=0,
            min_available_clients=min_available_clients,
            on_fit_config_fn=self.fit_config,
        )

    def fit_config(self, server_round: int) -> Dict[str, fl.common.Scalar]:
        return {
            "server_round": server_round,
            "dpdp_note": "Only model weights are shared; no raw data leaves the institution.",
        }
"""
Chakravyuh - Federated Client
==============================
Represents one institution (AIIMS / SBI / GOV) in the federation.

Two modes:
  - REAL mode : trains the actual NetworkAutoencoder from Phase 1 on local
                synthetic flows. Sends real model weights to the hub.
  - TOY mode  : fallback when Phase 1 is not installed. Trains a tiny
                2-parameter toy model so the Flower demo still runs.

The switch is automatic — if phase1_ml_detector is importable, REAL mode
is used. Otherwise falls back to TOY mode silently.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import numpy as np
import flwr as fl

from .federated_utils import init_toy_model, copy_params

# ---------------------------------------------------------------------------
# Try to import Phase 1 components
# ---------------------------------------------------------------------------
try:
    from phase1_ml_detector.network_autoencoder import NetworkAutoencoder
    from phase1_ml_detector.flow_preprocessor import FlowPreprocessor
    PHASE1_AVAILABLE = True
except ImportError:
    PHASE1_AVAILABLE = False


# ---------------------------------------------------------------------------
# Institution profiles
# Used in REAL mode to generate institution-specific synthetic flows,
# and in TOY mode for the target-weight simulation.
# ---------------------------------------------------------------------------
INSTITUTION_PROFILES: Dict[str, Dict] = {
    "AIIMS": {
        "num_examples": 1200,
        "anomaly_rate": 0.05,   # hospitals see fewer anomalies in normal ops
        "toy_base": 0.8,
    },
    "SBI": {
        "num_examples": 800,
        "anomaly_rate": 0.08,   # banks see slightly more probing attempts
        "toy_base": -0.4,
    },
    "GOV": {
        "num_examples": 500,
        "anomaly_rate": 0.06,
        "toy_base": 0.2,
    },
}

DEFAULT_PROFILE = {"num_examples": 300, "anomaly_rate": 0.05, "toy_base": 0.0}


# ---------------------------------------------------------------------------
# Helper: extract numpy weight arrays from NetworkAutoencoder
# ---------------------------------------------------------------------------
def _model_to_params(autoencoder: "NetworkAutoencoder") -> List[np.ndarray]:
    """
    Convert NetworkAutoencoder (FlowAutoencoder inside) state_dict
    to a flat list of numpy arrays — the format Flower expects.
    """
    return [
        val.cpu().numpy()
        for val in autoencoder.model.state_dict().values()
    ]


def _params_to_model(
    params: List[np.ndarray],
    autoencoder: "NetworkAutoencoder",
) -> None:
    """
    Load a flat list of numpy arrays back into the autoencoder model.
    Mutates autoencoder.model in-place.
    """
    import torch
    from collections import OrderedDict

    keys = list(autoencoder.model.state_dict().keys())
    if len(keys) != len(params):
        raise ValueError(
            f"Parameter count mismatch: model has {len(keys)} tensors, "
            f"received {len(params)}"
        )
    new_state = OrderedDict(
        {k: torch.tensor(v) for k, v in zip(keys, params)}
    )
    autoencoder.model.load_state_dict(new_state)


# ---------------------------------------------------------------------------
# REAL mode: local training on NetworkAutoencoder
# ---------------------------------------------------------------------------
def _real_local_train(
    params: List[np.ndarray],
    institution: str,
    server_round: int,
    local_epochs: int = 3,
    window_size: int = 5,
) -> Tuple[List[np.ndarray], int, Dict]:
    """
    Train the real NetworkAutoencoder on institution-specific synthetic flows.

    Steps:
      1. Generate synthetic normal flows for this institution
      2. Load global weights received from hub into local model
      3. Train for local_epochs
      4. Return updated weights + metrics
    """
    profile = INSTITUTION_PROFILES.get(institution.upper(), DEFAULT_PROFILE)
    n_samples = profile["num_examples"]

    # 1. Generate local synthetic flows (normal traffic only — autoencoder
    #    trains on normal data, detects deviations as anomalies)
    preprocessor = FlowPreprocessor(window_size=window_size)
    flows_df, _ = preprocessor.generate_synthetic_flows(
        n_samples=n_samples,
        anomaly_rate=0.0,   # train on normal only
    )
    X = preprocessor.fit_transform(flows_df)
    X_seq, _ = preprocessor.create_sequences(X)

    if len(X_seq) == 0:
        raise RuntimeError("No sequences generated — increase n_samples or reduce window_size")

    n_features = X_seq.shape[2]

    # 2. Build model and load global weights from hub
    autoencoder = NetworkAutoencoder(
        input_dim=n_features,
        seq_length=window_size,
        latent_dim=16,
        batch_size=32,
    )
    _params_to_model(params, autoencoder)

    # 3. Local training
    history = autoencoder.fit(
        X_train=X_seq,
        epochs=local_epochs,
        early_stopping_patience=5,
        verbose=False,
    )

    final_loss = history["train_loss"][-1] if history["train_loss"] else 0.0

    # 4. Extract updated weights
    updated_params = _model_to_params(autoencoder)

    metrics = {
        "loss": float(final_loss),
        "institution": institution,
        "server_round": server_round,
        "n_features": n_features,
        "n_sequences": len(X_seq),
        "mode": "real",
    }

    print(
        f"[Client:{institution}] REAL mode | round={server_round} "
        f"sequences={len(X_seq)} loss={final_loss:.6f}"
    )

    return updated_params, n_samples, metrics


# ---------------------------------------------------------------------------
# TOY mode: fallback synthetic training (no Phase 1 needed)
# ---------------------------------------------------------------------------
def _toy_local_train(
    params: List[np.ndarray],
    institution: str,
    server_round: int,
    steps: int = 25,
    lr: float = 0.04,
    seed: int = 0,
) -> Tuple[List[np.ndarray], int, Dict]:
    """
    Synthetic local training on a 2-parameter toy model.
    Used when phase1_ml_detector is not available.
    Each institution converges toward a different target — simulates
    heterogeneous data across institutions.
    """
    rng = np.random.default_rng(seed + server_round)
    profile = INSTITUTION_PROFILES.get(institution.upper(), DEFAULT_PROFILE)

    w, b = params[0].copy(), params[1].copy()
    dim = w.shape[0]

    base = profile["toy_base"]
    target_w = (base + 0.05 * server_round) * np.ones((dim,), dtype=np.float32)
    target_b = np.array([base], dtype=np.float32)
    target_w += rng.normal(0.0, 0.01, size=(dim,)).astype(np.float32)

    for _ in range(steps):
        w -= lr * 2.0 * (w - target_w)
        b -= lr * 2.0 * (b - target_b)

    loss = float(np.mean((w - target_w) ** 2) + np.mean((b - target_b) ** 2))

    metrics = {
        "loss": loss,
        "institution": institution,
        "server_round": server_round,
        "mode": "toy",
    }

    print(
        f"[Client:{institution}] TOY mode | round={server_round} "
        f"num_examples={profile['num_examples']} loss={loss:.6f}"
    )

    return (
        [w.astype(np.float32), b.astype(np.float32)],
        profile["num_examples"],
        metrics,
    )


# ---------------------------------------------------------------------------
# ChakravyuhClient — Flower NumPyClient
# ---------------------------------------------------------------------------
class ChakravyuhClient(fl.client.NumPyClient):
    """
    Flower client representing one institution in the federation.

    Automatically uses REAL mode (NetworkAutoencoder) if phase1_ml_detector
    is installed, otherwise falls back to TOY mode for demo purposes.
    """

    def __init__(
        self,
        institution: str,
        dim: int = 16,
        seed: int = 0,
        local_epochs: int = 3,
        window_size: int = 5,
        force_toy_mode: bool = False,
    ):
        """
        Args:
            institution   : "AIIMS", "SBI", or "GOV"
            dim           : Weight dimension for TOY mode (ignored in REAL mode)
            seed          : Random seed for reproducibility
            local_epochs  : Epochs per round in REAL mode
            window_size   : Flow sequence window for REAL mode
            force_toy_mode: Set True to force TOY mode even if Phase 1 is available
        """
        self.institution = institution
        self.seed = seed
        self.local_epochs = local_epochs
        self.window_size = window_size
        self.use_real_mode = PHASE1_AVAILABLE and not force_toy_mode

        if self.use_real_mode:
            # In REAL mode, initialize with a temporary model to get parameter
            # shapes. Actual weights will be replaced by hub on first fit().
            preprocessor = FlowPreprocessor(window_size=window_size)
            flows_df, _ = preprocessor.generate_synthetic_flows(n_samples=50)
            X = preprocessor.fit_transform(flows_df)
            X_seq, _ = preprocessor.create_sequences(X)
            n_features = X_seq.shape[2] if len(X_seq) > 0 else 12

            self._autoencoder = NetworkAutoencoder(
                input_dim=n_features,
                seq_length=window_size,
                latent_dim=16,
                batch_size=32,
            )
            self.parameters = _model_to_params(self._autoencoder)
            print(
                f"[Client:{institution}] Initialized in REAL mode | "
                f"n_features={n_features} | "
                f"param_tensors={len(self.parameters)}"
            )
        else:
            self.parameters = init_toy_model(dim=dim, seed=seed)
            mode_reason = "forced" if force_toy_mode else "phase1_ml_detector not found"
            print(
                f"[Client:{institution}] Initialized in TOY mode ({mode_reason})"
            )

    # ------------------------------------------------------------------
    # Flower interface
    # ------------------------------------------------------------------
    def get_parameters(self, config) -> List[np.ndarray]:
        return self.parameters

    def fit(
        self,
        parameters: List[np.ndarray],
        config: Dict,
    ) -> Tuple[List[np.ndarray], int, Dict]:
        """
        Receive global weights from hub, train locally, return updated weights.
        Raw data NEVER leaves this client — only weight updates are returned.
        """
        self.parameters = copy_params(parameters)
        server_round = int(config.get("server_round", 1))

        if self.use_real_mode:
            updated, num_examples, metrics = _real_local_train(
                params=self.parameters,
                institution=self.institution,
                server_round=server_round,
                local_epochs=self.local_epochs,
                window_size=self.window_size,
            )
        else:
            updated, num_examples, metrics = _toy_local_train(
                params=self.parameters,
                institution=self.institution,
                server_round=server_round,
                seed=self.seed,
            )

        self.parameters = updated
        return self.parameters, num_examples, metrics

    def evaluate(
        self,
        parameters: List[np.ndarray],
        config: Dict,
    ) -> Tuple[float, int, Dict]:
        """Evaluation skipped in demo — return dummy values."""
        return 0.0, 0, {"institution": self.institution}

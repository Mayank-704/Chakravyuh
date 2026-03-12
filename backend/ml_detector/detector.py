"""
Chakravyuh - ML Threat Detector
================================
Anomaly detection on network flow logs using an Autoencoder neural network.
Trains locally, never sends raw data — only model weights for federation.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger


# ---------------------------------------------------------------------------
# Feature columns expected in network flow CSV
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "duration", "protocol_type", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot",
    "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files",
    "num_outbound_cmds", "is_host_login", "is_guest_login",
    "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
]

INPUT_DIM = len(FEATURE_COLS)


# ---------------------------------------------------------------------------
# Autoencoder Model
# ---------------------------------------------------------------------------
class NetworkAutoencoder(nn.Module):
    """
    Unsupervised anomaly detection via reconstruction error.
    Normal traffic → low reconstruction error.
    Attack traffic → high reconstruction error (anomaly score).
    """

    def __init__(self, input_dim: int = INPUT_DIM, latent_dim: int = 12):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Linear(64, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """Mean squared reconstruction error per sample."""
        with torch.no_grad():
            recon = self.forward(x)
            return ((x - recon) ** 2).mean(dim=1)


# ---------------------------------------------------------------------------
# Preprocessor
# ---------------------------------------------------------------------------
class FlowPreprocessor:
    """Normalizes raw network flow features for model input."""

    def __init__(self):
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def fit(self, df: pd.DataFrame) -> "FlowPreprocessor":
        data = self._extract(df)
        self.mean_ = data.mean(axis=0)
        self.std_ = data.std(axis=0) + 1e-8
        return self

    def transform(self, df: pd.DataFrame) -> torch.Tensor:
        data = self._extract(df)
        normalized = (data - self.mean_) / self.std_
        return torch.FloatTensor(normalized)

    def _extract(self, df: pd.DataFrame) -> np.ndarray:
        missing = [c for c in FEATURE_COLS if c not in df.columns]
        if missing:
            for col in missing:
                df[col] = 0.0
        return df[FEATURE_COLS].fillna(0).values.astype(np.float32)

    def save(self, path: str) -> None:
        import joblib
        joblib.dump({"mean": self.mean_, "std": self.std_}, path)

    @classmethod
    def load(cls, path: str) -> "FlowPreprocessor":
        import joblib
        obj = cls()
        data = joblib.load(path)
        obj.mean_ = data["mean"]
        obj.std_ = data["std"]
        return obj


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------
class DetectorTrainer:
    def __init__(self, model: NetworkAutoencoder, lr: float = 1e-3):
        self.model = model
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.criterion = nn.MSELoss()

    def train_epoch(self, loader: torch.utils.data.DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        for batch in loader:
            x = batch[0]
            self.optimizer.zero_grad()
            recon = self.model(x)
            loss = self.criterion(recon, x)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / len(loader)

    def train(self, X: torch.Tensor, epochs: int = 30, batch_size: int = 256) -> list[float]:
        dataset = torch.utils.data.TensorDataset(X)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        losses = []
        for epoch in range(epochs):
            loss = self.train_epoch(loader)
            losses.append(loss)
            if epoch % 5 == 0:
                logger.info(f"Epoch {epoch:03d}/{epochs} | Loss: {loss:.6f}")
        return losses


# ---------------------------------------------------------------------------
# Detector (Inference)
# ---------------------------------------------------------------------------
class ThreatDetector:
    """
    Runs inference on new network flows.
    Returns a list of ThreatEvent dicts for flagged flows.
    """

    def __init__(self, model_path: str, preprocessor_path: str, threshold: float = 0.05):
        self.model = NetworkAutoencoder()
        self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
        self.model.eval()
        self.preprocessor = FlowPreprocessor.load(preprocessor_path)
        self.threshold = threshold

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = self.preprocessor.transform(df)
        scores = self.model.anomaly_score(X).numpy()
        df = df.copy()
        df["anomaly_score"] = scores
        df["is_threat"] = scores > self.threshold
        df["severity"] = pd.cut(
            scores,
            bins=[0, 0.02, 0.05, 0.15, float("inf")],
            labels=["normal", "low", "medium", "critical"],
        )
        return df

    def stream_predict(self, flow: dict) -> dict:
        """Predict on a single flow dict (for real-time streaming)."""
        df = pd.DataFrame([flow])
        result = self.predict(df).iloc[0]
        return {
            "is_threat": bool(result["is_threat"]),
            "anomaly_score": float(result["anomaly_score"]),
            "severity": str(result["severity"]),
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def train_cli():
    import argparse, joblib

    parser = argparse.ArgumentParser(description="Train Chakravyuh ML Detector")
    parser.add_argument("--data", required=True, help="Path to network flow CSV")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--output", default="models/detector")
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading data from {args.data}")
    df = pd.read_csv(args.data)

    preprocessor = FlowPreprocessor().fit(df)
    X = preprocessor.transform(df)

    model = NetworkAutoencoder()
    trainer = DetectorTrainer(model)
    losses = trainer.train(X, epochs=args.epochs)

    torch.save(model.state_dict(), f"{args.output}/model.pt")
    preprocessor.save(f"{args.output}/preprocessor.pkl")
    logger.success(f"Model saved to {args.output}/")
    logger.info(f"Final loss: {losses[-1]:.6f}")


if __name__ == "__main__":
    train_cli()

"""
NetworkAutoencoder: PyTorch encoder-decoder for network flow anomaly detection.
Reconstruction loss = anomaly score
Trains on normal traffic only, detects deviations
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Tuple, Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlowAutoencoder(nn.Module):
    """
    Autoencoder for network flow sequences.
    
    Architecture:
    - Encoder: Compresses flow features to latent representation
    - Decoder: Reconstructs original flow from latent
    - Loss: MSE between input and reconstruction (anomaly indicator)
    """
    
    def __init__(
        self,
        input_dim: int,
        seq_length: int,
        hidden_dims: List[int] = None,
        latent_dim: int = 16,
        dropout: float = 0.2
    ):
        """
        Initialize autoencoder.
        
        Args:
            input_dim: Number of features per flow
            seq_length: Sequence length (number of flows in window)
            hidden_dims: List of hidden layer dimensions [64, 32] (encoder)
            latent_dim: Latent representation dimension
            dropout: Dropout probability
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.seq_length = seq_length
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims or [64, 32]
        
        flattened_dim = seq_length * input_dim
        
        # ENCODER: Compress sequence to latent vector
        encoder_layers = []
        prev_dim = flattened_dim
        
        for hidden_dim in self.hidden_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        # Bottleneck: latent representation
        encoder_layers.append(nn.Linear(prev_dim, latent_dim))
        self.encoder = nn.Sequential(*encoder_layers)
        
        # DECODER: Reconstruct sequence from latent
        decoder_layers = []
        hidden_dims_rev = list(reversed(self.hidden_dims))
        prev_dim = latent_dim
        
        for hidden_dim in hidden_dims_rev:
            decoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        decoder_layers.append(nn.Linear(prev_dim, flattened_dim))
        self.decoder = nn.Sequential(*decoder_layers)
        
        logger.info(
            f"Initialized Autoencoder: input_dim={input_dim}, "
            f"seq_length={seq_length}, latent_dim={latent_dim}"
        )
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode sequence to latent representation."""
        batch_size = x.shape[0]
        x_flat = x.view(batch_size, -1)
        return self.encoder(x_flat)
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent representation to reconstructed sequence."""
        x_recon = self.decoder(z)
        x_recon = x_recon.view(-1, self.seq_length, self.input_dim)
        return x_recon
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass: encode and decode.
        
        Args:
            x: Input sequences (batch_size, seq_length, input_dim)
            
        Returns:
            (reconstruction, latent)
        """
        z = self.encode(x)
        x_recon = self.decode(z)
        return x_recon, z
    
    def reconstruction_loss(self, x: torch.Tensor, x_recon: torch.Tensor) -> torch.Tensor:
        """Calculate reconstruction loss (MSE)."""
        return nn.MSELoss()(x_recon, x)
    
    def anomaly_scores(self, x: torch.Tensor) -> np.ndarray:
        """
        Calculate anomaly scores (reconstruction error).
        
        Args:
            x: Input sequences (batch_size, seq_length, input_dim)
            
        Returns:
            Anomaly scores (batch_size,) - higher = more anomalous
        """
        self.eval()
        with torch.no_grad():
            x_recon, _ = self.forward(x)
            # Per-sample reconstruction error
            errors = torch.mean((x - x_recon) ** 2, dim=(1, 2)).cpu().numpy()
        return errors


class NetworkAutoencoder:
    """
    Trainer and manager for flow autoencoder.
    Handles training, validation, and anomaly detection.
    """
    
    def __init__(
        self,
        input_dim: int,
        seq_length: int,
        latent_dim: int = 16,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 0.001,
        batch_size: int = 32
    ):
        """
        Initialize autoencoder trainer.
        
        Args:
            input_dim: Number of features per flow
            seq_length: Sequence length
            latent_dim: Latent dimension
            device: 'cuda' or 'cpu'
            learning_rate: Optimizer learning rate
            batch_size: Batch size for training
        """
        self.device = torch.device(device)
        self.input_dim = input_dim
        self.seq_length = seq_length
        self.latent_dim = latent_dim
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        
        # Initialize model
        self.model = FlowAutoencoder(
            input_dim=input_dim,
            seq_length=seq_length,
            latent_dim=latent_dim
        ).to(self.device)
        
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5, 
        )
        
        self.training_history = {
            'train_loss': [],
            'val_loss': [],
            'epoch': []
        }
        
        logger.info(
            f"NetworkAutoencoder initialized on {self.device} | "
            f"latent_dim={latent_dim}, batch_size={batch_size}"
        )
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Args:
            train_loader: DataLoader for training data
            
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        for X_batch, _ in train_loader:  # Ignore labels, use reconstruction only
            X_batch = X_batch.to(self.device)
            
            self.optimizer.zero_grad()
            x_recon, _ = self.model(X_batch)
            loss = self.model.reconstruction_loss(X_batch, x_recon)
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def validate(self, val_loader: DataLoader) -> float:
        """
        Validate on validation set.
        
        Args:
            val_loader: DataLoader for validation data
            
        Returns:
            Average validation loss
        """
        self.model.eval()
        total_loss = 0
        num_batches = 0
        
        with torch.no_grad():
            for X_batch, _ in val_loader:
                X_batch = X_batch.to(self.device)
                x_recon, _ = self.model(X_batch)
                loss = self.model.reconstruction_loss(X_batch, x_recon)
                total_loss += loss.item()
                num_batches += 1
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def fit(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray = None,
        epochs: int = 50,
        early_stopping_patience: int = 10,
        verbose: bool = True
    ) -> Dict:
        """
        Train autoencoder on normal traffic.
        
        Args:
            X_train: Training sequences (n_samples, seq_length, n_features)
            X_val: Validation sequences (optional)
            epochs: Number of training epochs
            early_stopping_patience: Epochs to wait before stopping
            verbose: Print progress
            
        Returns:
            Training history dictionary
        """
        logger.info(f"Starting training for {epochs} epochs...")
        
        # Create DataLoaders
        train_tensor = TensorDataset(
            torch.from_numpy(X_train).float(),
            torch.zeros(len(X_train))  # Dummy labels
        )
        train_loader = DataLoader(train_tensor, batch_size=self.batch_size, shuffle=True)
        
        val_loader = None
        if X_val is not None:
            val_tensor = TensorDataset(
                torch.from_numpy(X_val).float(),
                torch.zeros(len(X_val))
            )
            val_loader = DataLoader(val_tensor, batch_size=self.batch_size, shuffle=False)
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)
            
            val_loss = None
            if val_loader:
                val_loss = self.validate(val_loader)
                self.scheduler.step(val_loss)
                
                self.training_history['val_loss'].append(val_loss)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= early_stopping_patience:
                        logger.info(f"Early stopping at epoch {epoch}")
                        break
            
            self.training_history['train_loss'].append(train_loss)
            self.training_history['epoch'].append(epoch)
            
            if verbose and (epoch + 1) % max(1, epochs // 10) == 0:
                msg = f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f}"
                if val_loss:
                    msg += f" | Val Loss: {val_loss:.4f}"
                logger.info(msg)
        
        logger.info("Training completed!")
        return self.training_history
    
    def predict_anomalies(
        self,
        X: np.ndarray,
        threshold: float = None,
        percentile: float = 95
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies using reconstruction error.
        
        Args:
            X: Input sequences
            threshold: Anomaly threshold (if None, use percentile)
            percentile: Percentile for threshold calculation
            
        Returns:
            (anomaly_scores, binary_predictions)
        """
        X_tensor = torch.from_numpy(X).float().to(self.device)
        anomaly_scores = self.model.anomaly_scores(X_tensor)
        
        if threshold is None:
            threshold = np.percentile(anomaly_scores, percentile)
        
        predictions = (anomaly_scores > threshold).astype(int)
        
        logger.info(
            f"Detected {predictions.sum()} anomalies out of {len(X)} samples | "
            f"Threshold: {threshold:.4f}"
        )
        
        return anomaly_scores, predictions
    
    def save_model(self, path: str) -> None:
        """Save model checkpoint."""
        torch.save(self.model.state_dict(), path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str) -> None:
        """Load model checkpoint."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        logger.info(f"Model loaded from {path}")


if __name__ == "__main__":
    # Test with synthetic data
    import sys
    from pathlib import Path
    
    # Add parent to path
    sys.path.insert(0, str(Path(__file__).parent))
    from flow_preprocessor import FlowPreprocessor
    
    logger.info("Testing NetworkAutoencoder...")
    
    # Generate synthetic data
    preprocessor = FlowPreprocessor(window_size=5)
    flows_df, labels = preprocessor.generate_synthetic_flows(n_samples=500, anomaly_rate=0.1)
    X = preprocessor.fit_transform(flows_df)
    X_seq, _ = preprocessor.create_sequences(X, labels)
    
    # Split train/val
    split = int(0.8 * len(X_seq))
    X_train, X_val = X_seq[:split], X_seq[split:]
    
    print(f"Data shapes - Train: {X_train.shape}, Val: {X_val.shape}")
    
    # Train autoencoder
    ae = NetworkAutoencoder(
        input_dim=X_train.shape[2],
        seq_length=X_train.shape[1],
        latent_dim=8,
        batch_size=16
    )
    
    history = ae.fit(
        X_train,
        X_val,
        epochs=20,
        early_stopping_patience=5,
        verbose=True
    )
    
    # Test anomaly detection
    scores, preds = ae.predict_anomalies(X_val, percentile=90)
    print(f"\nAnomalies detected: {preds.sum()} / {len(preds)}")
    print(f"Score range: [{scores.min():.4f}, {scores.max():.4f}]")
    
    logger.info("✓ NetworkAutoencoder test passed!")

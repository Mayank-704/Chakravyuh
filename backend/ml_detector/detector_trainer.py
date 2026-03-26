"""
DetectorTrainer: Complete training loop for anomaly detector.
Handles batch loading, early stopping, checkpoint saving on normal traffic only.
"""

import numpy as np
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Optional
import pickle

from .flow_preprocessor import FlowPreprocessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectorTrainer:
    """
    Complete training pipeline for network anomaly detector.
    
    Workflow:
    1. Load/generate normal traffic data
    2. Preprocess: parse PCAP/CSV, normalize, create sequences
    3. Train autoencoder on normal traffic only
    4. Save model and preprocessor
    5. Evaluate reconstruction error thresholds
    """
    
    def __init__(
        self,
        checkpoint_dir: str = './checkpoints',
        window_size: int = 5,
        latent_dim: int = 16,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        device: str = None
    ):
        """
        Initialize trainer.
        
        Args:
            checkpoint_dir: Directory to save models and preprocessor
            window_size: Flow sequence window size
            latent_dim: Autoencoder latent dimension
            batch_size: Training batch size
            learning_rate: Optimizer learning rate
            device: 'cuda' or 'cpu' (default: auto-detect)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect device if not specified
        if device is None:
            try:
                import torch
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except:
                device = 'cpu'
        
        self.window_size = window_size
        self.latent_dim = latent_dim
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.device = device
        
        self.preprocessor: Optional[FlowPreprocessor] = None
        self.autoencoder: Optional[NetworkAutoencoder] = None
        self.training_metadata = {}
        
        logger.info(f"DetectorTrainer initialized | Device: {device}")
    
    def load_training_data(
        self,
        data_source: str = 'synthetic',
        pcap_path: str = None,
        csv_path: str = None,
        normal_samples: int = 1000,
        test_split: float = 0.2,
        val_split: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Load or generate training data (normal traffic only).
        
        Args:
            data_source: 'synthetic', 'pcap', or 'csv'
            pcap_path: Path to PCAP file (if using pcap)
            csv_path: Path to CSV file (if using csv)
            normal_samples: Number of normal samples to generate/load
            test_split: Test set fraction
            val_split: Validation set fraction
            
        Returns:
            (X_train, X_val, X_test) - sequences for train/val/test
        """
        logger.info(f"Loading training data from: {data_source}")
        
        # Initialize preprocessor
        self.preprocessor = FlowPreprocessor(window_size=self.window_size)
        
        # Load flows
        if data_source == 'synthetic':
            flows_df, labels = self.preprocessor.generate_synthetic_flows(
                n_samples=normal_samples,
                anomaly_rate=0.0  # Normal traffic only!
            )
        elif data_source == 'pcap':
            if not pcap_path:
                raise ValueError("pcap_path required for pcap data source")
            flows_df = self.preprocessor.parse_pcap(pcap_path)
            labels = np.zeros(len(flows_df))  # Assume all normal
        elif data_source == 'csv':
            if not csv_path:
                raise ValueError("csv_path required for csv data source")
            flows_df = self.preprocessor.load_csv(csv_path)
            labels = np.zeros(len(flows_df))  # Assume all normal
        else:
            raise ValueError(f"Unknown data source: {data_source}")
        
        logger.info(f"Loaded {len(flows_df)} normal flows")
        
        # Preprocess: fit and transform
        X = self.preprocessor.fit_transform(flows_df)
        logger.info(f"Transformed to feature matrix: {X.shape}")
        
        # Create sequences
        X_seq, y_seq = self.preprocessor.create_sequences(X, labels)
        logger.info(f"Created sequences: {X_seq.shape}")
        
        # Split into train/val/test
        n_samples = len(X_seq)
        n_test = int(test_split * n_samples)
        n_val = int(val_split * (n_samples - n_test))
        
        indices = np.random.permutation(n_samples)
        idx_train = indices[:(n_samples - n_test - n_val)]
        idx_val = indices[(n_samples - n_test - n_val):(n_samples - n_test)]
        idx_test = indices[(n_samples - n_test):]
        
        X_train = X_seq[idx_train]
        X_val = X_seq[idx_val]
        X_test = X_seq[idx_test]
        
        logger.info(
            f"Data split - Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}"
        )
        
        self.training_metadata['n_features'] = X.shape[1]
        self.training_metadata['data_source'] = data_source
        self.training_metadata['n_normal_flows'] = len(flows_df)
        self.training_metadata['window_size'] = self.window_size
        self.training_metadata['latent_dim'] = self.latent_dim
        
        return X_train, X_val, X_test
    
    def train(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        epochs: int = 50,
        early_stopping_patience: int = 10,
        verbose: bool = True
    ) -> Dict:
        """
        Train autoencoder on normal traffic.
        
        Args:
            X_train: Training sequences
            X_val: Validation sequences
            epochs: Number of epochs
            early_stopping_patience: Early stopping patience
            verbose: Print progress
            
        Returns:
            Training history
        """
        logger.info("Initializing autoencoder...")
        
        # Lazy import to avoid torch DLL issues on Windows
        from .network_autoencoder import NetworkAutoencoder
        
        self.autoencoder = NetworkAutoencoder(
            input_dim=X_train.shape[2],
            seq_length=X_train.shape[1],
            latent_dim=self.latent_dim,
            device=self.device,
            learning_rate=self.learning_rate,
            batch_size=self.batch_size
        )
        
        logger.info("Starting training...")
        history = self.autoencoder.fit(
            X_train,
            X_val,
            epochs=epochs,
            early_stopping_patience=early_stopping_patience,
            verbose=verbose
        )
        
        self.training_metadata['epochs_trained'] = len(history['epoch'])
        self.training_metadata['final_train_loss'] = history['train_loss'][-1]
        if history['val_loss']:
            self.training_metadata['final_val_loss'] = history['val_loss'][-1]
        
        return history
    
    def evaluate_thresholds(
        self,
        X_val: np.ndarray,
        percentiles: list = [90, 95, 99]
    ) -> Dict[str, float]:
        """
        Evaluate anomaly detection thresholds on validation data.
        
        Args:
            X_val: Validation sequences
            percentiles: Percentiles to test
            
        Returns:
            Dictionary of thresholds
        """
        logger.info("Evaluating anomaly thresholds...")
        
        scores, _ = self.autoencoder.predict_anomalies(
            X_val,
            threshold=0,  # Get all scores
            percentile=100  # No filtering
        )
        
        thresholds = {}
        for p in percentiles:
            threshold = np.percentile(scores, p)
            thresholds[f'p{p}'] = float(threshold)
            logger.info(f"  Percentile {p}: {threshold:.4f}")
        
        self.training_metadata['thresholds'] = thresholds
        
        return thresholds
    
    def save_checkpoint(self, name: str = 'detector') -> None:
        """
        Save model, preprocessor, and metadata.
        
        Args:
            name: Checkpoint name prefix
        """
        if not self.autoencoder or not self.preprocessor:
            raise ValueError("Must train before saving checkpoint")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = self.checkpoint_dir / f"{name}_{timestamp}"
        checkpoint_path.mkdir(exist_ok=True)
        
        # Save model
        model_path = checkpoint_path / "model.pt"
        self.autoencoder.save_model(str(model_path))
        
        # Save preprocessor
        preprocessor_path = checkpoint_path / "preprocessor.pkl"
        with open(preprocessor_path, 'wb') as f:
            pickle.dump(self.preprocessor, f)
        
        # Save metadata
        metadata_path = checkpoint_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.training_metadata, f, indent=2, default=str)
        
        logger.info(f"Checkpoint saved to: {checkpoint_path}")
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: str) -> None:
        """Load model and preprocessor from checkpoint."""
        checkpoint_path = Path(checkpoint_path)
        
        # Load preprocessor
        preprocessor_path = checkpoint_path / "preprocessor.pkl"
        with open(preprocessor_path, 'rb') as f:
            self.preprocessor = pickle.load(f)
        
        # Load metadata
        metadata_path = checkpoint_path / "metadata.json"
        with open(metadata_path, 'r') as f:
            self.training_metadata = json.load(f)
        
        # Initialize and load model
        # Lazy import to avoid torch DLL issues on Windows
        from .network_autoencoder import NetworkAutoencoder
        
        n_features = self.training_metadata['n_features']
        latent_dim = self.training_metadata.get('latent_dim', self.latent_dim)
        self.autoencoder = NetworkAutoencoder(
            input_dim=n_features,
            seq_length=self.window_size,
            latent_dim=latent_dim,
            device=self.device,
            learning_rate=self.learning_rate,
            batch_size=self.batch_size
        )
        
        model_path = checkpoint_path / "model.pt"
        self.autoencoder.load_model(str(model_path))
        
        logger.info(f"Checkpoint loaded from: {checkpoint_path}")
    
    def run_full_pipeline(
        self,
        data_source: str = 'synthetic',
        normal_samples: int = 1000,
        epochs: int = 50,
        checkpoint_name: str = 'detector'
    ) -> Path:
        """
        Run complete pipeline: data -> preprocess -> train -> save.
        
        Args:
            data_source: 'synthetic', 'pcap', or 'csv'
            normal_samples: Number of normal training samples
            epochs: Training epochs
            checkpoint_name: Name for saved checkpoint
            
        Returns:
            Path to saved checkpoint
        """
        logger.info("=" * 60)
        logger.info("RUNNING FULL DETECTOR TRAINING PIPELINE")
        logger.info("=" * 60)
        
        # Step 1: Load data
        X_train, X_val, X_test = self.load_training_data(
            data_source=data_source,
            normal_samples=normal_samples
        )
        
        # Step 2: Train
        history = self.train(X_train, X_val, epochs=epochs)
        
        # Step 3: Evaluate thresholds
        thresholds = self.evaluate_thresholds(X_val)
        
        # Step 4: Save
        checkpoint_path = self.save_checkpoint(checkpoint_name)
        
        logger.info("=" * 60)
        logger.info(f"Pipeline complete! Checkpoint: {checkpoint_path}")
        logger.info("=" * 60)
        
        return checkpoint_path


if __name__ == "__main__":
    # Full training pipeline test
    logger.info("Testing DetectorTrainer pipeline...")
    
    trainer = DetectorTrainer(
        checkpoint_dir='./phase1_checkpoints',
        window_size=5,
        latent_dim=8,
        batch_size=16,
        learning_rate=0.001
    )
    
    checkpoint_path = trainer.run_full_pipeline(
        data_source='synthetic',
        normal_samples=500,
        epochs=20,
        checkpoint_name='detector_v1'
    )
    
    logger.info(f"\n✓ Training pipeline test passed!")
    logger.info(f"Checkpoint saved at: {checkpoint_path}")

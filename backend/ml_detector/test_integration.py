"""
Phase 1 Integration Test: ML Detector Foundation
Tests complete pipeline: preprocessing -> autoencoder -> trainer -> detector

Run from BACKEND ML+FED directory:
    pytest phase1_ml_detector/test_integration.py -v
"""

import sys
import pytest
import numpy as np
import logging
from pathlib import Path

# Fix 1: make phase1_ml_detector importable when running via pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix 2: use relative-style absolute imports (works from any working directory)
from phase1_ml_detector.flow_preprocessor import FlowPreprocessor
from phase1_ml_detector.network_autoencoder import NetworkAutoencoder
from phase1_ml_detector.detector_trainer import DetectorTrainer
from phase1_ml_detector.threat_detector import ThreatDetector


# ---------------------------------------------------------------------------
# Fix 3: checkpoint_path must be a pytest fixture, not a function parameter
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def checkpoint_path(tmp_path_factory):
    """
    Train a detector and save a checkpoint.
    Shared across all tests in this module via scope="module".
    """
    tmp = tmp_path_factory.mktemp("checkpoints")

    trainer = DetectorTrainer(
        checkpoint_dir=str(tmp),
        window_size=5,
        latent_dim=8,
        batch_size=16,
        learning_rate=0.001,
        device='cpu'
    )

    X_train, X_val, _ = trainer.load_training_data(
        data_source='synthetic',
        normal_samples=300,
        test_split=0.15,
        val_split=0.15
    )

    trainer.train(X_train, X_val, epochs=10, early_stopping_patience=5, verbose=False)
    trainer.evaluate_thresholds(X_val, percentiles=[90, 95, 99])
    path = trainer.save_checkpoint('test_detector')
    return path


# ===========================================================================
# TEST 1 — FlowPreprocessor
# ===========================================================================
def test_flow_preprocessor():
    """Test FlowPreprocessor module."""
    logger.info("TEST 1: FlowPreprocessor")

    preprocessor = FlowPreprocessor(window_size=5, test_mode=True)

    flows_df, labels = preprocessor.generate_synthetic_flows(
        n_samples=200, anomaly_rate=0.15
    )
    assert len(flows_df) == 200, "Flow count mismatch"
    assert len(labels) == 200, "Label count mismatch"
    logger.info(f"Generated {len(flows_df)} flows")

    X = preprocessor.fit_transform(flows_df)
    assert X.shape[0] == 200, "Sample count mismatch"
    assert X.shape[1] > 0, "No features extracted"
    logger.info(f"Transformed shape: {X.shape}")

    X_seq, y_seq = preprocessor.create_sequences(X, labels)
    assert len(X_seq) == len(y_seq), "Sequence/label count mismatch"
    assert X_seq.shape[1] == preprocessor.window_size, "Window size mismatch"
    logger.info(f"Created {len(X_seq)} sequences of size {preprocessor.window_size}")

    feature_names = preprocessor.get_feature_names()
    assert len(feature_names) > 0, "No feature names returned"
    logger.info(f"Features: {feature_names}")


# ===========================================================================
# TEST 2 — NetworkAutoencoder
# ===========================================================================
def test_network_autoencoder():
    """Test NetworkAutoencoder training and anomaly scoring."""
    logger.info("TEST 2: NetworkAutoencoder Training")

    preprocessor = FlowPreprocessor(window_size=5)
    flows_df, labels = preprocessor.generate_synthetic_flows(
        n_samples=200, anomaly_rate=0.1
    )
    X = preprocessor.fit_transform(flows_df)
    X_seq, _ = preprocessor.create_sequences(X, labels)

    split = int(0.8 * len(X_seq))
    X_train, X_val = X_seq[:split], X_seq[split:]
    logger.info(f"Train: {X_train.shape}, Val: {X_val.shape}")

    ae = NetworkAutoencoder(
        input_dim=X_train.shape[2],
        seq_length=X_train.shape[1],
        latent_dim=8,
        batch_size=16,
        device='cpu'
    )
    logger.info("Initialized NetworkAutoencoder (latent_dim=8)")

    history = ae.fit(
        X_train, X_val, epochs=15,
        early_stopping_patience=5, verbose=False
    )
    assert 'train_loss' in history, "Training history missing train_loss"
    assert len(history['train_loss']) > 0, "No training losses recorded"
    logger.info(f"Trained for {len(history['epoch'])} epochs | "
                f"final loss: {history['train_loss'][-1]:.4f}")

    scores, preds = ae.predict_anomalies(X_val, percentile=90)
    assert len(scores) == len(X_val), "Score count mismatch"
    assert len(preds) == len(X_val), "Prediction count mismatch"
    logger.info(f"Detected {preds.sum()} anomalies / {len(X_val)} samples | "
                f"score range: [{scores.min():.4f}, {scores.max():.4f}]")


# ===========================================================================
# TEST 3 — DetectorTrainer
# ===========================================================================
def test_detector_trainer(tmp_path):
    """Test DetectorTrainer full pipeline."""
    logger.info("TEST 3: DetectorTrainer Pipeline")

    trainer = DetectorTrainer(
        checkpoint_dir=str(tmp_path),
        window_size=5,
        latent_dim=8,
        batch_size=16,
        learning_rate=0.001,
        device='cpu'
    )
    logger.info("Initialized DetectorTrainer")

    X_train, X_val, X_test = trainer.load_training_data(
        data_source='synthetic',
        normal_samples=300,
        test_split=0.15,
        val_split=0.15
    )
    logger.info(f"Data — Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    history = trainer.train(
        X_train, X_val, epochs=15,
        early_stopping_patience=5, verbose=False
    )
    assert len(history['epoch']) > 0, "No training epochs recorded"
    logger.info(f"Training completed ({len(history['epoch'])} epochs)")

    thresholds = trainer.evaluate_thresholds(X_val, percentiles=[90, 95, 99])
    assert len(thresholds) > 0, "No thresholds calculated"
    logger.info(f"Thresholds: {thresholds}")

    saved_path = trainer.save_checkpoint('test_detector')
    assert saved_path.exists(), f"Checkpoint not found at {saved_path}"
    logger.info(f"Checkpoint saved: {saved_path}")


# ===========================================================================
# TEST 4 — ThreatDetector  (uses the module-scoped fixture)
# ===========================================================================
def test_threat_detector(checkpoint_path):
    """Test ThreatDetector live inference."""
    logger.info("TEST 4: ThreatDetector Live Inference")

    detector = ThreatDetector(str(checkpoint_path), threshold_percentile='p95')
    logger.info(f"Loaded detector | threshold: {detector.threshold:.4f}")

    preprocessor = FlowPreprocessor()
    flows_df, _ = preprocessor.generate_synthetic_flows(
        n_samples=150, anomaly_rate=0.2
    )
    logger.info(f"Generated {len(flows_df)} test flows")

    alerts = detector.process_flows_batch(flows_df.to_dict('records'))
    logger.info(f"Detected {len(alerts)} anomalies")

    stats = detector.get_stats()
    assert 'flows_processed' in stats
    assert 'alerts_emitted' in stats
    logger.info(f"Flows processed: {stats['flows_processed']} | "
                f"Alerts: {stats['alerts_emitted']}")

    recent = detector.get_alerts(limit=3)
    for alert in recent:
        logger.info(f"Alert — {alert['flow_id']}: "
                    f"score={alert['anomaly_score']:.4f}, "
                    f"severity={alert['severity']}")


# ===========================================================================
# TEST 5 — End-to-end (calls all above in sequence)
# ===========================================================================
def test_end_to_end(checkpoint_path):
    """Full end-to-end integration test."""
    logger.info("CHAKRAVYUH PHASE 1 — END-TO-END INTEGRATION TEST")

    # Preprocessor
    preprocessor = FlowPreprocessor(window_size=5)
    flows_df, labels = preprocessor.generate_synthetic_flows(
        n_samples=200, anomaly_rate=0.1
    )
    X = preprocessor.fit_transform(flows_df)
    X_seq, _ = preprocessor.create_sequences(X, labels)
    assert len(X_seq) > 0, "No sequences generated"

    # Autoencoder
    split = int(0.8 * len(X_seq))
    ae = NetworkAutoencoder(
        input_dim=X_seq.shape[2],
        seq_length=X_seq.shape[1],
        latent_dim=8, batch_size=16, device='cpu'
    )
    history = ae.fit(X_seq[:split], X_seq[split:], epochs=5, verbose=False)
    assert len(history['train_loss']) > 0

    # Detector
    detector = ThreatDetector(str(checkpoint_path), threshold_percentile='p95')
    alerts = detector.process_flows_batch(flows_df.head(50).to_dict('records'))
    stats = detector.get_stats()
    assert stats['flows_processed'] > 0

    logger.info("ALL PHASE 1 TESTS PASSED")


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
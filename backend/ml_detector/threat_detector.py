"""
ThreatDetector: Live inference engine for network anomaly detection.
Loads checkpoint, detects anomalies in real-time traffic, emits alerts.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import json
import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import threading
from collections import deque
import queue
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertEvent:
    """Represents a security alert event."""
    
    def __init__(
        self,
        flow_id: str,
        anomaly_score: float,
        threshold: float,
        severity: str = 'MEDIUM',
        flows_window: List[Dict] = None
    ):
        """
        Initialize alert event.
        
        Args:
            flow_id: Identifier for the anomalous flow
            anomaly_score: Reconstruction error score
            threshold: Detection threshold used
            severity: Alert severity (LOW/MEDIUM/HIGH/CRITICAL)
            flows_window: Recent flows leading to alert
        """
        self.flow_id = flow_id
        self.anomaly_score = anomaly_score
        self.threshold = threshold
        self.severity = severity
        self.timestamp = datetime.utcnow().isoformat()
        self.flows_window = flows_window or []
        self.acknowledged = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'flow_id': self.flow_id,
            'anomaly_score': float(self.anomaly_score),
            'threshold': float(self.threshold),
            'severity': self.severity,
            'timestamp': self.timestamp,
            'n_flows_in_window': len(self.flows_window),
            'acknowledged': self.acknowledged
        }
    
    def __repr__(self) -> str:
        return (
            f"AlertEvent(flow_id={self.flow_id}, "
            f"score={self.anomaly_score:.4f}, "
            f"severity={self.severity}, "
            f"timestamp={self.timestamp})"
        )


class ThreatDetector:
    """
    Real-time threat detection engine.
    
    Workflow:
    1. Load pre-trained model checkpoint
    2. Accept live flows from network monitor
    3. Create sliding windows and detect anomalies
    4. Emit AlertEvent when threshold exceeded
    5. Track flow history and patterns
    """
    
    def __init__(
        self,
        checkpoint_path: str,
        threshold_percentile: str = 'p95',
        alert_queue: Optional[queue.Queue] = None,
        history_size: int = 1000,
        api_url: str = "http://localhost:8000/api/v1/alert"
    ):
        """
        Initialize threat detector.
        
        Args:
            checkpoint_path: Path to trained model checkpoint
            threshold_percentile: Which percentile threshold to use (p90/p95/p99)
            alert_queue: Optional queue for alert events (for async processing)
            history_size: Size of flow history buffer
            api_url: The URL for the API to send alerts to.
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.threshold_percentile = threshold_percentile
        self.alert_queue = alert_queue if alert_queue else queue.Queue()
        self.history_size = history_size
        self.api_url = api_url
        
        self.preprocessor = None
        self.autoencoder = None
        self.threshold = None
        self.metadata = {}
        
        # Flow history and detection state
        self.flow_history = deque(maxlen=history_size)
        self.alerts = deque(maxlen=100)
        self.lock = threading.RLock()
        
        # Load checkpoint
        self._load_checkpoint()
        
        logger.info(f"ThreatDetector initialized | Threshold: {self.threshold:.4f}")
    
    def _load_checkpoint(self) -> None:
        """Load model, preprocessor, and metadata from checkpoint."""
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {self.checkpoint_path}")
        
        # Load preprocessor
        preprocessor_path = self.checkpoint_path / "preprocessor.pkl"
        with open(preprocessor_path, 'rb') as f:
            self.preprocessor = pickle.load(f)
        
        # Load metadata
        metadata_path = self.checkpoint_path / "metadata.json"
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        # Extract threshold
        thresholds = self.metadata.get('thresholds', {})
        if self.threshold_percentile not in thresholds:
            logger.warning(
                f"Percentile {self.threshold_percentile} not found. "
                f"Available: {list(thresholds.keys())}"
            )
            self.threshold = thresholds[list(thresholds.keys())[0]]
        else:
            self.threshold = thresholds[self.threshold_percentile]
        
        # Initialize autoencoder
        from .network_autoencoder import NetworkAutoencoder
        
        n_features = self.metadata['n_features']
        window_size = self.preprocessor.window_size
        
        self.autoencoder = NetworkAutoencoder(
            input_dim=n_features,
            seq_length=window_size,
            latent_dim=self.metadata.get('latent_dim', 16)
        )
        
        # Load model weights
        model_path = self.checkpoint_path / "model.pt"
        self.autoencoder.load_model(str(model_path))
        
        logger.info(f"Checkpoint loaded from: {self.checkpoint_path}")
    
    def process_flow(self, flow_dict: Dict) -> Optional[AlertEvent]:
        """
        Process a single flow for anomaly detection.
        
        Required flow fields:
        - src_ip, dst_ip, src_port, dst_port, protocol
        - packet_count, total_bytes, duration
        - inter_arrival_time, payload_size_variance, flag_pattern, window_size
        
        Args:
            flow_dict: Dictionary with flow features
            
        Returns:
            AlertEvent if anomalous, None otherwise
        """
        with self.lock:
            # Add to history
            self.flow_history.append(flow_dict)
            
            # Check if we have enough flows for a window
            if len(self.flow_history) < self.preprocessor.window_size:
                return None
            
            # Create a DataFrame from recent flows
            recent_flows = list(self.flow_history)[-self.preprocessor.window_size:]
            flows_df = pd.DataFrame(recent_flows)
            
            # Preprocess
            try:
                X = self.preprocessor.transform(flows_df)
            except Exception as e:
                logger.warning(f"Preprocessing error: {e}")
                return None
            
            # Create sequence
            X_seq, _ = self.preprocessor.create_sequences(X)
            
            if len(X_seq) == 0:
                return None
            
            # Latest sequence
            X_latest = X_seq[-1:]
            
            # Get anomaly score
            scores, preds = self.autoencoder.predict_anomalies(
                X_latest,
                threshold=self.threshold,
                percentile=100
            )
            
            score = scores[0]
            is_anomalous = preds[0] == 1
            
            # Determine severity
            if not is_anomalous:
                return None
            
            severity = 'CRITICAL' if score > self.threshold * 2 else 'HIGH'
            
            # Create alert
            flow_id = f"{flow_dict.get('src_ip', '?')}-{flow_dict.get('dst_ip', '?')}"
            alert = AlertEvent(
                flow_id=flow_id,
                anomaly_score=score,
                threshold=self.threshold,
                severity=severity,
                flows_window=recent_flows
            )

            # Send alert to API
            try:
                alert_data = alert.to_dict()
                # Add attacker_ip for the trap controller
                alert_data['attacker_ip'] = flow_dict.get('src_ip')
                requests.post(self.api_url, json=alert_data, timeout=5)
                logger.info(f"Sent alert to API: {alert_data}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send alert to API: {e}")

            # Store alert
            self.alerts.append(alert)
            
            # Emit to queue
            self.alert_queue.put(alert)
            
            logger.warning(f"ALERT EMITTED: {alert}")
            
            return alert
    
    def process_flows_batch(
        self,
        flows_list: List[Dict]
    ) -> List[AlertEvent]:
        """
        Process a batch of flows.
        
        Args:
            flows_list: List of flow dictionaries
            
        Returns:
            List of AlertEvents
        """
        alerts = []
        for flow_dict in flows_list:
            alert = self.process_flow(flow_dict)
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def get_stats(self) -> Dict:
        """Get detector statistics."""
        with self.lock:
            return {
                'flows_processed': len(self.flow_history),
                'alerts_emitted': len(self.alerts),
                'threshold': float(self.threshold),
                'threshold_percentile': self.threshold_percentile,
                'recent_alerts': [a.to_dict() for a in list(self.alerts)[-5:]]
            }
    
    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        with self.lock:
            alerts = list(self.alerts)[-limit:]
            return [a.to_dict() for a in alerts]
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge an alert by index."""
        with self.lock:
            if 0 <= alert_id < len(self.alerts):
                self.alerts[alert_id].acknowledged = True
                return True
        return False
    
    def export_alerts(self, output_path: str) -> None:
        """Export all alerts to JSON file."""
        with self.lock:
            alerts_data = [a.to_dict() for a in self.alerts]
        
        with open(output_path, 'w') as f:
            json.dump(alerts_data, f, indent=2)
        
        logger.info(f"Exported {len(alerts_data)} alerts to {output_path}")


class ThreatDetectorAPI:
    """
    REST/WebSocket API wrapper for ThreatDetector.
    Handles async alert streaming and flow processing.
    """
    
    def __init__(self, checkpoint_path: str):
        """Initialize API with detector."""
        self.detector = ThreatDetector(checkpoint_path)
        self.clients = set()
    
    def process_flow(self, flow_dict: Dict) -> Dict:
        """Process flow and return response."""
        alert = self.detector.process_flow(flow_dict)
        
        return {
            'status': 'anomalous' if alert else 'normal',
            'alert': alert.to_dict() if alert else None,
            'stats': self.detector.get_stats()
        }
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display."""
        return {
            'stats': self.detector.get_stats(),
            'recent_alerts': self.detector.get_alerts(limit=20),
            'metadata': self.detector.metadata
        }


if __name__ == "__main__":
    # Test detector - requires checkpoint from trainer
    import sys
    from pathlib import Path
    
    logger.info("Testing ThreatDetector...")
    
    # First, train a model
    from detector_trainer import DetectorTrainer
    
    trainer = DetectorTrainer(checkpoint_dir='./test_checkpoints')
    checkpoint_path = trainer.run_full_pipeline(
        data_source='synthetic',
        normal_samples=300,
        epochs=10,
        checkpoint_name='test_detector'
    )
    
    # Now test detector
    detector = ThreatDetector(str(checkpoint_path))
    
    # Generate test flows
    from flow_preprocessor import FlowPreprocessor
    preprocessor = FlowPreprocessor()
    flows_df, labels = preprocessor.generate_synthetic_flows(n_samples=100, anomaly_rate=0.2)
    
    alerts = detector.process_flows_batch(flows_df.to_dict('records'))
    print(f"\nDetected {len(alerts)} anomalies in {len(flows_df)} flows")
    
    # Show stats
    stats = detector.get_stats()
    print(f"\nDetector stats:")
    print(f"  Flows processed: {stats['flows_processed']}")
    print(f"  Alerts emitted: {stats['alerts_emitted']}")
    print(f"  Threshold: {stats['threshold']:.4f}")
    
    logger.info("✓ ThreatDetector test passed!")

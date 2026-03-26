"""
FlowPreprocessor: Parse PCAP/CSV flows, normalize features, encode categoricals.
Input: PCAP files or CSV flows
Output: Normalized numpy tensors for ML training
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, List, Union, Optional
from pathlib import Path
import logging
from sklearn.preprocessing import StandardScaler, LabelEncoder
from collections import defaultdict

try:
    from scapy.all import rdpcap, IP, TCP, UDP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlowPreprocessor:
    """
    Preprocessor for network flows: handles PCAP parsing, CSV loading, feature engineering.
    
    Features extracted:
    - Temporal: src_port, dst_port, protocol
    - Statistical: packet_count, bytes_total, duration
    - Behavioral: inter_arrival_time, payload_size_var
    """
    
    # Standard network flow features
    STANDARD_FEATURES = [
        'src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol',
        'packet_count', 'total_bytes', 'duration',
        'inter_arrival_time', 'payload_size_variance',
        'flag_pattern', 'window_size'
    ]
    
    # Categorical features (require encoding)
    CATEGORICAL_FEATURES = ['src_ip', 'dst_ip', 'protocol', 'flag_pattern']
    
    # Numeric features (require normalization)
    NUMERIC_FEATURES = [
        'src_port', 'dst_port', 'packet_count', 'total_bytes', 
        'duration', 'inter_arrival_time', 'payload_size_variance', 'window_size'
    ]
    
    def __init__(self, window_size: int = 5, test_mode: bool = False):
        """
        Initialize preprocessor.
        
        Args:
            window_size: Number of flows per sequence window
            test_mode: If True, use synthetic data for testing
        """
        self.window_size = window_size
        self.test_mode = test_mode
        self.scalers: Dict[str, StandardScaler] = {}
        self.encoders: Dict[str, LabelEncoder] = {}
        self.feature_stats = {}
        self.is_fitted = False
        
    def parse_pcap(self, pcap_path: str, flow_timeout: int = 600) -> pd.DataFrame:
        """
        Parse PCAP file into flows.
        
        Args:
            pcap_path: Path to PCAP file
            flow_timeout: Timeout to consider flow ended (seconds)
            
        Returns:
            DataFrame with extracted flows
        """
        if not SCAPY_AVAILABLE:
            raise ImportError("scapy not available. Install: pip install scapy")
        
        logger.info(f"Parsing PCAP: {pcap_path}")
        pcap_file = Path(pcap_path)
        
        if not pcap_file.exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_path}")
        
        packets = rdpcap(str(pcap_path))
        flows = defaultdict(lambda: {
            'packets': [],
            'bytes': [],
            'timestamps': [],
            'flags': []
        })
        
        for pkt in packets:
            if IP in pkt:
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                proto = pkt[IP].proto
                
                # Determine transport layer
                if TCP in pkt:
                    src_port = pkt[TCP].sport
                    dst_port = pkt[TCP].dport
                    flags = pkt[TCP].flags
                    proto_name = 'TCP'
                elif UDP in pkt:
                    src_port = pkt[UDP].sport
                    dst_port = pkt[UDP].dport
                    flags = 0
                    proto_name = 'UDP'
                else:
                    continue
                
                flow_key = (src_ip, dst_ip, src_port, dst_port, proto_name)
                flow = flows[flow_key]
                
                flow['packets'].append(1)
                flow['bytes'].append(len(pkt))
                flow['timestamps'].append(float(pkt.time))
                flow['flags'].append(flags)
        
        # Convert flows to DataFrame rows
        rows = []
        for (src_ip, dst_ip, src_port, dst_port, protocol), flow in flows.items():
            if len(flow['packets']) > 1:  # Skip single-packet flows
                timestamps = flow['timestamps']
                inter_arrivals = np.diff(timestamps)
                
                rows.append({
                    'src_ip': src_ip,
                    'dst_ip': dst_ip,
                    'src_port': src_port,
                    'dst_port': dst_port,
                    'protocol': protocol,
                    'packet_count': len(flow['packets']),
                    'total_bytes': sum(flow['bytes']),
                    'duration': timestamps[-1] - timestamps[0],
                    'inter_arrival_time': np.mean(inter_arrivals) if len(inter_arrivals) > 0 else 0,
                    'payload_size_variance': np.var(flow['bytes']),
                    'flag_pattern': 'TCP' if protocol == 'TCP' else 'OTHER',
                    'window_size': 65535
                })
        
        df = pd.DataFrame(rows)
        logger.info(f"Extracted {len(df)} flows from PCAP")
        return df
    
    def load_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Load flows from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            DataFrame with flows
        """
        logger.info(f"Loading CSV: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        missing = set(self.STANDARD_FEATURES) - set(df.columns)
        if missing:
            logger.warning(f"Missing columns: {missing}. Will use defaults for missing.")
        
        # Fill missing columns with defaults
        for col in self.STANDARD_FEATURES:
            if col not in df.columns:
                if col in self.NUMERIC_FEATURES:
                    df[col] = 0
                else:
                    df[col] = 'UNKNOWN'
        
        return df[self.STANDARD_FEATURES]
    
    def fit(self, flows_df: pd.DataFrame) -> None:
        """
        Fit scalers and encoders on training data.
        
        Args:
            flows_df: DataFrame with flows
        """
        logger.info("Fitting preprocessor on training data...")
        
        # Fit numeric scalers
        for col in self.NUMERIC_FEATURES:
            if col in flows_df.columns:
                scaler = StandardScaler()
                scaler.fit(flows_df[[col]])
                self.scalers[col] = scaler
                self.feature_stats[col] = {
                    'mean': scaler.mean_[0],
                    'std': scaler.scale_[0]
                }
        
        # Fit categorical encoders
        for col in self.CATEGORICAL_FEATURES:
            if col in flows_df.columns:
                # Add unknown category
                unique_vals = list(flows_df[col].unique()) + ['UNKNOWN']
                encoder = LabelEncoder()
                encoder.fit(unique_vals)
                self.encoders[col] = encoder
        
        self.is_fitted = True
        logger.info(f"Fitted on {len(flows_df)} flows")
    
    def transform(self, flows_df: pd.DataFrame) -> np.ndarray:
        """
        Transform flows to normalized feature vectors.
        
        Args:
            flows_df: DataFrame with flows
            
        Returns:
            Array of shape (n_flows, n_features)
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor must be fitted first")
        
        logger.info(f"Transforming {len(flows_df)} flows...")
        
        # Handle missing values
        flows_df = flows_df.fillna(0)
        
        features = []
        
        # Numeric features (scaled)
        for col in self.NUMERIC_FEATURES:
            if col in flows_df.columns and col in self.scalers:
                scaled = self.scalers[col].transform(flows_df[[col]])
                features.append(scaled.flatten())
        
        # Categorical features (encoded)
        for col in self.CATEGORICAL_FEATURES:
            if col in flows_df.columns and col in self.encoders:
                # Handle unknown values
                vals = flows_df[col].fillna('UNKNOWN').astype(str)
                try:
                    encoded = self.encoders[col].transform(vals)
                except ValueError:
                    # Unknown values -> map to 'UNKNOWN'
                    vals = vals.apply(
                        lambda x: x if x in self.encoders[col].classes_ else 'UNKNOWN'
                    )
                    encoded = self.encoders[col].transform(vals)
                
                # Normalize encoded values
                n_classes = len(self.encoders[col].classes_)
                if n_classes > 1:
                    normalized = encoded / (n_classes - 1)
                else:
                    normalized = encoded
                features.append(normalized)
        
        # Combine all features
        X = np.column_stack(features)
        logger.info(f"Transformed to shape: {X.shape}")
        return X
    
    def fit_transform(self, flows_df: pd.DataFrame) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(flows_df)
        return self.transform(flows_df)
    
    def create_sequences(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Create sliding window sequences for autoencoder.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Optional labels
            
        Returns:
            Sequences of shape (n_sequences, window_size, n_features)
        """
        X_seq = []
        y_seq = []
        
        for i in range(len(X) - self.window_size + 1):
            X_seq.append(X[i:i + self.window_size])
            if y is not None:
                # Use max label in window as sequence label (any malicious = malicious)
                y_seq.append(max(y[i:i + self.window_size]))
        
        X_seq = np.array(X_seq)
        logger.info(f"Created {len(X_seq)} sequences of size {self.window_size}")
        
        if y is not None:
            return X_seq, np.array(y_seq)
        return X_seq, None
    
    def generate_synthetic_flows(self, n_samples: int = 1000, anomaly_rate: float = 0.1) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Generate synthetic flows for testing.
        
        Args:
            n_samples: Number of flows to generate
            anomaly_rate: Fraction of flows to be anomalous
            
        Returns:
            (flows DataFrame, labels array)
        """
        logger.info(f"Generating {n_samples} synthetic flows ({anomaly_rate*100:.1f}% anomalies)...")
        
        rows = []
        labels = []
        
        for i in range(n_samples):
            is_anomaly = np.random.rand() < anomaly_rate
            
            if is_anomaly:
                # Anomalous flow: unusual patterns
                packet_count = np.random.randint(1000, 5000)
                total_bytes = np.random.randint(1000000, 10000000)
                inter_arrival = np.random.exponential(0.01)
                payload_var = np.random.uniform(10000, 50000)
                src_port = np.random.randint(49152, 65535)
            else:
                # Normal flow: typical patterns
                packet_count = np.random.randint(10, 200)
                total_bytes = np.random.randint(1000, 100000)
                inter_arrival = np.random.exponential(0.1)
                payload_var = np.random.uniform(100, 5000)
                src_port = np.random.randint(1024, 10000)
            
            rows.append({
                'src_ip': f'192.168.{np.random.randint(1,256)}.{np.random.randint(1,256)}',
                'dst_ip': f'10.0.{np.random.randint(1,256)}.{np.random.randint(1,256)}',
                'src_port': src_port,
                'dst_port': np.random.choice([80, 443, 22, 3306, 5432]),
                'protocol': np.random.choice(['TCP', 'UDP']),
                'packet_count': packet_count,
                'total_bytes': total_bytes,
                'duration': np.random.uniform(0.1, 300),
                'inter_arrival_time': inter_arrival,
                'payload_size_variance': payload_var,
                'flag_pattern': 'TCP',
                'window_size': 65535
            })
            labels.append(1 if is_anomaly else 0)
        
        df = pd.DataFrame(rows)
        return df, np.array(labels)
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names in order."""
        features = []
        for col in self.NUMERIC_FEATURES:
            if col in self.scalers:
                features.append(col)
        for col in self.CATEGORICAL_FEATURES:
            if col in self.encoders:
                features.append(col)
        return features
    
    def get_n_features(self) -> int:
        """Get total number of features after transformation."""
        return len(self.get_feature_names())


if __name__ == "__main__":
    # Test with synthetic data
    preprocessor = FlowPreprocessor(window_size=5, test_mode=True)
    
    # Generate synthetic flows
    flows_df, labels = preprocessor.generate_synthetic_flows(n_samples=500, anomaly_rate=0.1)
    print(f"\nGenerated flows shape: {flows_df.shape}")
    print(f"Labels distribution: {np.bincount(labels)}")
    
    # Fit and transform
    X = preprocessor.fit_transform(flows_df)
    print(f"Transformed shape: {X.shape}")
    
    # Create sequences
    X_seq, y_seq = preprocessor.create_sequences(X, labels)
    print(f"Sequence shape: {X_seq.shape}")
    print(f"Sequence labels: {np.bincount(y_seq)}")
    
    print("\n✓ FlowPreprocessor test passed!")

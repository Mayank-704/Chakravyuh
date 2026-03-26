"""
Phase 1: ML Detector Foundation
Autoencoder-based anomaly detection for network flows
"""

def __getattr__(name):
    """Lazy loading of phase1 modules to handle optional dependencies."""
    if name == 'FlowPreprocessor':
        from .flow_preprocessor import FlowPreprocessor
        return FlowPreprocessor
    elif name == 'NetworkAutoencoder':
        from .network_autoencoder import NetworkAutoencoder
        return NetworkAutoencoder
    elif name == 'DetectorTrainer':
        from .detector_trainer import DetectorTrainer
        return DetectorTrainer
    elif name == 'ThreatDetector':
        from .threat_detector import ThreatDetector
        return ThreatDetector
    elif name == 'AlertEvent':
        from .threat_detector import AlertEvent
        return AlertEvent
    elif name == 'ThreatDetectorAPI':
        from .threat_detector import ThreatDetectorAPI
        return ThreatDetectorAPI
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'FlowPreprocessor',
    'NetworkAutoencoder',
    'DetectorTrainer',
    'ThreatDetector',
    'AlertEvent',
    'ThreatDetectorAPI'
]

__version__ = '1.0.0'

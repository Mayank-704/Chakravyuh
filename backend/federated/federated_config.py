"""
Federated Learning Configuration
Manages training parameters, aggregation strategies, and node settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Supported aggregation strategies."""
    FED_AVG = "fedavg"  # Simple averaging
    FED_PROX = "fedprox"  # Proximal term to prevent divergence
    WEIGHTED_AVG = "weighted_avg"  # Weighted by data volume
    MEDIAN = "median"  # Robust to outliers
    TRIMMED_MEAN = "trimmed_mean"  # Trim extreme values


@dataclass
class FederatedConfig:
    """Configuration for federated learning setup."""
    
    # Training parameters
    num_rounds: int = 5
    """Total number of federated learning rounds."""
    
    num_nodes: int = 3
    """Number of participating nodes."""
    
    local_epochs: int = 2
    """Epochs of local training per round."""
    
    learning_rate: float = 0.01
    """Local learning rate for nodes."""
    
    batch_size: int = 32
    """Local batch size for training."""
    
    # Aggregation parameters
    aggregation_strategy: AggregationStrategy = AggregationStrategy.FED_AVG
    """Strategy for aggregating weight deltas."""
    
    min_nodes_for_round: int = 2
    """Minimum nodes required to complete a round."""
    
    # Privacy & security
    differential_privacy: bool = False
    """Enable differential privacy on weight updates."""
    
    dp_epsilon: float = 1.0
    """Privacy budget (epsilon) for differential privacy."""
    
    dp_delta: float = 0.01
    """Delta parameter for differential privacy."""
    
    clip_weights: bool = True
    """Clip weight updates to prevent outliers."""
    
    weight_clip_norm: float = 1.0
    """L2 norm for weight clipping."""
    
    # Communication
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    """Node configurations: {node_id: {host, port, ...}}"""
    
    server_host: str = "localhost"
    """Aggregation server host."""
    
    server_port: int = 9000
    """Aggregation server port."""
    
    # Checkpointing
    checkpoint_dir: str = "./federated_checkpoints"
    """Directory for saving federated checkpoints."""
    
    save_every_n_rounds: int = 1
    """Save checkpoint every N rounds."""
    
    # Monitoring
    log_frequency: int = 1
    """Log metrics every N rounds."""
    
    verbose: bool = True
    """Enable verbose logging."""
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.num_rounds < 1:
            raise ValueError("num_rounds must be >= 1")
        if self.num_nodes < 1:
            raise ValueError("num_nodes must be >= 1")
        if self.local_epochs < 1:
            raise ValueError("local_epochs must be >= 1")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be > 0")
        if self.dp_epsilon <= 0:
            raise ValueError("dp_epsilon must be > 0")
        
        logger.info(
            f"Federated Config: {self.num_rounds} rounds, "
            f"{self.num_nodes} nodes, {self.local_epochs} local epochs, "
            f"strategy={self.aggregation_strategy.value}"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'num_rounds': self.num_rounds,
            'num_nodes': self.num_nodes,
            'local_epochs': self.local_epochs,
            'learning_rate': self.learning_rate,
            'batch_size': self.batch_size,
            'aggregation_strategy': self.aggregation_strategy.value,
            'min_nodes_for_round': self.min_nodes_for_round,
            'differential_privacy': self.differential_privacy,
            'dp_epsilon': self.dp_epsilon if self.differential_privacy else None,
            'weight_clip_norm': self.weight_clip_norm if self.clip_weights else None,
            'server_host': self.server_host,
            'server_port': self.server_port,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'FederatedConfig':
        """Create config from dictionary."""
        strategy_str = config_dict.pop('aggregation_strategy', 'fedavg')
        config_dict['aggregation_strategy'] = AggregationStrategy(strategy_str)
        return cls(**config_dict)

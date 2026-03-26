from __future__ import annotations

from typing import List, Sequence

import numpy as np


def init_toy_model(dim: int, seed: int | None = None) -> List[np.ndarray]:
    """Toy model = [weights vector, bias scalar]."""
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 0.1, size=(dim,)).astype(np.float32)
    b = np.array([0.0], dtype=np.float32)
    return [w, b]


def copy_params(params: Sequence[np.ndarray]) -> List[np.ndarray]:
    return [p.copy() for p in params]
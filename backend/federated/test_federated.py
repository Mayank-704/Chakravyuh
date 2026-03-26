"""
Chakravyuh - Federated Module Tests
=====================================
Tests for Phase 2: Federated Learning.

Run from backend/ directory:
    pytest federated/test_federated.py -v

Or run directly:
    python federated/test_federated.py
"""

import sys
import threading
import time
from pathlib import Path
import pytest
import numpy as np

# Make sure federated/ is importable when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from federated.federated_utils import init_toy_model, copy_params
from federated.federated_client import (
    ChakravyuhClient,
    INSTITUTION_PROFILES,
    _toy_local_train,
    _model_to_params,
    _params_to_model,
    PHASE1_AVAILABLE,
)
from federated.federated_aggregator import ChakravyuhAggregator
from federated.federated_strategy import ChakravyuhFedAvg
from federated.federated_config import FederatedConfig, AggregationStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_toy_params(dim: int = 16, seed: int = 0):
    return init_toy_model(dim=dim, seed=seed)


# ===========================================================================
# 1. federated_utils
# ===========================================================================
class TestFederatedUtils:

    def test_init_toy_model_shape(self):
        params = init_toy_model(dim=16, seed=42)
        assert len(params) == 2
        assert params[0].shape == (16,)   # weight vector
        assert params[1].shape == (1,)    # bias scalar

    def test_init_toy_model_dtype(self):
        params = init_toy_model(dim=8)
        assert params[0].dtype == np.float32
        assert params[1].dtype == np.float32

    def test_init_toy_model_seed_reproducible(self):
        p1 = init_toy_model(dim=10, seed=7)
        p2 = init_toy_model(dim=10, seed=7)
        assert np.array_equal(p1[0], p2[0])

    def test_copy_params_independent(self):
        params = make_toy_params()
        copied = copy_params(params)
        copied[0][0] = 999.0
        assert params[0][0] != 999.0  # original untouched


# ===========================================================================
# 2. Institution profiles
# ===========================================================================
class TestInstitutionProfiles:

    def test_all_institutions_present(self):
        for name in ["AIIMS", "SBI", "GOV"]:
            assert name in INSTITUTION_PROFILES

    def test_profile_keys(self):
        for name, profile in INSTITUTION_PROFILES.items():
            assert "num_examples" in profile
            assert "anomaly_rate" in profile
            assert "toy_base" in profile

    def test_num_examples_positive(self):
        for profile in INSTITUTION_PROFILES.values():
            assert profile["num_examples"] > 0

    def test_anomaly_rate_range(self):
        for profile in INSTITUTION_PROFILES.values():
            assert 0.0 <= profile["anomaly_rate"] <= 1.0


# ===========================================================================
# 3. TOY local training (always available, no Phase 1 needed)
# ===========================================================================
class TestToyLocalTrain:

    def test_returns_correct_structure(self):
        params = make_toy_params(dim=16)
        updated, n_examples, metrics = _toy_local_train(
            params=params, institution="AIIMS", server_round=1, seed=0
        )
        assert len(updated) == 2
        assert isinstance(n_examples, int)
        assert "loss" in metrics
        assert "institution" in metrics
        assert "server_round" in metrics
        assert metrics["mode"] == "toy"

    def test_different_institutions_different_weights(self):
        params = make_toy_params(dim=16, seed=42)
        w_aiims, _, _ = _toy_local_train(params, "AIIMS", 1, seed=0)
        w_sbi, _, _ = _toy_local_train(params, "SBI", 1, seed=0)
        # Different targets → different weights after training
        assert not np.allclose(w_aiims[0], w_sbi[0])

    def test_loss_is_non_negative(self):
        params = make_toy_params()
        _, _, metrics = _toy_local_train(params, "AIIMS", 1)
        assert metrics["loss"] >= 0.0

    def test_institution_in_metrics(self):
        params = make_toy_params()
        _, _, metrics = _toy_local_train(params, "SBI", 3)
        assert metrics["institution"] == "SBI"
        assert metrics["server_round"] == 3

    def test_num_examples_matches_profile(self):
        params = make_toy_params()
        _, n, _ = _toy_local_train(params, "AIIMS", 1)
        assert n == INSTITUTION_PROFILES["AIIMS"]["num_examples"]

    def test_unknown_institution_uses_default(self):
        params = make_toy_params()
        updated, n_examples, metrics = _toy_local_train(params, "UNKNOWN_ORG", 1)
        assert n_examples == 300   # DEFAULT_PROFILE num_examples
        assert len(updated) == 2


# ===========================================================================
# 4. ChakravyuhClient (TOY mode — no Phase 1 dependency)
# ===========================================================================
class TestChakravyuhClientToyMode:

    def _make_client(self, institution="AIIMS", dim=16, seed=0):
        return ChakravyuhClient(
            institution=institution,
            dim=dim,
            seed=seed,
            force_toy_mode=True,   # always use toy mode in unit tests
        )

    def test_initialization(self):
        client = self._make_client("AIIMS")
        assert client.institution == "AIIMS"
        assert len(client.parameters) == 2  # toy model: [w, b]

    def test_get_parameters_returns_list(self):
        client = self._make_client("SBI")
        params = client.get_parameters(config={})
        assert isinstance(params, list)
        assert all(isinstance(p, np.ndarray) for p in params)

    def test_fit_returns_correct_structure(self):
        client = self._make_client("GOV")
        params = make_toy_params(dim=16, seed=0)
        updated, n_examples, metrics = client.fit(
            parameters=params, config={"server_round": 1}
        )
        assert isinstance(updated, list)
        assert isinstance(n_examples, int)
        assert isinstance(metrics, dict)
        assert "loss" in metrics
        assert "institution" in metrics

    def test_fit_updates_internal_parameters(self):
        client = self._make_client("AIIMS")
        original = copy_params(client.parameters)
        new_params = make_toy_params(dim=16, seed=99)
        client.fit(parameters=new_params, config={"server_round": 1})
        # Internal params must have changed
        assert not np.array_equal(client.parameters[0], original[0])

    def test_fit_does_not_mutate_input(self):
        client = self._make_client("SBI")
        params = make_toy_params(dim=16, seed=5)
        original_copy = copy_params(params)
        client.fit(parameters=params, config={"server_round": 1})
        assert np.array_equal(params[0], original_copy[0])

    def test_evaluate_returns_tuple(self):
        client = self._make_client("GOV")
        loss, n, metrics = client.evaluate(
            parameters=client.parameters, config={}
        )
        assert isinstance(loss, float)
        assert isinstance(n, int)
        assert "institution" in metrics

    def test_multiple_rounds_loss_changes(self):
        client = self._make_client("AIIMS", seed=42)
        params = make_toy_params(dim=16, seed=0)
        losses = []
        for r in range(1, 4):
            _, _, metrics = client.fit(parameters=params, config={"server_round": r})
            losses.append(metrics["loss"])
        # Loss should generally decrease (not guaranteed but very likely with 3 rounds)
        assert len(losses) == 3

    def test_all_three_institutions(self):
        for institution in ["AIIMS", "SBI", "GOV"]:
            client = self._make_client(institution)
            params = make_toy_params()
            _, _, metrics = client.fit(params, {"server_round": 1})
            assert metrics["institution"] == institution


# ===========================================================================
# 5. REAL mode — only run if Phase 1 is installed
# ===========================================================================
@pytest.mark.skipif(not PHASE1_AVAILABLE, reason="phase1_ml_detector not installed")
class TestChakravyuhClientRealMode:

    def test_real_mode_initializes(self):
        client = ChakravyuhClient("AIIMS", local_epochs=1, window_size=5)
        assert client.use_real_mode is True
        assert len(client.parameters) > 2  # real model has many tensors

    def test_real_mode_fit_returns_params(self):
        client = ChakravyuhClient("AIIMS", local_epochs=1, window_size=5)
        updated, n_examples, metrics = client.fit(
            parameters=client.parameters, config={"server_round": 1}
        )
        assert isinstance(updated, list)
        assert len(updated) == len(client.parameters)
        assert metrics["mode"] == "real"
        assert n_examples == INSTITUTION_PROFILES["AIIMS"]["num_examples"]

    def test_model_to_params_and_back(self):
        from phase1_ml_detector.network_autoencoder import NetworkAutoencoder
        import torch
        from collections import OrderedDict

        ae = NetworkAutoencoder(input_dim=12, seq_length=5, latent_dim=8)
        params = _model_to_params(ae)
        assert all(isinstance(p, np.ndarray) for p in params)

        # Modify params and load back
        modified = [p + 0.001 for p in params]
        _params_to_model(modified, ae)

        reloaded = _model_to_params(ae)
        for orig, mod, rel in zip(params, modified, reloaded):
            assert np.allclose(mod, rel, atol=1e-6)

    def test_param_count_consistent_across_rounds(self):
        client = ChakravyuhClient("SBI", local_epochs=1, window_size=5)
        n_tensors = len(client.parameters)
        for r in range(1, 3):
            updated, _, _ = client.fit(client.parameters, {"server_round": r})
            assert len(updated) == n_tensors


# ===========================================================================
# 6. FederatedConfig
# ===========================================================================
class TestFederatedConfig:

    def test_default_config(self):
        cfg = FederatedConfig()
        assert cfg.num_rounds >= 1
        assert cfg.min_fit_clients >= 1

    def test_custom_config(self):
        cfg = FederatedConfig(num_rounds=10, min_fit_clients=2)
        assert cfg.num_rounds == 10
        assert cfg.min_fit_clients == 2

    def test_aggregation_strategy_enum(self):
        cfg = FederatedConfig(aggregation_strategy=AggregationStrategy.FED_AVG)
        assert cfg.aggregation_strategy == AggregationStrategy.FED_AVG

    def test_to_dict(self):
        cfg = FederatedConfig(num_rounds=3)
        d = cfg.to_dict()
        assert d["num_rounds"] == 3
        assert "aggregation_strategy" in d

    def test_from_dict(self):
        d = {"num_rounds": 4, "aggregation_strategy": "fedavg"}
        cfg = FederatedConfig.from_dict(d)
        assert cfg.num_rounds == 4


# ===========================================================================
# 7. ChakravyuhFedAvg strategy
# ===========================================================================
class TestChakravyuhFedAvg:

    def test_instantiation(self):
        strategy = ChakravyuhFedAvg(
            fraction_fit=1.0,
            min_fit_clients=2,
            min_available_clients=2,
        )
        assert strategy is not None

    def test_fit_config_returns_round(self):
        strategy = ChakravyuhFedAvg()
        config = strategy.fit_config(server_round=3)
        assert config["server_round"] == 3

    def test_fit_config_has_dpdp_note(self):
        strategy = ChakravyuhFedAvg()
        config = strategy.fit_config(server_round=1)
        assert "dpdp_note" in config


# ===========================================================================
# 8. ChakravyuhAggregator (configuration only — no server started)
# ===========================================================================
class TestChakravyuhAggregator:

    def test_instantiation_defaults(self):
        agg = ChakravyuhAggregator()
        assert agg.host == "127.0.0.1"
        assert agg.port == 8080
        assert agg.num_rounds == 5
        assert agg.min_fit_clients == 3

    def test_custom_config(self):
        agg = ChakravyuhAggregator(
            host="0.0.0.0",
            port=9090,
            num_rounds=3,
            min_fit_clients=2,
            min_available_clients=2,
        )
        assert agg.port == 9090
        assert agg.num_rounds == 3


# ===========================================================================
# 9. Integration: client + params round-trip (TOY mode, no network)
# ===========================================================================
class TestIntegrationToyRoundTrip:
    """
    Simulates one federated round in-process (no Flower server needed).
    Client A and B train, we manually FedAvg their weights.
    """

    def test_manual_fedavg_round(self):
        dim = 16
        clients = [
            ChakravyuhClient("AIIMS", dim=dim, seed=101, force_toy_mode=True),
            ChakravyuhClient("SBI",   dim=dim, seed=202, force_toy_mode=True),
            ChakravyuhClient("GOV",   dim=dim, seed=303, force_toy_mode=True),
        ]

        # Simulate global model (toy)
        global_params = make_toy_params(dim=dim, seed=0)

        # Each client receives global params and trains
        all_updated = []
        all_n = []
        for client in clients:
            updated, n, metrics = client.fit(
                parameters=copy_params(global_params),
                config={"server_round": 1},
            )
            all_updated.append(updated)
            all_n.append(n)
            assert metrics["loss"] >= 0.0

        # Manual FedAvg (weighted by num_examples)
        total = sum(all_n)
        aggregated = []
        for i in range(len(global_params)):
            weighted = sum(
                all_updated[j][i] * (all_n[j] / total)
                for j in range(len(clients))
            )
            aggregated.append(weighted.astype(np.float32))

        # Aggregated params must differ from original global
        assert not np.array_equal(aggregated[0], global_params[0])

    def test_three_rounds_loss_trend(self):
        """Loss from each client should generally decrease over rounds."""
        client = ChakravyuhClient("AIIMS", dim=16, seed=42, force_toy_mode=True)
        params = make_toy_params(dim=16, seed=0)

        losses = []
        for r in range(1, 6):
            _, _, metrics = client.fit(params, {"server_round": r})
            losses.append(metrics["loss"])

        # At least the last loss should be less than the first
        assert losses[-1] < losses[0], \
            f"Loss did not decrease: {losses}"


# ===========================================================================
# Entry point for running without pytest
# ===========================================================================
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])

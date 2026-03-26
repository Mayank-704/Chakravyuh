"""Quick test to verify checkpoint fix works."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from phase1_ml_detector.detector_trainer import DetectorTrainer
from phase1_ml_detector.threat_detector import ThreatDetector

def test_checkpoint_fix():
    print("\n" + "="*60)
    print("TEST: Checkpoint with Thresholds")
    print("="*60)
    
    # Create temp directory for checkpoint
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        print("\n1. Building and training detector...")
        trainer = DetectorTrainer(
            checkpoint_dir=str(tmp_path),
            window_size=5,
            latent_dim=8,
            batch_size=16,
            learning_rate=0.001,
            device='cpu'
        )
        
        print("2. Loading training data...")
        X_train, X_val, _ = trainer.load_training_data(
            data_source='synthetic',
            normal_samples=300,
            test_split=0.15,
            val_split=0.15
        )
        print(f"   ✓ Train: {X_train.shape}, Val: {X_val.shape}")
        
        print("3. Training autoencoder...")
        trainer.train(X_train, X_val, epochs=10, early_stopping_patience=5, verbose=False)
        print("   ✓ Training complete")
        
        print("4. Evaluating thresholds...")
        thresholds = trainer.evaluate_thresholds(X_val, percentiles=[90, 95, 99])
        print(f"   ✓ Thresholds: {thresholds}")
        
        print("5. Saving checkpoint...")
        checkpoint_path = trainer.save_checkpoint('test_detector')
        print(f"   ✓ Checkpoint: {checkpoint_path}")
        
        # Check metadata
        import json
        metadata_path = checkpoint_path / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        print(f"   ✓ Metadata keys: {list(metadata.keys())}")
        print(f"   ✓ latent_dim in metadata: {metadata.get('latent_dim')}")
        print(f"   ✓ thresholds in metadata: {list(metadata.get('thresholds', {}).keys())}")
        
        print("\n6. Loading checkpoint with ThreatDetector...")
        try:
            detector = ThreatDetector(str(checkpoint_path), threshold_percentile='p95')
            print(f"   ✓ Detector loaded successfully")
            print(f"   ✓ Threshold: {detector.threshold:.4f}")
            print(f"   ✓ Autoencoder model loaded: {detector.autoencoder is not None}")
            
            print("\n✅ ALL TESTS PASSED - Checkpoint fix works!")
            return True
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_checkpoint_fix()
    sys.exit(0 if success else 1)

"""
Test CLIP import in isolation
"""
import os
from pathlib import Path

# Set cache paths BEFORE any imports
backend_dir = Path(__file__).parent
src_dir = backend_dir.parent
os.environ["HF_HOME"] = str(src_dir / ".cache" / "huggingface")
os.environ["TORCH_HOME"] = str(src_dir / ".cache" / "torch")
os.environ["TRANSFORMERS_CACHE"] = str(src_dir / ".cache" / "huggingface" / "transformers")

print("=" * 60)
print("CLIP Import Test")
print("=" * 60)
print(f"HF_HOME: {os.environ['HF_HOME']}")
print(f"TORCH_HOME: {os.environ['TORCH_HOME']}")
print()

print("1. Importing torch...")
try:
    import torch
    print(f"   ✓ torch {torch.__version__}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("2. Importing transformers...")
try:
    from transformers import CLIPModel, CLIPProcessor
    print(f"   ✓ transformers imported")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("3. Loading CLIP model...")
try:
    model_name = "openai/clip-vit-base-patch32"
    cache_dir = os.environ["HF_HOME"]
    print(f"   Loading {model_name} from {cache_dir}")
    model = CLIPModel.from_pretrained(model_name, cache_dir=cache_dir)
    processor = CLIPProcessor.from_pretrained(model_name, cache_dir=cache_dir)
    print(f"   ✓ Model loaded successfully")
    print(f"   Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("=" * 60)
print("SUCCESS - All imports and model loading worked!")
print("=" * 60)

"""
Quick test CLIP với một vài ảnh để kiểm tra xem model có hoạt động không.

Usage:
    python -m scripts.quick_test_clip
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.clip_ingredient_service import recognize_ingredients_with_clip


def test_clip_with_sample():
    """Test CLIP với ảnh mẫu hoặc fake data."""
    
    print("="*80)
    print("CLIP INGREDIENT RECOGNITION - QUICK TEST")
    print("="*80)
    
    # Test 1: Kiểm tra CLIP có load được không
    print("\n[TEST 1] Checking if CLIP model can be loaded...")
    try:
        from app.services.clip_ingredient_service import get_clip_model
        model, processor = get_clip_model()
        if model and processor:
            print("✅ CLIP model loaded successfully!")
            print(f"   Model: {model.__class__.__name__}")
            print(f"   Processor: {processor.__class__.__name__}")
        else:
            print("❌ CLIP model failed to load")
            return False
    except Exception as e:
        print(f"❌ Error loading CLIP model: {e}")
        return False
    
    # Test 2: Kiểm tra với fake image bytes
    print("\n[TEST 2] Testing with minimal fake image...")
    try:
        # Tạo ảnh PNG đơn giản nhất (1x1 pixel đỏ)
        fake_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
            b'\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        
        result = recognize_ingredients_with_clip(
            image_bytes=fake_png,
            filename="test.png"
        )
        
        print(f"✅ Recognition completed!")
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Ingredients found: {len(result.get('ingredients', []))}")
        
        if result.get('candidates'):
            print(f"   Top 3 candidates:")
            for i, cand in enumerate(result['candidates'][:3], 1):
                print(f"      {i}. {cand['name']}: {cand['score']:.4f}")
    
    except Exception as e:
        print(f"❌ Error during recognition: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Thống kê prompts
    print("\n[TEST 3] Prompt statistics...")
    try:
        from app.services.clip_ingredient_service import INGREDIENT_PROMPT_GROUPS, VALID_INGREDIENTS
        
        total_prompts = sum(len(prompts) for prompts in INGREDIENT_PROMPT_GROUPS.values())
        print(f"✅ Total ingredients supported: {len(VALID_INGREDIENTS)}")
        print(f"✅ Total prompts configured: {total_prompts}")
        print(f"✅ Average prompts per ingredient: {total_prompts / len(INGREDIENT_PROMPT_GROUPS):.1f}")
        
        # Top 5 ingredients với nhiều prompts nhất
        sorted_ingredients = sorted(
            INGREDIENT_PROMPT_GROUPS.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        print(f"\n   Top 5 ingredients with most prompts:")
        for i, (name, prompts) in enumerate(sorted_ingredients[:5], 1):
            print(f"      {i}. {name}: {len(prompts)} prompts")
    
    except Exception as e:
        print(f"⚠️  Could not get prompt statistics: {e}")
    
    print("\n" + "="*80)
    print("✅ QUICK TEST COMPLETED SUCCESSFULLY!")
    print("="*80)
    print("\n📝 NEXT STEPS:")
    print("1. Prepare test images: python -m scripts.create_clip_test_dataset")
    print("2. Add images to data/clip_test_images/*/")
    print("3. Run full evaluation: python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images")
    print("\n📖 Read more: docs/CLIP_EVALUATION.md")
    print("="*80)
    
    return True


if __name__ == "__main__":
    success = test_clip_with_sample()
    sys.exit(0 if success else 1)

"""
Script to check and fix failed test images for CLIP evaluation.
Identifies corrupted, invalid, or problematic images and suggests fixes.
"""

import json
import sys
from pathlib import Path
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def check_image_validity(image_path: Path) -> tuple[bool, str]:
    """Check if an image is valid and can be loaded."""
    try:
        with Image.open(image_path) as img:
            img.verify()  # Verify it's a valid image
        
        # Re-open to check if it can be actually loaded
        with Image.open(image_path) as img:
            img.load()  # Try to load the image data
            width, height = img.size
            mode = img.mode
            
            # Check for minimum dimensions
            if width < 50 or height < 50:
                return False, f"Image too small: {width}x{height}"
            
            # Check for valid mode
            if mode not in ['RGB', 'RGBA', 'L', 'P']:
                return False, f"Invalid image mode: {mode}"
            
            return True, f"Valid {mode} image: {width}x{height}"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def fix_image(image_path: Path) -> bool:
    """Try to fix a problematic image by re-saving it."""
    try:
        logger.info(f"  Attempting to fix: {image_path.name}")
        
        # Try to open and re-save the image
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P', 'L'):
                logger.info(f"    Converting {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Create a backup
            backup_path = image_path.with_suffix('.jpg.backup')
            if not backup_path.exists():
                image_path.rename(backup_path)
                logger.info(f"    Created backup: {backup_path.name}")
            
            # Save as new JPEG with high quality
            img.save(image_path, 'JPEG', quality=95, optimize=True)
            logger.info(f"    ✅ Fixed and saved: {image_path.name}")
            return True
            
    except Exception as e:
        logger.error(f"    ❌ Could not fix: {str(e)}")
        return False

def main():
    # Load the evaluation results
    results_file = Path(__file__).parent.parent / 'results' / 'clip_evaluation.json'
    
    if not results_file.exists():
        logger.error(f"Results file not found: {results_file}")
        sys.exit(1)
    
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    failed_images = results.get('failed_images', [])
    
    if not failed_images:
        logger.info("✅ No failed images found!")
        return
    
    logger.info(f"Found {len(failed_images)} failed images")
    logger.info("=" * 60)
    
    # Get test images directory
    test_dir = Path(__file__).parent.parent.parent / 'data' / 'clip_test_images'
    
    if not test_dir.exists():
        logger.error(f"Test directory not found: {test_dir}")
        sys.exit(1)
    
    stats = {
        'total': len(failed_images),
        'valid': 0,
        'invalid': 0,
        'fixed': 0,
        'not_fixed': 0,
        'missing': 0
    }
    
    for failed in failed_images:
        file_path = failed['file']
        ground_truth = failed['ground_truth']
        
        # Convert Windows path to Path object
        image_path = test_dir / file_path.replace('\\', '/')
        
        logger.info(f"\nChecking: {file_path}")
        logger.info(f"  Ground truth: {ground_truth}")
        
        if not image_path.exists():
            logger.warning(f"  ⚠️  File not found!")
            stats['missing'] += 1
            continue
        
        # Check validity
        is_valid, message = check_image_validity(image_path)
        logger.info(f"  Status: {message}")
        
        if is_valid:
            stats['valid'] += 1
            logger.info(f"  ✅ Image is actually valid (may be model limitation)")
        else:
            stats['invalid'] += 1
            logger.info(f"  ❌ Image is invalid or problematic")
            
            # Try to fix
            if fix_image(image_path):
                stats['fixed'] += 1
            else:
                stats['not_fixed'] += 1
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total failed images:     {stats['total']}")
    logger.info(f"Actually valid:          {stats['valid']} (model limitation)")
    logger.info(f"Invalid/problematic:     {stats['invalid']}")
    logger.info(f"  - Successfully fixed:  {stats['fixed']}")
    logger.info(f"  - Could not fix:       {stats['not_fixed']}")
    logger.info(f"Missing files:           {stats['missing']}")
    logger.info("=" * 60)
    
    if stats['fixed'] > 0:
        logger.info(f"\n✅ Fixed {stats['fixed']} images!")
        logger.info("Run evaluation again to check improvement:")
        logger.info("python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images")
    
    if stats['valid'] > 0:
        logger.info(f"\n⚠️  {stats['valid']} images are actually valid but failed recognition.")
        logger.info("This is likely a CLIP model limitation, not an image problem.")
        logger.info("Consider:")
        logger.info("  1. Adding more specific prompts for these ingredients")
        logger.info("  2. Upgrading to CLIP Large model")
        logger.info("  3. Using different test images with clearer features")

if __name__ == '__main__':
    main()

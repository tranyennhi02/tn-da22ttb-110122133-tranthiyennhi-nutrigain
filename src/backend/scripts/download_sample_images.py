"""
Download sample images for CLIP evaluation from free sources.

This script helps you quickly set up test images for CLIP evaluation by:
1. Suggesting keywords to search for
2. Providing download links to free image sources
3. Organizing images into the correct folder structure

Usage:
    python -m scripts.download_sample_images

Manual alternative:
    1. Visit https://unsplash.com or https://pexels.com
    2. Search for each ingredient keyword
    3. Download 10-15 images per ingredient
    4. Save to data/clip_test_images/{Ingredient_Name}/
"""

from pathlib import Path

# Mapping of folder names to search keywords (English and Vietnamese)
INGREDIENT_SEARCH_KEYWORDS = {
    "Thit_bo": ["raw beef", "beef steak", "fresh beef meat"],
    "Thit_lon": ["raw pork", "fresh pork", "pork meat"],
    "Thit_ga": ["raw chicken", "whole chicken", "chicken breast"],
    "Xuc_xich": ["sausage", "hot dog", "grilled sausage"],
    "Ca": ["fresh fish", "raw fish", "whole fish"],
    "Ca_hoi": ["salmon", "salmon fillet", "raw salmon"],
    "Tom": ["shrimp", "prawns", "fresh shrimp"],
    "Cua": ["crab", "fresh crab", "live crab"],
    "Hau": ["oyster", "fresh oysters", "raw oysters"],
    "So": ["clam", "fresh clams", "shellfish"],
    "Trung": ["egg", "chicken egg", "raw egg"],
    "Khoai_lang": ["sweet potato", "raw sweet potato", "orange sweet potato"],
    "Khoai_tay": ["potato", "raw potato", "yellow potato"],
    "Ca_rot": ["carrot", "fresh carrot", "raw carrot"],
    "Ca_chua": ["tomato", "fresh tomato", "red tomato"],
    "Cam": ["orange fruit", "fresh orange", "orange slices"],
    "Chuoi": ["banana", "yellow banana", "ripe banana"],
    "Tao": ["apple", "red apple", "fresh apple"],
    "Sua": ["milk", "glass of milk", "fresh milk"],
    "Dau_hu": ["tofu", "tofu blocks", "bean curd"],
    "Dau_nanh": ["soybeans", "soy beans", "edamame"],
    "Yen_mach": ["oats", "oatmeal", "rolled oats"],
    "Rau_cai": ["bok choy", "leafy greens", "mustard greens"],
    "Bi_do": ["pumpkin", "pumpkin slices", "squash"],
    "Nam": ["mushroom", "fresh mushrooms", "white mushroom"],
    "Com": ["cooked rice", "white rice", "bowl of rice"],
}

FREE_IMAGE_SOURCES = [
    {
        "name": "Unsplash",
        "url": "https://unsplash.com",
        "license": "Free to use (Unsplash License)",
        "search_template": "https://unsplash.com/s/photos/{keyword}",
        "instructions": [
            "1. Click on image",
            "2. Click 'Download free' button",
            "3. Save to appropriate folder",
        ]
    },
    {
        "name": "Pexels",
        "url": "https://pexels.com",
        "license": "Free to use (Pexels License)",
        "search_template": "https://www.pexels.com/search/{keyword}/",
        "instructions": [
            "1. Click on image",
            "2. Click 'Free Download' button",
            "3. Select 'Original' size",
            "4. Save to appropriate folder",
        ]
    },
    {
        "name": "Pixabay",
        "url": "https://pixabay.com",
        "license": "Free to use (Pixabay License)",
        "search_template": "https://pixabay.com/images/search/{keyword}/",
        "instructions": [
            "1. Click on image",
            "2. Click 'Free download' button",
            "3. Select size (1280x720 or larger)",
            "4. Save to appropriate folder",
        ]
    },
]

PRIORITY_INGREDIENTS = [
    "Thit_bo",      # Beef - common protein
    "Thit_ga",      # Chicken - common protein
    "Ca_hoi",       # Salmon - specific seafood
    "Tom",          # Shrimp - common seafood
    "Trung",        # Egg - very common
    "Khoai_lang",   # Sweet potato - confusable with potato
    "Khoai_tay",    # Potato - confusable with sweet potato
    "Ca_rot",       # Carrot - common vegetable
    "Ca_chua",      # Tomato - common vegetable
    "Com",          # Rice - staple food
]


def print_download_guide():
    """Print comprehensive guide for downloading test images."""
    
    print("=" * 80)
    print("CLIP EVALUATION - IMAGE DOWNLOAD GUIDE")
    print("=" * 80)
    
    print("\n📋 SUMMARY:")
    print(f"   Total ingredients to test: {len(INGREDIENT_SEARCH_KEYWORDS)}")
    print(f"   Priority ingredients: {len(PRIORITY_INGREDIENTS)}")
    print(f"   Recommended images per ingredient: 10-15")
    print(f"   Total images needed: {len(INGREDIENT_SEARCH_KEYWORDS) * 10} - {len(INGREDIENT_SEARCH_KEYWORDS) * 15}")
    
    print("\n" + "=" * 80)
    print("FREE IMAGE SOURCES")
    print("=" * 80)
    
    for source in FREE_IMAGE_SOURCES:
        print(f"\n🌐 {source['name']}")
        print(f"   URL: {source['url']}")
        print(f"   License: {source['license']}")
        print(f"   How to download:")
        for instruction in source['instructions']:
            print(f"      {instruction}")
    
    print("\n" + "=" * 80)
    print("PRIORITY INGREDIENTS (START WITH THESE)")
    print("=" * 80)
    
    for idx, folder_name in enumerate(PRIORITY_INGREDIENTS, 1):
        keywords = INGREDIENT_SEARCH_KEYWORDS.get(folder_name, [])
        print(f"\n{idx}. {folder_name}/ (Target: 10-15 images)")
        print(f"   Search keywords: {', '.join(keywords)}")
        print(f"   Unsplash: https://unsplash.com/s/photos/{keywords[0].replace(' ', '-')}")
        print(f"   Pexels: https://www.pexels.com/search/{keywords[0].replace(' ', '%20')}/")
        print(f"   Save to: data/clip_test_images/{folder_name}/")
    
    print("\n" + "=" * 80)
    print("ALL INGREDIENTS (COMPLETE LIST)")
    print("=" * 80)
    
    for folder_name, keywords in sorted(INGREDIENT_SEARCH_KEYWORDS.items()):
        priority = "⭐ PRIORITY" if folder_name in PRIORITY_INGREDIENTS else ""
        print(f"\n📁 {folder_name}/ {priority}")
        print(f"   Keywords: {', '.join(keywords)}")
        print(f"   Target: 10-15 images")
    
    print("\n" + "=" * 80)
    print("TIPS FOR EFFICIENT COLLECTION")
    print("=" * 80)
    
    print("""
1. ⚡ Start with priority ingredients (10 items × 10 images = 100 images)
   - This is enough for initial evaluation
   - Can add more ingredients later

2. 📸 Image quality requirements:
   - Resolution: At least 640×480 pixels
   - Format: JPG, JPEG, or PNG
   - Quality: Clear, well-lit, in focus
   - Background: Any (white, wood, plate, cutting board)

3. 🎯 Diversity matters:
   - Different angles (top view, side view, close-up)
   - Different lighting (natural, indoor)
   - Different presentations (raw, on plate, on cutting board)

4. ⚠️ Avoid:
   - Cooked/processed food (we want raw ingredients)
   - Multiple ingredients in one image
   - Heavily edited/filtered images
   - Watermarked images

5. 📝 Naming convention:
   - Use descriptive names: beef_raw_1.jpg, chicken_breast_2.jpg
   - Sequential numbering: image_1.jpg, image_2.jpg, etc.
   - Avoid spaces: use underscores or hyphens

6. 🚀 Batch download:
   - Open multiple tabs for different keywords
   - Download 2-3 images per tab
   - Save directly to the correct folder
    """)
    
    print("\n" + "=" * 80)
    print("AFTER DOWNLOADING")
    print("=" * 80)
    
    print("""
Run the evaluation:

    cd backend
    python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images

Expected output:
    - Overall accuracy: ~85-95% (target)
    - Per-ingredient accuracy
    - Confusion matrix (which ingredients are confused)
    - Processing time statistics

Results saved to:
    - results/clip_evaluation.json (detailed JSON)
    - results/clip_evaluation_details.csv (CSV for analysis)
    """)
    
    print("=" * 80)
    print("\n✅ Ready to start! Begin with the priority ingredients and collect 10 images each.")
    print("   Estimated time: 30-45 minutes for 100 images\n")


def check_progress():
    """Check how many images have been downloaded so far."""
    base_path = Path(__file__).parent.parent.parent / "data" / "clip_test_images"
    
    if not base_path.exists():
        print("❌ Test directory not found. Run: python -m scripts.create_clip_test_dataset first")
        return
    
    print("\n" + "=" * 80)
    print("DOWNLOAD PROGRESS")
    print("=" * 80)
    
    total_images = 0
    folder_stats = []
    
    for folder_name in INGREDIENT_SEARCH_KEYWORDS.keys():
        folder_path = base_path / folder_name
        if folder_path.exists():
            image_count = len(list(folder_path.glob("*.jpg"))) + \
                         len(list(folder_path.glob("*.jpeg"))) + \
                         len(list(folder_path.glob("*.png")))
            total_images += image_count
            
            if image_count > 0:
                priority = "⭐" if folder_name in PRIORITY_INGREDIENTS else "  "
                status = "✅" if image_count >= 10 else "⚠️"
                folder_stats.append((folder_name, image_count, priority, status))
    
    # Print folders with images
    if folder_stats:
        print(f"\n📊 Found {len(folder_stats)} folders with images:")
        print("-" * 80)
        print(f"{'Folder':<25} {'Images':<10} {'Status':<10} {'Priority'}")
        print("-" * 80)
        
        for folder, count, priority, status in sorted(folder_stats, key=lambda x: -x[1]):
            print(f"{folder:<25} {count:<10} {status:<10} {priority}")
        
        print("-" * 80)
        print(f"Total images: {total_images}")
        
        if total_images >= 100:
            print("\n✅ Good! You have enough images to run evaluation.")
            print("   Run: python -m scripts.evaluate_clip_accuracy --test-dir ../data/clip_test_images")
        elif total_images >= 50:
            print(f"\n⚠️  You have {total_images} images. Recommended: at least 100 images.")
            print("   You can run evaluation now, but results may not be comprehensive.")
        else:
            print(f"\n❌ Only {total_images} images found. Recommended: at least 100 images.")
            print("   Continue downloading to get more reliable evaluation results.")
    else:
        print("\n❌ No images found yet.")
        print("   Start by downloading images for priority ingredients.")
    
    # Show priority ingredients without images
    print("\n📝 Priority ingredients still missing images:")
    missing_priority = []
    for folder_name in PRIORITY_INGREDIENTS:
        folder_path = base_path / folder_name
        if folder_path.exists():
            image_count = len(list(folder_path.glob("*.jpg"))) + \
                         len(list(folder_path.glob("*.jpeg"))) + \
                         len(list(folder_path.glob("*.png")))
            if image_count < 10:
                missing_priority.append((folder_name, image_count))
    
    if missing_priority:
        for folder, count in missing_priority:
            keywords = INGREDIENT_SEARCH_KEYWORDS.get(folder, [])
            print(f"   • {folder}: {count}/10 images")
            print(f"     Search: {keywords[0]}")
    else:
        print("   ✅ All priority ingredients have 10+ images!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--progress":
        check_progress()
    else:
        print_download_guide()
        print("\n" + "=" * 80)
        print("💡 TIP: Run with --progress to check download progress:")
        print("   python -m scripts.download_sample_images --progress")
        print("=" * 80)

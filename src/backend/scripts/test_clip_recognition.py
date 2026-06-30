import sys
import os
import json
import logging

# Add backend dir to PYTHONPATH to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ingredient_recognition_service import recognize_with_clip

# Configure logging to see the logger.info prints locally
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_clip_recognition.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: File not found {image_path}")
        sys.exit(1)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Simple content_type guessing
    ext = os.path.splitext(image_path)[1].lower()
    content_type = "image/jpeg"
    if ext == ".png":
        content_type = "image/png"
    elif ext == ".webp":
        content_type = "image/webp"

    print("====================================")
    print(f"Testing local CLIP recognition on: {image_path}")
    print("====================================")
    print("\n[LOGS]")
    result = recognize_with_clip(image_bytes, content_type)

    print("\n[RESULT JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

"""
CLIP Ingredient Recognition Accuracy Evaluation Script

Đánh giá độ chính xác của CLIP model trong việc nhận diện nguyên liệu từ ảnh.

Usage:
    python -m scripts.evaluate_clip_accuracy --test-dir data/clip_test_images --output-file results/clip_evaluation.json
    
Test directory structure:
    data/clip_test_images/
    ├── Thit_bo/
    │   ├── beef_1.jpg
    │   ├── beef_2.jpg
    │   └── ...
    ├── Thit_ga/
    │   ├── chicken_1.jpg
    │   └── ...
    ├── Ca_hoi/
    │   ├── salmon_1.jpg
    │   └── ...
    └── ...
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.clip_ingredient_service import recognize_ingredients_with_clip


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# Mapping tên thư mục -> tên nguyên liệu chuẩn
FOLDER_TO_INGREDIENT = {
    "Thit_bo": "Thịt bò",
    "Thit_lon": "Thịt lợn",
    "Thit_ga": "Thịt gà",
    "Xuc_xich": "Xúc xích",
    "Ca": "Cá",
    "Ca_hoi": "Cá hồi",
    "Tom": "Tôm",
    "Cua": "Cua",
    "Hau": "Hàu",
    "So": "Sò",
    "Trung": "Trứng",
    "Khoai_lang": "Khoai lang",
    "Khoai_tay": "Khoai tây",
    "Ca_rot": "Cà rốt",
    "Ca_chua": "Cà chua",
    "Cam": "Cam",
    "Chuoi": "Chuối",
    "Tao": "Táo",
    "Sua": "Sữa",
    "Dau_hu": "Đậu hũ",
    "Dau_nanh": "Đậu nành",
    "Yen_mach": "Yến mạch",
    "Rau_cai": "Rau cải",
    "Bi_do": "Bí đỏ",
    "Nam": "Nấm",
    "Com": "Cơm",
}


def evaluate_clip_on_test_set(test_dir: str) -> dict[str, Any]:
    """
    Đánh giá CLIP model trên test dataset.
    
    Args:
        test_dir: Đường dẫn đến thư mục test images (cấu trúc: test_dir/IngredientName/*.jpg)
        
    Returns:
        Dictionary chứa kết quả đánh giá chi tiết
    """
    test_path = Path(test_dir)
    
    if not test_path.exists():
        raise FileNotFoundError(f"Test directory not found: {test_dir}")
    
    results = {
        "test_dir": str(test_path.absolute()),
        "evaluated_at": datetime.now().isoformat(),
        "total_images": 0,
        "total_correct": 0,
        "total_incorrect": 0,
        "total_failed": 0,
        "accuracy": 0.0,
        "per_ingredient_results": {},
        "confusion_matrix": defaultdict(lambda: defaultdict(int)),
        "failed_images": [],
        "detailed_results": [],
    }
    
    # Tìm tất cả các thư mục con (mỗi thư mục = 1 loại nguyên liệu)
    ingredient_folders = [d for d in test_path.iterdir() if d.is_dir()]
    
    if not ingredient_folders:
        logger.warning(f"No ingredient folders found in {test_dir}")
        return results
    
    logger.info(f"Found {len(ingredient_folders)} ingredient folders")
    
    # Duyệt qua từng loại nguyên liệu
    for folder in sorted(ingredient_folders):
        folder_name = folder.name
        ground_truth = FOLDER_TO_INGREDIENT.get(folder_name, folder_name)
        
        logger.info(f"\nEvaluating: {folder_name} (Ground truth: {ground_truth})")
        
        # Tìm tất cả ảnh trong thư mục
        image_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
        
        if not image_files:
            logger.warning(f"  No images found in {folder_name}")
            continue
        
        logger.info(f"  Found {len(image_files)} images")
        
        # Khởi tạo metrics cho nguyên liệu này
        ingredient_metrics = {
            "ground_truth": ground_truth,
            "total_images": len(image_files),
            "correct": 0,
            "incorrect": 0,
            "failed": 0,
            "accuracy": 0.0,
            "avg_confidence": 0.0,
            "avg_processing_time_ms": 0.0,
        }
        
        confidences = []
        processing_times = []
        
        # Test từng ảnh
        for img_file in image_files:
            results["total_images"] += 1
            
            try:
                # Đọc ảnh
                with open(img_file, "rb") as f:
                    image_bytes = f.read()
                
                # Nhận diện
                start_time = time.time()
                recognition_result = recognize_ingredients_with_clip(
                    image_bytes=image_bytes,
                    filename=img_file.name,
                    image_url=None
                )
                processing_time_ms = (time.time() - start_time) * 1000
                processing_times.append(processing_time_ms)
                
                # Lấy kết quả
                success = recognition_result.get("success", False)
                predicted_ingredients = recognition_result.get("ingredients", [])
                
                if not success or not predicted_ingredients:
                    # Nhận diện thất bại
                    results["total_failed"] += 1
                    ingredient_metrics["failed"] += 1
                    results["failed_images"].append({
                        "file": str(img_file.relative_to(test_path)),
                        "ground_truth": ground_truth,
                        "error": "Recognition failed or empty result"
                    })
                    continue
                
                # Lấy prediction đầu tiên
                predicted = predicted_ingredients[0] if isinstance(predicted_ingredients, list) else predicted_ingredients
                predicted_name = predicted.get("name", "") if isinstance(predicted, dict) else str(predicted)
                confidence = predicted.get("confidence", 0.0) if isinstance(predicted, dict) else 0.0
                confidences.append(confidence)
                
                # Kiểm tra đúng/sai
                is_correct = predicted_name == ground_truth
                
                if is_correct:
                    results["total_correct"] += 1
                    ingredient_metrics["correct"] += 1
                else:
                    results["total_incorrect"] += 1
                    ingredient_metrics["incorrect"] += 1
                
                # Cập nhật confusion matrix
                results["confusion_matrix"][ground_truth][predicted_name] += 1
                
                # Lưu chi tiết
                results["detailed_results"].append({
                    "file": str(img_file.relative_to(test_path)),
                    "ground_truth": ground_truth,
                    "predicted": predicted_name,
                    "confidence": confidence,
                    "correct": is_correct,
                    "processing_time_ms": round(processing_time_ms, 2)
                })
                
            except Exception as e:
                logger.error(f"  Error processing {img_file.name}: {e}")
                results["total_failed"] += 1
                ingredient_metrics["failed"] += 1
                results["failed_images"].append({
                    "file": str(img_file.relative_to(test_path)),
                    "ground_truth": ground_truth,
                    "error": str(e)
                })
        
        # Tính metrics cho nguyên liệu này
        if ingredient_metrics["total_images"] > 0:
            ingredient_metrics["accuracy"] = round(
                ingredient_metrics["correct"] / ingredient_metrics["total_images"] * 100, 2
            )
        if confidences:
            ingredient_metrics["avg_confidence"] = round(sum(confidences) / len(confidences), 4)
        if processing_times:
            ingredient_metrics["avg_processing_time_ms"] = round(sum(processing_times) / len(processing_times), 2)
        
        results["per_ingredient_results"][ground_truth] = ingredient_metrics
        
        logger.info(f"  Accuracy: {ingredient_metrics['accuracy']:.2f}% ({ingredient_metrics['correct']}/{ingredient_metrics['total_images']})")
    
    # Tính overall accuracy
    total_evaluated = results["total_correct"] + results["total_incorrect"]
    if total_evaluated > 0:
        results["accuracy"] = round(results["total_correct"] / total_evaluated * 100, 2)
    
    # Convert confusion matrix to regular dict
    results["confusion_matrix"] = {
        k: dict(v) for k, v in results["confusion_matrix"].items()
    }
    
    return results


def print_evaluation_summary(results: dict[str, Any]) -> None:
    """In tóm tắt kết quả đánh giá."""
    print("\n" + "="*80)
    print("CLIP INGREDIENT RECOGNITION - EVALUATION RESULTS")
    print("="*80)
    
    print(f"\nTest Directory: {results['test_dir']}")
    print(f"Evaluated At: {results['evaluated_at']}")
    
    print(f"\n[OVERALL RESULTS]")
    print(f"  Total Images: {results['total_images']}")
    print(f"  Correct: {results['total_correct']}")
    print(f"  Incorrect: {results['total_incorrect']}")
    print(f"  Failed: {results['total_failed']}")
    print(f"  Accuracy: {results['accuracy']:.2f}%")
    
    print(f"\n[PER-INGREDIENT RESULTS]")
    print("-"*80)
    print(f"{'Ingredient':<20} {'Total':<8} {'Correct':<10} {'Accuracy':<12} {'Avg Confidence':<15}")
    print("-"*80)
    
    for ingredient, metrics in sorted(results["per_ingredient_results"].items()):
        print(f"{ingredient:<20} {metrics['total_images']:<8} {metrics['correct']:<10} "
              f"{metrics['accuracy']:>6.2f}%     {metrics['avg_confidence']:>8.4f}")
    
    print("-"*80)
    
    if results["failed_images"]:
        print(f"\n[FAILED IMAGES] ({len(results['failed_images'])}):")
        for fail in results["failed_images"][:10]:  # Show first 10
            print(f"  - {fail['file']}: {fail['error']}")
        if len(results["failed_images"]) > 10:
            print(f"  ... and {len(results['failed_images']) - 10} more")
    
    print("\n" + "="*80)


def export_results_to_csv(results: dict[str, Any], output_csv: str) -> None:
    """Xuất kết quả chi tiết ra CSV."""
    df = pd.DataFrame(results["detailed_results"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Detailed results exported to: {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate CLIP ingredient recognition accuracy on test dataset"
    )
    parser.add_argument(
        "--test-dir",
        required=True,
        help="Path to test images directory (structure: test_dir/IngredientName/*.jpg)"
    )
    parser.add_argument(
        "--output-file",
        default="results/clip_evaluation.json",
        help="Path to output JSON file (default: results/clip_evaluation.json)"
    )
    parser.add_argument(
        "--output-csv",
        default="results/clip_evaluation_details.csv",
        help="Path to output CSV file with detailed results (default: results/clip_evaluation_details.csv)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run evaluation
    logger.info("Starting CLIP evaluation...")
    results = evaluate_clip_on_test_set(args.test_dir)
    
    # Print summary
    print_evaluation_summary(results)
    
    # Save JSON results
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to: {args.output_file}")
    
    # Save CSV details
    if results["detailed_results"]:
        export_results_to_csv(results, args.output_csv)
    
    logger.info("Evaluation complete!")
    
    return 0 if results["accuracy"] >= 70.0 else 1  # Exit code 0 if accuracy >= 70%


if __name__ == "__main__":
    sys.exit(main())

from datetime import datetime, timezone
import math

ASIAN_BMI_LABELS = {
    "underweight": "Gầy / thiếu cân",
    "normal": "Bình thường",
    "overweight": "Thừa cân",
    "obese": "Béo phì",
    "unknown": "Đang theo dõi",
}


def classify_asian_bmi(bmi: float) -> str:
    if bmi is None:
        return "unknown"
    value = round(float(bmi), 1)
    if value < 18.5:
        return "underweight"
    if value < 23:
        return "normal"
    if value < 30:
        return "overweight"
    return "obese"


def asian_bmi_label(category: str | None) -> str:
    return ASIAN_BMI_LABELS.get(str(category or "").strip().lower(), "Đang theo dõi")


class NutritionCalculationService:
    @staticmethod
    def calculate_bmi(weight_kg: float, height_cm: float) -> float:
        if height_cm <= 0:
            return 0.0
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m * height_m), 1)

    @staticmethod
    def get_bmi_status(bmi: float) -> str:
        return classify_asian_bmi(bmi)

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        # Mifflin-St Jeor
        if gender.lower() in ["male", "nam", "m"]:
            return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    @staticmethod
    def get_activity_factor(activity_level: str) -> float:
        normalized = str(activity_level or "").strip().lower()
        factors = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "light": 1.375,
            "light_active": 1.375,
            "moderate": 1.55,
            "moderately_active": 1.55,
            "active": 1.725,
            "very_active": 1.725
        }
        return factors.get(normalized, 1.55)

    @staticmethod
    def calculate_targets(
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        activity_level: str,
        gain_speed: str = "moderate",
        weeks_active: int = 1,
        target_weight: float = None
    ) -> dict:
        bmi = NutritionCalculationService.calculate_bmi(weight_kg, height_cm)
        bmi_status = NutritionCalculationService.get_bmi_status(bmi)
        bmi_label = asian_bmi_label(bmi_status)
        bmr = NutritionCalculationService.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee = bmr * NutritionCalculationService.get_activity_factor(activity_level)
        
        medical_warning = bmi < 16

        # Surplus Logic
        surplus = 0
        ramp_up_week = weeks_active if bmi < 16 else None
        speed_key = str(gain_speed or "medium").strip().lower()
        if speed_key in {"slow", "nhe", "nhẹ"}:
            speed_surplus = 250
        elif speed_key in {"fast", "nhanh", "manh", "mạnh", "aggressive"}:
            speed_surplus = 650
        else:
            speed_surplus = 400
        
        if bmi < 16:
            if weeks_active == 1:
                surplus = 250
            elif weeks_active == 2:
                surplus = 400
            else:
                surplus = speed_surplus
        else:
            surplus = speed_surplus

        calorie_target = round(tdee + surplus)

        # Target Weight Stages
        height_m = height_cm / 100.0
        stage_1_weight = round(16 * (height_m * height_m), 1)
        stage_2_weight = round(18.5 * (height_m * height_m), 1)
        target_weight_missing = target_weight is None or target_weight <= 0

        # Macros: keep protein in a safer 1.4-2.0 g/kg/day band, with
        # 1.6 g/kg as the default weight-gain target.
        reference_weight = stage_1_weight if (bmi < 16 and target_weight_missing) else (target_weight or weight_kg)
        protein_g = round(min(max(1.6 * reference_weight, 1.4 * weight_kg), 2.0 * weight_kg))
        fat_g = round((0.30 * calorie_target) / 9)
        
        remaining_kcal = calorie_target - (protein_g * 4) - (fat_g * 9)
        carbs_g = max(0, round(remaining_kcal / 4))
            
        return {
            "profile_summary": {
                "age": age,
                "gender": gender,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "bmi": bmi,
                "bmi_status": bmi_status,
                "bmi_category": bmi_status,
                "bmi_label": bmi_label,
                "medical_warning": medical_warning,
                "target_weight_missing": target_weight_missing,
                "suggested_stage_1_weight": stage_1_weight,
                "suggested_stage_2_weight": stage_2_weight,
            },
            "nutrition_target": {
                "bmr": round(bmr),
                "tdee": round(tdee),
                "surplus": surplus,
                "ramp_up_week": ramp_up_week,
                "calorie_target": calorie_target,
                "protein_g": protein_g,
                "fat_g": fat_g,
                "carbs_g": carbs_g,
                "calculation_source": "NutritionCalculationService"
            }
        }

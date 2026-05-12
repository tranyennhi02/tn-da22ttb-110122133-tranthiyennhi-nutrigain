import sys
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Add backend to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.database import SessionLocal
from app.models.entities import User, UserProfileEntity, WeightLog

def repair():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "nhi96942@gmail.com").first()
        if not user:
            print("User nhi96942@gmail.com not found!")
            return
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Find weight_log with weight_kg=38, source="profile_update" newest
        logs = db.query(WeightLog).filter(
            WeightLog.user_id == user.id,
            WeightLog.weight_kg == 38.0,
            WeightLog.source == "profile_update"
        ).order_by(WeightLog.id.desc()).all()

        # VN timezone
        VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
        target_date = date(2026, 5, 11)

        # Set created_at corresponds to 2026-05-11 in Asia/Ho_Chi_Minh.
        dt_vn = datetime(2026, 5, 11, 12, 0, 0, tzinfo=VN_TZ)

        if logs:
            log = logs[0]
            print(f"Found log to repair: ID={log.id}, log_date={log.log_date}, created_at={log.created_at}")
        else:
            profile = db.query(UserProfileEntity).filter(UserProfileEntity.user_id == user.id).first()
            if not profile or float(profile.weight_kg or 0) != 38.0:
                print("No weight log of 38kg with source 'profile_update' found, and profile is not 38kg.")
                return

            log = db.query(WeightLog).filter(
                WeightLog.user_id == user.id,
                WeightLog.log_date == target_date,
            ).order_by(WeightLog.id.desc()).first()
            if log:
                print(f"Found existing log on target date to repair: ID={log.id}, weight={log.weight_kg}, source={log.source}")
            else:
                log = WeightLog(
                    user_id=user.id,
                    weight_kg=38.0,
                    log_date=target_date,
                    source="profile_update",
                    is_chart_milestone=False,
                )
                db.add(log)
                print("No 38kg profile_update log found; creating missing 2026-05-11 profile_update log.")

        # Set log_date to 2026-05-11
        log.weight_kg = 38.0
        log.log_date = target_date
        log.source = "profile_update"
        log.created_at = dt_vn
        log.updated_at = dt_vn
        
        db.commit()
        print("Repair successful!")
        print(f"Repaired log: ID={log.id}, log_date={log.log_date}, created_at={log.created_at}")
    except Exception as e:
        db.rollback()
        print(f"Error during repair: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    repair()

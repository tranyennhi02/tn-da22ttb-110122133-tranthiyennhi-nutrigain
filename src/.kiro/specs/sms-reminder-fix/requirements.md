# Requirements Document: Sửa lỗi chức năng nhắc nhở SMS

## Introduction

Chức năng nhắc nhở bữa ăn qua SMS trong NutriGain hiện không hoạt động do 4 vấn đề kỹ thuật:
1. Thiếu biến môi trường Twilio (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) trong `backend/.env`.
2. Lazy loading SQLAlchemy trong `send_test_sms()` gây ra việc đọc `phone_number` từ profile trả về `None` khi session đã đóng.
3. DB session được inject vào endpoint `POST /meal-reminders/test-sms` nhưng không được truyền vào service, khiến service không thể truy vấn profile với session đang hoạt động.
4. Frontend không có API để kiểm tra trạng thái cấu hình Twilio, dẫn đến trải nghiệm người dùng không rõ ràng khi Twilio chưa sẵn sàng.

Spec này mô tả các yêu cầu để sửa các lỗi trên và bổ sung API kiểm tra trạng thái Twilio.

## Glossary

- **SMS_Service**: Module `backend/app/services/sms_service.py`, chịu trách nhiệm gửi SMS qua Twilio.
- **Reminder_Service**: Module `backend/app/services/meal_reminder_service.py`, chứa logic nhắc nhở bữa ăn và hàm `send_test_sms`.
- **Routes**: Module `backend/app/api/routes.py`, định nghĩa các API endpoint FastAPI.
- **Settings**: Class `Settings` trong `backend/app/core/config.py`, đọc biến môi trường.
- **DB_Session**: SQLAlchemy `Session` object được inject qua `Depends(get_db)`.
- **User_Profile**: Entity `UserProfileEntity` chứa `phone_number` và `sms_reminder_enabled`.
- **Twilio**: Dịch vụ gửi SMS bên ngoài, yêu cầu `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
- **Frontend**: Ứng dụng React trong `frontend/src/`.
- **E.164**: Định dạng số điện thoại quốc tế, ví dụ: `+84912345678`.
- **env_file**: File `backend/.env` chứa các biến môi trường cho backend.

---

## Requirements

### Requirement 1: Bổ sung cấu hình Twilio vào file môi trường

**User Story:** Là developer, tôi muốn file `backend/.env` và `backend/.env.example` có các biến Twilio cần thiết, để Twilio được cấu hình đúng và hàm `is_twilio_configured()` trả về `True`.

#### Acceptance Criteria

1. THE `env_file` SHALL chứa các khóa `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, và `TWILIO_PHONE_NUMBER` với giá trị thực (không phải chuỗi rỗng).
2. THE `env_file` example (`backend/.env.example`) SHALL chứa các khóa `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, và `TWILIO_PHONE_NUMBER` với giá trị placeholder minh họa cú pháp đúng.
3. WHEN `Settings` đọc `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, và `TWILIO_PHONE_NUMBER` từ biến môi trường có giá trị hợp lệ, THE `SMS_Service` SHALL trả về `True` từ hàm `is_twilio_configured()`.
4. IF `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, hoặc `TWILIO_PHONE_NUMBER` là chuỗi rỗng, không được đặt, hoặc nếu `Settings` gặp lỗi khi đọc cấu hình, THEN THE `SMS_Service` SHALL trả về `False` từ hàm `is_twilio_configured()`.

---

### Requirement 2: Sửa lỗi lazy loading trong `send_test_sms`

**User Story:** Là người dùng, tôi muốn hàm gửi SMS thử hoạt động đúng, để `phone_number` không bị đọc nhầm thành `None` khi SQLAlchemy session đã đóng.

#### Acceptance Criteria

1. WHEN hàm `send_test_sms` trong `Reminder_Service` được gọi, THE `Reminder_Service` SHALL truy vấn `phone_number` của người dùng trực tiếp từ `DB_Session` đang hoạt động thay vì dùng `getattr(user, "profile", None)`.
2. WHEN `DB_Session` được truyền vào `send_test_sms`, THE `Reminder_Service` SHALL thực hiện truy vấn `SELECT phone_number FROM user_profiles WHERE user_id = :id` sử dụng session đó.
3. IF `phone_number` không tồn tại hoặc là `None` sau khi truy vấn từ DB, THEN THE `Reminder_Service` SHALL trả về `(False, "Tài khoản chưa có số điện thoại để nhận SMS.", None)`.
4. THE `Reminder_Service` SHALL không còn phụ thuộc vào SQLAlchemy lazy relationship `user.profile` để lấy `phone_number` trong hàm `send_test_sms`.

---

### Requirement 3: Truyền DB session vào service trong endpoint test SMS

**User Story:** Là developer, tôi muốn endpoint `POST /api/v1/meal-reminders/test-sms` truyền `DB_Session` vào service, để service có thể truy vấn database với session đang hoạt động.

#### Acceptance Criteria

1. WHEN endpoint `POST /api/v1/meal-reminders/test-sms` trong `Routes` nhận request, THE `Routes` SHALL truyền `db` (DB_Session đang hoạt động) vào hàm `send_test_meal_reminder_sms`.
2. THE hàm `send_test_meal_reminder_sms` trong `Reminder_Service` SHALL chấp nhận tham số `db: Session` bổ sung.
3. THE hàm `send_test_sms` trong class `MealReminderService` SHALL chấp nhận tham số `db: Session` và dùng session đó để truy vấn `phone_number`.
4. IF endpoint nhận request từ người dùng đã xác thực và có số điện thoại trong DB, THEN THE `Routes` SHALL trả về response với `success=True` và `sent_to` chứa số điện thoại đã che một phần.

---

### Requirement 4: API kiểm tra trạng thái cấu hình Twilio

**User Story:** Là người dùng, tôi muốn frontend biết được Twilio có được cấu hình hay không, để giao diện hiển thị thông báo phù hợp khi tính năng SMS chưa khả dụng.

#### Acceptance Criteria

1. THE `Routes` SHALL cung cấp endpoint `GET /api/v1/sms/status` yêu cầu xác thực người dùng.
2. WHEN người dùng đã xác thực gọi `GET /api/v1/sms/status`, THE `Routes` SHALL trả về JSON object với trường `configured: bool` cho biết Twilio có đủ thông tin cấu hình hay không.
3. WHEN `is_twilio_configured()` trả về `True`, THE `Routes` SHALL trả về `{"configured": true}` với HTTP status 200.
4. WHEN `is_twilio_configured()` trả về `False`, THE `Routes` SHALL trả về `{"configured": false}` với HTTP status 200.
5. IF người dùng gọi `GET /api/v1/sms/status` mà không có token xác thực hợp lệ, THEN THE `Routes` SHALL trả về HTTP status 401 mà không kiểm tra trạng thái cấu hình Twilio.

---

### Requirement 5: Cập nhật `.env.example` với hướng dẫn Twilio

**User Story:** Là developer mới, tôi muốn file `.env.example` có hướng dẫn rõ ràng về cách lấy thông tin Twilio, để cấu hình đúng mà không cần tìm kiếm tài liệu bên ngoài.

#### Acceptance Criteria

1. THE `env_file` example SHALL chứa comment giải thích nguồn lấy `TWILIO_ACCOUNT_SID` và `TWILIO_AUTH_TOKEN` (từ Twilio Console tại https://console.twilio.com).
2. THE `env_file` example SHALL chứa comment giải thích định dạng `TWILIO_PHONE_NUMBER` phải là E.164 (ví dụ: `+1234567890`).
3. THE `env_file` example SHALL đặt 3 biến Twilio trong cùng một nhóm với comment phân tách rõ ràng.

---

### Requirement 6: Chuẩn hóa số điện thoại trước khi gửi SMS

**User Story:** Là người dùng Việt Nam, tôi muốn nhập số điện thoại theo định dạng địa phương (ví dụ: `0912345678`), để hệ thống tự động chuyển đổi sang E.164 và gửi SMS thành công qua Twilio.

#### Acceptance Criteria

1. WHEN `Reminder_Service` lấy được `phone_number` từ DB, THE `Reminder_Service` SHALL gọi `_normalize_phone()` từ `SMS_Service` để chuyển đổi sang E.164 trước khi gửi SMS.
2. WHEN `_normalize_phone()` nhận vào số định dạng địa phương Việt Nam bắt đầu bằng `0` và có đúng 10 chữ số, THE `SMS_Service` SHALL trả về số E.164 dạng `+84xxxxxxxxx`.
3. IF `_normalize_phone()` nhận vào chuỗi không hợp lệ (không đủ độ dài, chứa ký tự không phải số sau khi tách ký tự phân cách), THEN THE `SMS_Service` SHALL trả về `None`.
4. WHEN `_normalize_phone()` trả về `None`, THE `Reminder_Service` SHALL không gọi Twilio và trả về `(False, "Số điện thoại không hợp lệ.", None)`.

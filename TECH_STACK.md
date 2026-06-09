# Hệ Thống Gợi Ý Thực Phẩm Tăng Cân Lành Mạnh (NutriGain) - Tech Stack

## 1. Tổng quan hệ thống
NutriGain là một hệ thống ứng dụng thông minh được thiết kế đặc biệt dành cho người gầy (underweight) với mục tiêu hỗ trợ tăng cân lành mạnh. Ứng dụng cung cấp giải pháp toàn diện từ việc theo dõi chỉ số cơ thể, thiết lập mục tiêu cá nhân hóa, cho đến việc đề xuất thực đơn hàng ngày. 

**Đối tượng sử dụng (Target Audience) dựa trên chuẩn BMI Châu Á:**
- **Được hỗ trợ (BMI < 25):** 
  - Người gầy / thiếu cân (BMI < 18.5): Nhóm đối tượng chính cần được hỗ trợ tăng cân an toàn (đặc biệt có cảnh báo y tế và lộ trình riêng "Ramp-up" cho người suy dinh dưỡng nặng BMI < 16).
  - Người có thể trạng bình thường (18.5 ≤ BMI < 25): Có nhu cầu cải thiện hình thể, tăng cơ hoặc tăng thêm cân trong giới hạn an toàn.
- **Không hỗ trợ (BMI ≥ 25):** Hệ thống có cơ chế chặn và từ chối tạo hồ sơ/thực đơn tăng cân đối với nhóm người dùng Thừa cân (25 ≤ BMI < 30) và Béo phì (BMI ≥ 30) vì kiến trúc thuật toán chuyên biệt cho việc tăng cân. Ngoài ra, người dùng cũng không được phép thiết lập cân nặng mục tiêu (Target Weight) vượt quá mức BMI 25.0.

Thay vì chỉ tập trung vào việc tăng lượng calo một cách mù quáng, hệ thống áp dụng các tiêu chuẩn dinh dưỡng khoa học (tránh hội chứng nuôi ăn lại - refeeding syndrome) và kết hợp các yếu tố Gamification để duy trì động lực bền vững cho người dùng trong suốt quá trình thay đổi thể trạng.

## 2. Kiến trúc hệ thống
Hệ thống được thiết kế theo mô hình **Client-Server** hiện đại và được container hóa hoàn toàn:
- **Frontend (Client):** Ứng dụng Single Page Application (SPA) chịu trách nhiệm hiển thị giao diện, quản lý state và tương tác với người dùng.
- **Backend (API Server):** Cung cấp các RESTful endpoints, xử lý logic nghiệp vụ, tính toán dinh dưỡng, xác thực người dùng và tích hợp các module AI/ML.
- **Database:** Hệ quản trị cơ sở dữ liệu quan hệ (RDBMS) lưu trữ thông tin người dùng, dữ liệu thực phẩm, lịch sử bữa ăn và tiến độ.
- **AI/ML Module:** Tích hợp trực tiếp vào backend để xử lý thuật toán gợi ý món ăn (Recommender System) và nhận diện hình ảnh nguyên liệu (Ingredient Recognition).
- **Docker:** Toàn bộ kiến trúc được triển khai đồng bộ thông qua Docker Compose (bao gồm các container `frontend`, `backend`, và `db`).

## 3. Công nghệ sử dụng

### Frontend
- **Framework:** React 18 (build bằng Vite cho tốc độ nhanh, tối ưu hóa).
- **UI & Styling:** Tailwind CSS để xây dựng giao diện tùy chỉnh, kết hợp `clsx` để quản lý class động.
- **Chart / Visualization:** Recharts để vẽ các biểu đồ theo dõi tiến độ cân nặng, thống kê dinh dưỡng.
- **Icons:** Lucide React.
- **PDF Export:** `jspdf`, `jspdf-autotable`, `html2canvas` để xuất báo cáo, lịch sử ăn uống.

### Backend
- **Framework:** FastAPI (Python 3) cho hiệu suất cao, xử lý bất đồng bộ, tự động sinh tài liệu Swagger/OpenAPI. Server chạy bằng Uvicorn.
- **Authentication:** JWT (JSON Web Tokens) cho API authentication, kết hợp `bcrypt` để mã hóa mật khẩu và Google OAuth để hỗ trợ đăng nhập qua Google.
- **API Architecture:** RESTful API.
- **Data Processing:** Pandas, NumPy cho việc xử lý dataset thực phẩm, làm sạch và chuẩn bị dữ liệu cho AI.

### Database
- **Loại database:** MySQL 8.4
- **ORM:** SQLAlchemy kết hợp `pymysql` (Database Driver).
- **Thiết kế dữ liệu dinh dưỡng thực phẩm:** Lưu trữ chi tiết thông tin các món ăn (calories, proteins, fats, carbs), các thành phần nguyên liệu, dữ liệu lịch sử theo dõi (Weight Logs, Meal Consumption) và các thông tin cấu hình cá nhân (Preferences/Allergies).

### Recommendation System & AI
- **Loại hệ thống gợi ý:** Hybrid (Kết hợp Content-based filtering và Rule-based logic).
- **Các công thức toán học và dinh dưỡng cốt lõi áp dụng:**
  1. **Công thức BMI (Chỉ số khối cơ thể):**
     - `BMI = Cân nặng(kg) / [Chiều cao(m)]^2`
  2. **Công thức BMR (Tỷ lệ trao đổi chất cơ bản) - Áp dụng chuẩn Mifflin-St Jeor:**
     - Cho Nam: `BMR = 10 * W(kg) + 6.25 * H(cm) - 5 * Tuổi + 5`
     - Cho Nữ: `BMR = 10 * W(kg) + 6.25 * H(cm) - 5 * Tuổi - 161`
  3. **Công thức TDEE (Tổng năng lượng tiêu hao mỗi ngày):**
     - `TDEE = BMR * Activity_Factor` (Hệ số hoạt động từ 1.2 đến 1.725)
  4. **Công thức Target Calories (Mục tiêu Calo Tăng cân):**
     - `Target_Calories = TDEE + Calorie_Surplus`
     - *Trong đó `Calorie_Surplus` dao động từ 250 kcal (Ramp-up phase/Tăng chậm), 400 kcal (Vừa), đến 650 kcal (Nhanh).*
  5. **Công thức tính tỷ lệ Macronutrients (Chỉ số vĩ mô):**
     - **Protein (g):** Mặc định `1.6 * Target_Weight` (Giới hạn kẹp trong an toàn từ `1.4` đến `2.0 * Current_Weight`).
     - **Fat (g):** Chiếm 30% tổng Calo `(0.3 * Target_Calories) / 9` (Mỗi gam chất béo = 9 kcal).
     - **Carbs (g):** Phần năng lượng còn lại `(Target_Calories - Protein * 4 - Fat * 9) / 4` (Mỗi gam tinh bột/protein = 4 kcal).
  6. **Công thức nội suy Mốc cân nặng an toàn (Dành riêng cho người BMI < 16):**
     - Giai đoạn 1 (Hướng tới BMI 16): `Stage_1_Weight = 16 * [Chiều cao(m)]^2`
     - Giai đoạn 2 (Hướng tới BMI 18.5): `Stage_2_Weight = 18.5 * [Chiều cao(m)]^2`
- **Logic gợi ý thực phẩm:** Lọc thực phẩm theo danh sách dị ứng/không thích của user. Gợi ý bữa ăn thỏa mãn lượng Calories, Protein, Carb, Fat mục tiêu của từng bữa, áp dụng Scikit-learn để tối ưu hóa.
- **Computer Vision:** Tích hợp mô hình CLIP (OpenAI) thông qua PyTorch và Hugging Face Transformers để nhận diện nguyên liệu thực phẩm từ hình ảnh.

### DevOps / Deployment
- **Containerization:** Docker, Docker Compose cho môi trường phát triển và triển khai. Tách biệt `docker-compose.yml` định nghĩa các container `db`, `backend`, `frontend`, và volume mappings (bao gồm cả cache cho mô hình AI).
- **Environment Management:** Quản lý biến môi trường an toàn thông qua `python-dotenv`.

### External APIs
- **Twilio SMS:** Gửi tin nhắn SMS nhắc nhở ăn uống.
- **Google OAuth:** API tích hợp xác thực tài khoản Google.

## 4. Luồng hoạt động hệ thống

1. **User Onboarding:** Người dùng đăng ký/đăng nhập, sau đó cung cấp các thông tin cá nhân (tuổi, giới tính, chiều cao, cân nặng, mức độ vận động) và tùy chọn dinh dưỡng (món ăn dị ứng, sở thích, mục tiêu tăng cân).
2. **Tính toán dinh dưỡng (Core Engine):** Hệ thống tính toán BMI, đưa ra cảnh báo y tế (nếu có). Tính BMR, TDEE, và xác định chính xác lượng Calories, Protein, Fat, Carbs mục tiêu cần nạp mỗi ngày.
3. **Sinh thực đơn (Recommendation):** AI dựa trên hồ sơ người dùng và mục tiêu dinh dưỡng để gợi ý các bữa ăn (Sáng, Trưa, Tối, Phụ) phù hợp nhất từ cơ sở dữ liệu thực phẩm.
4. **Theo dõi và tương tác:** Người dùng thực hiện tính năng "Mark as Eaten" (đánh dấu đã ăn) trên Dashboard. Hệ thống cập nhật số liệu calo đã tiêu thụ/còn lại trong ngày.
5. **Cập nhật tiến độ & Điều chỉnh:** Người dùng log cân nặng theo thời gian. Hệ thống cung cấp biểu đồ tiến độ và tự động tính toán lại TDEE/Meal plan dựa trên mức cân nặng mới.

## 5. Điểm nổi bật của hệ thống
- **Personalized Nutrition & Safety First:** Không chỉ đơn thuần là gợi ý món ăn, hệ thống có cảnh báo y tế sâu sắc (phát hiện BMI quá thấp), áp dụng "Ramp-up phase" giúp tăng cân an toàn, không gây quá tải dạ dày.
- **Gamification & Gentle Motivation:** Thiết kế với triết lý tạo động lực tích cực (Gentle Motivation Panel), người dùng tích lũy EXP, thăng cấp (Leveling system) và thu thập thành tựu (Achievements) thông qua việc ăn đúng bữa, log cân nặng. Ngôn từ hỗ trợ, không mang tính phán xét (body-shaming).
- **Smart Recommendation & Ingredient Recognition:** Hệ thống gợi ý thông minh linh hoạt thay đổi theo sở thích người dùng. Hỗ trợ nhận diện nguyên liệu nhanh bằng AI, mang lại trải nghiệm tiện lợi tối đa.

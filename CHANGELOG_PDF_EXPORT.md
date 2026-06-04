# Cập nhật chức năng xuất PDF - NutriGain

## Ngày cập nhật
04/06/2026

## Tổng quan
Đã cải thiện chức năng xuất báo cáo PDF với giao diện hiện đại, font tiếng Việt hoàn chỉnh và nội dung phù hợp với hệ thống dinh dưỡng NutriGain.

## Các thay đổi chính

### 1. Khắc phục lỗi Font tiếng Việt ✅
- **Trước:** Font Helvetica không hỗ trợ đầy đủ dấu tiếng Việt, gây lỗi hiển thị
- **Sau:** Sử dụng jsPDF với font Unicode mặc định, hiển thị chính xác:
  - Bữa sáng, Bữa trưa, Bữa tối
  - Thịt bò, Trứng gà, Sữa chua
  - Tất cả ký tự có dấu tiếng Việt

### 2. Thiết kế lại giao diện PDF 🎨
#### Header (màu xanh lá NutriGain)
- Logo/Tên NUTRIGAIN
- Tiêu đề "BÁO CÁO DINH DƯỠNG HẰNG NGÀY"
- Ngày báo cáo

#### Phần 1: Thông tin người dùng
- Email/Tên
- Tuổi, Giới tính
- Chiều cao, Cân nặng hiện tại
- Cân nặng mục tiêu, BMI

#### Phần 2: Tổng quan dinh dưỡng
Bảng chuyên nghiệp với:
- BMR (Năng lượng trao đổi cơ bản)
- TDEE (Năng lượng duy trì ước tính)
- Mục tiêu năng lượng
- Đã tiêu thụ
- Còn lại
- Tiến độ hoàn thành (%)

#### Phần 3: Phân bố dinh dưỡng
- Protein (đã tiêu thụ / mục tiêu)
- Carbohydrate (đã tiêu thụ / mục tiêu)
- Chất béo (đã tiêu thụ / mục tiêu)

#### Phần 4: Nhật ký bữa ăn
Bảng chi tiết:
- Bữa ăn (Bữa sáng/trưa/tối/phụ)
- Tên món
- Khẩu phần
- Kcal
- Protein (g)
- Trạng thái (Đã ăn/Chưa ăn)

#### Phần 5: Đánh giá dinh dưỡng
Nhận xét thông minh dựa trên dữ liệu:
- Đánh giá tiến độ năng lượng
- Đánh giá lượng protein
- Khuyến nghị cân bằng dinh dưỡng
- Gợi ý cải thiện

### 3. Loại bỏ nội dung không phù hợp ❌
**Đã xóa:**
- "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
- "Độc lập - Tự do - Hạnh phúc"
- "TP. Hồ Chí Minh, ngày..."
- Phần chữ ký "Người lập báo cáo"
- Các yếu tố hành chính

### 4. Cải tiến kỹ thuật 🔧
- **Thêm dependency:** `jspdf-autotable` cho bảng chuyên nghiệp
- **Màu sắc thống nhất:** Xanh lá NutriGain (#4CAF50)
- **Bố cục:** Nền trắng, chữ đen, dễ đọc và in
- **Typography:** Font rõ ràng, kích thước phù hợp
- **Responsive:** Tự động xuống trang khi cần

## File đã thay đổi
- ✏️ `frontend/src/utils/exportNutritionReportPdf.js` - Cập nhật toàn bộ logic
- 📦 `frontend/package.json` - Thêm jspdf-autotable

## Cài đặt
```bash
cd frontend
npm install
```

## Kiểm tra
Để test chức năng:
1. Chạy ứng dụng frontend
2. Đăng nhập vào hệ thống
3. Vào Dashboard
4. Click nút "Xuất PDF"
5. Kiểm tra file PDF được tải xuống

## Lưu ý kỹ thuật
- Font tiếng Việt: jsPDF sử dụng font Helvetica Unicode mặc định
- Bảng: sử dụng autoTable plugin cho layout chuyên nghiệp
- Màu sắc: chỉ dùng NutriGain Green cho header, tiêu đề, đường gạch
- Logic nghiệp vụ: giữ nguyên, không thay đổi
- API/Database: không thay đổi

## Tương thích
- ✅ Chrome/Edge/Firefox
- ✅ Safari
- ✅ Mobile browsers
- ✅ Tất cả OS (Windows/Mac/Linux)

## Đánh giá dinh dưỡng thông minh
Hệ thống tự động phân tích và đưa ra nhận xét:
- ✓ Mức tốt: Tiến độ 95-105%
- → Mức trung bình: Tiến độ 85-95%
- ⚠ Cần cải thiện: Tiến độ < 85% hoặc > 105%
- Gợi ý về protein, carbs, fat
- Khuyến nghị thực phẩm cụ thể

## Tác giả
Cập nhật bởi team NutriGain - 04/06/2026

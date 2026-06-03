# Cải thiện Báo cáo PDF Dinh Dưỡng

## Ngày cập nhật: 03/06/2026

### Tổng quan
Đã cải thiện hoàn toàn giao diện và nội dung file PDF "Báo cáo dinh dưỡng" để trở nên chuyên nghiệp, dễ đọc và có cấu trúc rõ ràng.

---

## Các thay đổi chính

### 1. **NutritionReportTemplate.jsx** - Cải thiện hoàn toàn template

#### ✅ Sửa lỗi Header
- **Trước:** Header hiển thị sai "NGNUTRIGAIN"
- **Sau:** Hiển thị đúng "NutriGain" với font size phù hợp (22pt)
- Thêm subtitle "Báo cáo dinh dưỡng cá nhân"
- Thêm ngày xuất báo cáo ở góc phải

#### ✅ Cải thiện Font và Typography
- **Body text:** 10pt (thay vì quá lớn)
- **Section title:** 14pt
- **Brand name:** 22pt
- **Table text:** 9pt
- Font family: Segoe UI, Roboto, Arial (hỗ trợ tiếng Việt tốt)

#### ✅ Bố cục chuyên nghiệp
- **Page setup:** A4 portrait với margin 14-16mm
- **Header:** Có nền gradient xanh mint nhạt (#ecfdf5 → #ffffff), border xanh (#059669)
- **User info box:** Hiển thị tách biệt tên và email, không dính chữ
- **Sections:** Chia rõ ràng với border và spacing phù hợp

#### ✅ Thông tin hồ sơ - Layout 2 cột
Thay vì liệt kê dài, giờ hiển thị dạng grid 2 cột với các card:
- Tuổi / Giới tính
- Chiều cao / Cân nặng hiện tại
- Cân nặng mục tiêu / Mục tiêu tăng cân

Mỗi card có:
- Background: #f8fafc
- Border: #e2e8f0
- Label màu xám, Value màu đen đậm

#### ✅ Tổng quan dinh dưỡng - Layout 4 cột
Hiển thị dạng stat boxes với thông tin:
- **Mục tiêu kcal**
- **Đã ăn kcal**
- **Còn lại kcal**
- **Protein**

Mỗi box có:
- Background: #ecfdf5 (xanh mint nhạt)
- Border: #a7f3d0
- Label uppercase nhỏ (8pt)
- Value lớn đậm (13pt)

Thêm progress bar thể hiện % hoàn thành và số món đã ăn.

#### ✅ Bảng món ăn chuyên nghiệp
Cải thiện hoàn toàn table với 6 cột:
- **Bữa** (15%)
- **Món ăn** (35%)
- **Khẩu phần** (15%)
- **Kcal** (12%)
- **Protein** (11%)
- **Trạng thái** (12%)

**Styling:**
- Header: Background #ecfdf5, text #059669, border bottom 2px
- Rows: Xen kẽ trắng và #f8fafc
- Text size: 9pt dễ đọc
- Trạng thái "Đã ăn" màu xanh (#059669), "Chưa ăn" màu xám

#### ✅ Nhận xét dinh dưỡng thông minh
Thêm logic tự động tạo insights dựa trên dữ liệu:

**Kiểm tra năng lượng:**
- 80-110%: "Mức năng lượng hôm nay khá phù hợp với mục tiêu."
- < 80%: "Bạn còn thiếu năng lượng so với mục tiêu, nên bổ sung thêm bữa phụ giàu năng lượng."
- > 110%: "Năng lượng hôm nay vượt mục tiêu, nên điều chỉnh khẩu phần cho phù hợp."

**Kiểm tra protein:**
- < 70%: "Protein hôm nay còn thấp, nên thêm trứng, sữa, thịt, cá hoặc đậu phụ."
- 70-100%: "Lượng protein đạt mức tốt."

**Kiểm tra tiến độ:**
- Chưa ăn món nào: "Chưa có món ăn nào được đánh dấu là đã ăn."
- Ăn ít hơn 50%: "Bạn đã ăn ít hơn một nửa thực đơn hôm nay."

Insight box có:
- Background: #fffbeb (vàng nhạt)
- Border: #fcd34d
- Bullet màu cam (#f59e0b)

#### ✅ Footer chuyên nghiệp
Mỗi trang có footer với:
- "NutriGain • Build healthy calories" (bên trái)
- "Trang 1" (bên phải)
- Text size 8pt màu xám (#64748b)
- Border top #e2e8f0

#### ✅ Disclaimer
Thêm disclaimer ở cuối:
"Báo cáo này chỉ mang tính tham khảo, không thay thế tư vấn từ chuyên gia dinh dưỡng hoặc bác sĩ."
- Font size: 8pt
- Màu xám nhạt (#94a3b8)
- Style: italic
- Align: center

#### ✅ Màu sắc thương hiệu
Sử dụng tone chính của NutriGain:
- **Primary green:** #059669
- **Mint light:** #ecfdf5, #a7f3d0
- **Text dark:** #0f172a
- **Text muted:** #64748b, #94a3b8
- **Border:** #e2e8f0
- **Warning yellow:** #fffbeb, #fcd34d, #f59e0b

#### ✅ Xử lý dữ liệu sạch
- Không hiển thị undefined/null/NaN
- Dùng "Chưa cập nhật" cho dữ liệu thiếu
- Format số theo chuẩn Việt Nam: 2.273 kcal
- Email và tên tách biệt rõ ràng

---

### 2. **exportNutritionReportPdf.js** - Cải thiện chất lượng export

#### ✅ Tăng chất lượng render
- **Scale:** Từ 2 → 3 (chất lượng cao hơn, text sắc nét hơn)
- **Format:** PNG → JPEG với quality 0.95 (file nhẹ hơn, chất lượng vẫn tốt)
- **Compression:** Bật compress trong jsPDF

#### ✅ Cải thiện xử lý nhiều trang
- Logic phân trang chính xác hơn
- Tự động thêm trang nếu nội dung dài
- Mỗi trang giữ nguyên chất lượng

#### ✅ Error handling tốt hơn
- Console log chi tiết cho dev
- Message lỗi thân thiện cho user: "Không thể tạo PDF. Vui lòng thử lại."
- Không để lộ lỗi kỹ thuật ra ngoài

#### ✅ Logging
- Log success với số trang đã export
- Log error với chi tiết kỹ thuật
- Prefix rõ ràng: `[PDF Export]`

---

## Kết quả

### Trước khi cải thiện:
❌ Header lỗi "NGNUTRIGAIN"  
❌ Font quá lớn  
❌ Layout dạng text thô  
❌ Bảng nhỏ, khó đọc  
❌ Không có màu thương hiệu  
❌ Trang 2 bị lẻ, thiếu header/footer  
❌ Email dính với tên  

### Sau khi cải thiện:
✅ Header đúng "NutriGain"  
✅ Font chuẩn, dễ đọc (10-22pt)  
✅ Layout chuyên nghiệp với grid, card, table  
✅ Bảng rõ ràng với 6 cột đầy đủ  
✅ Màu xanh mint thương hiệu NutriGain  
✅ Tất cả trang có header/footer  
✅ Tên và email tách biệt rõ ràng  
✅ Insights tự động dựa trên dữ liệu  
✅ Progress bar trực quan  
✅ Disclaimer và footer chuyên nghiệp  

---

## Test với dữ liệu mẫu

**Profile:**
- Tuổi: 22
- Giới tính: Nữ
- Chiều cao: 167 cm
- Cân nặng hiện tại: 51 kg
- Cân nặng mục tiêu: 56 kg
- Mục tiêu: +5.0 kg

**Expected result:**
✅ Tất cả thông tin hiển thị đúng trong grid 2 cột  
✅ Tổng quan dinh dưỡng hiển thị 4 stat boxes  
✅ Bảng món ăn đầy đủ 6 cột, dễ đọc  
✅ Insights tự động dựa trên % hoàn thành  
✅ Không có trang trắng hoặc lỗi  
✅ Footer "Trang 1" xuất hiện  

---

## Lưu ý kỹ thuật

1. **Inline styles:** Template sử dụng inline styles thay vì CSS class để đảm bảo html2canvas render đúng
2. **Font support:** Dùng system fonts (Segoe UI, Roboto, Arial) để đảm bảo tương thích với html2canvas
3. **Color consistency:** Tất cả màu đều dùng hex code thay vì CSS variables
4. **Page break:** `pageBreakInside: "avoid"` cho sections để tránh cắt ngang
5. **No external images:** Không dùng logo image để tránh CORS issues với html2canvas

---

## Files đã thay đổi

1. `frontend/src/components/reports/NutritionReportTemplate.jsx` - Redesign hoàn toàn
2. `frontend/src/utils/exportNutritionReportPdf.js` - Cải thiện chất lượng export

**Không thay đổi:**
- Backend code
- Meal generation logic
- Recommender service
- Auth logic
- Meal consumption toggle
- Restore functionality

---

## Hướng dẫn sử dụng

1. Click nút "Xuất báo cáo PDF" trên Dashboard
2. Chờ vài giây (html2canvas đang render)
3. PDF sẽ tự động tải về với tên: `nutrigain_report_[timestamp].pdf`

**Lưu ý:**
- PDF có thể mất 3-5 giây để render (scale cao = chất lượng tốt)
- Nếu lỗi, alert sẽ hiện: "Không thể xuất báo cáo PDF. Vui lòng thử lại."
- Dev có thể check console để xem lỗi chi tiết

---

## Tương lai có thể cải thiện

- [ ] Thêm charts/graphs cho tiến độ
- [ ] Export nhiều ngày thành 1 PDF
- [ ] Tùy chọn export language (EN/VI)
- [ ] Watermark hoặc QR code
- [ ] Email PDF trực tiếp
- [ ] Cloud storage integration

---

**Developed with ❤️ for NutriGain**

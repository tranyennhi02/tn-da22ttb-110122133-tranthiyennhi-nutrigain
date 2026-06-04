# Hướng dẫn Test Chức năng Xuất PDF

## Chuẩn bị

1. **Cài đặt dependencies:**
```bash
cd frontend
npm install
```

2. **Kiểm tra packages:**
```bash
npm list jspdf jspdf-autotable
```

Kết quả mong đợi:
- jspdf@^2.5.2
- jspdf-autotable@^3.8.4

## Test trên Development

1. **Chạy frontend:**
```bash
cd frontend
npm run dev
```

2. **Truy cập ứng dụng:**
- Mở trình duyệt: http://localhost:5173
- Đăng nhập vào hệ thống

3. **Test xuất PDF:**
- Vào trang Dashboard
- Đảm bảo có dữ liệu bữa ăn (thêm một vài món nếu cần)
- Click nút "Xuất PDF" ở góc trên bên phải
- File PDF sẽ được tải xuống tự động

## Kiểm tra nội dung PDF

### ✅ Header
- [ ] Nền màu xanh lá (#4CAF50)
- [ ] Logo "NUTRIGAIN" màu trắng
- [ ] Tiêu đề "BÁO CÁO DINH DƯỠNG HẰNG NGÀY"
- [ ] Ngày báo cáo hiển thị đúng

### ✅ Phần 1: Thông tin người dùng
- [ ] Email/Tên hiển thị đúng
- [ ] Tuổi, giới tính
- [ ] Chiều cao, cân nặng
- [ ] BMI

### ✅ Phần 2: Tổng quan dinh dưỡng
- [ ] Bảng có header màu xanh lá
- [ ] BMR, TDEE hiển thị
- [ ] Mục tiêu năng lượng
- [ ] Đã tiêu thụ, còn lại
- [ ] Tiến độ hoàn thành (%)

### ✅ Phần 3: Phân bố dinh dưỡng
- [ ] Protein (đã tiêu thụ / mục tiêu)
- [ ] Carbohydrate
- [ ] Chất béo

### ✅ Phần 4: Nhật ký bữa ăn
- [ ] Bảng có đầy đủ cột: Bữa ăn, Tên món, Khẩu phần, Kcal, Protein, Trạng thái
- [ ] Dữ liệu bữa sáng/trưa/tối hiển thị đúng
- [ ] Tên món tiếng Việt hiển thị chính xác (có dấu)
- [ ] Trạng thái "Đã ăn" / "Chưa ăn"

### ✅ Phần 5: Đánh giá dinh dưỡng
- [ ] Có ít nhất 2-3 dòng đánh giá
- [ ] Đánh giá dựa trên tiến độ (✓, →, ⚠)
- [ ] Khuyến nghị cụ thể về thực phẩm
- [ ] Disclaimer ở cuối

### ✅ Footer
- [ ] Đường kẻ màu xanh lá
- [ ] "NutriGain - Hệ thống Dinh dưỡng Thông minh"
- [ ] Số trang (Trang 1/2, 2/2...)

### ✅ Font tiếng Việt
Test các từ sau phải hiển thị ĐÚNG:
- Bữa sáng, Bữa trưa, Bữa tối
- Khẩu phần
- Đã ăn, Chưa ăn
- Năng lượng
- Đánh giá dinh dưỡng
- Thịt bò, Trứng gà, Sữa chua
- Cơm, Bánh mì, Khoai

### ✅ Không có
- [ ] KHÔNG có "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
- [ ] KHÔNG có "Độc lập - Tự do - Hạnh phúc"
- [ ] KHÔNG có phần chữ ký
- [ ] KHÔNG có "Người lập báo cáo"

## Test trên Production Build

```bash
cd frontend
npm run build
npm run preview
```

Truy cập: http://localhost:4173

Lặp lại các bước test như trên.

## Troubleshooting

### Lỗi: "Cannot find module 'jspdf-autotable'"
```bash
cd frontend
npm install jspdf-autotable
```

### Lỗi: Font tiếng Việt vẫn bị lỗi
- Kiểm tra version jsPDF >= 2.5.0
- Xóa node_modules và cài lại:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Lỗi: Bảng không hiển thị
- Kiểm tra jspdf-autotable version >= 3.8.0
- Kiểm tra console log trong trình duyệt

### PDF không tải xuống
- Kiểm tra console log
- Kiểm tra popup blocker
- Thử trình duyệt khác

## Test Cases

### Test 1: PDF với dữ liệu đầy đủ
- Thêm ít nhất 5 món ăn (2 sáng, 2 trưa, 1 tối)
- Đánh dấu một số món đã ăn
- Xuất PDF và kiểm tra

### Test 2: PDF với dữ liệu rỗng
- Xóa tất cả bữa ăn
- Xuất PDF
- Kiểm tra: phải có thông báo "Chưa có dữ liệu"

### Test 3: PDF với tên món dài
- Thêm món có tên rất dài (>50 ký tự)
- Kiểm tra: tên phải wrap xuống dòng trong bảng

### Test 4: PDF với ký tự đặc biệt
- Thêm món với tên tiếng Việt có đầy đủ dấu
- VD: "Phở bò Hà Nội đặc biệt", "Cơm tấm sườn nướng"
- Kiểm tra: hiển thị chính xác

## Kết quả mong đợi

✅ PDF tải xuống thành công
✅ Tất cả tiếng Việt hiển thị đúng
✅ Bố cục chuyên nghiệp, dễ đọc
✅ Màu sắc NutriGain nhất quán
✅ Dữ liệu chính xác
✅ Đánh giá dinh dưỡng hợp lý

## Báo lỗi

Nếu phát hiện lỗi, ghi chú:
1. Bước thực hiện
2. Kết quả thực tế
3. Kết quả mong đợi
4. Screenshot (nếu có)
5. Console log (nếu có)

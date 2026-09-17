# 📄 Dự Án Quét CV & Bóc Tách Hồ Sơ Thông Minh (Smart CV Parser)

Hệ thống ứng dụng trí tuệ nhân tạo thị giác (Multimodal Vision AI - Gemini Flash) để bóc tách tự động dữ liệu từ các tệp CV/Hồ sơ ứng viên (PDF, DOCX, ảnh chụp PNG/JPG) đơn lẻ hoặc hàng loạt.

Hệ thống thích ứng linh hoạt với **mọi hình thức trình bày khác nhau** (bố cục 1 cột, 2 cột Canva/TopCV, bảng biểu, infographic), tự động nhận diện ngôn ngữ (**Tiếng Việt, Tiếng Anh & Song ngữ**) và xuất dữ liệu ra file **Excel (.xlsx), CSV (UTF-8-sig) và JSON**.

> **Quy tắc quan trọng:** Bất kỳ trường thông tin nào ứng viên không đề cập sẽ được tự động điền giá trị chuẩn: `"Không có thông tin cụ thể"`.

---

## 🌟 Điểm Nổi Bật

1. **Multimodal Vision OCR:** Đọc hiểu bố cục đa cột mà không bị dính dòng như OCR truyền thống.
2. **Xử lý Đa ngôn ngữ tinh tế:**
   - Tự động hiểu các thuật ngữ tiếng Anh tương đương (`Work History` $\rightarrow$ `Kinh nghiệm làm việc`, `Education` $\rightarrow$ `Học vấn`).
   - Chuẩn hóa các trường phân loại (Giới tính: *Nam/Nữ*, Trình độ: *Đại học/Thạc sĩ*, Kinh nghiệm: *X năm*).
   - Giữ nguyên các thuật ngữ chuyên môn kỹ thuật (`Python, React, Docker, B2B Sales...`).
   - Có tùy chọn dịch tóm tắt toàn bộ sang Tiếng Việt.
3. **Cơ chế Rate Limiting & Retry (Tenacity):** Tự động xử lý Exponential Backoff khi gặp lỗi `429 Too Many Requests`.
4. **Bảo mật & Quyền riêng tư (PII):** Tự động dọn dẹp các tệp tạm trên máy sau mỗi phiên quét.
5. **Định dạng Excel chuyên nghiệp:** Header màu Navy, tự căn độ rộng cột, wrap text và cố định (freeze pane) cột Họ Tên.

---

## 📋 Danh Mục 22 Trường Dữ Liệu Bóc Tách

| STT | Tên trường | Khóa dữ liệu | Xử lý khi thiếu |
|---|---|---|---|
| 1 | Họ và tên | `full_name` | "Không có thông tin cụ thể" |
| 2 | Số điện thoại | `phone` | "Không có thông tin cụ thể" |
| 3 | Email | `email` | "Không có thông tin cụ thể" |
| 4 | Ngày / Năm sinh | `date_of_birth` | "Không có thông tin cụ thể" |
| 5 | Giới tính | `gender` | "Không có thông tin cụ thể" |
| 6 | Địa chỉ / Nơi cư trú | `address` | "Không có thông tin cụ thể" |
| 7 | Liên kết cá nhân | `social_links` | "Không có thông tin cụ thể" |
| 8 | Vị trí ứng tuyển / Chức danh | `target_position` | "Không có thông tin cụ thể" |
| 9 | Mục tiêu nghề nghiệp / Tóm tắt | `career_objective` | "Không có thông tin cụ thể" |
| 10 | Trình độ học vấn cao nhất | `highest_degree` | "Không có thông tin cụ thể" |
| 11 | Chi tiết học vấn | `education_details` | "Không có thông tin cụ thể" |
| 12 | Tổng số năm kinh nghiệm | `years_of_experience` | "Không có thông tin cụ thể" |
| 13 | Chi tiết kinh nghiệm làm việc | `work_experience_details` | "Không có thông tin cụ thể" |
| 14 | Kỹ năng chuyên môn (Hard skills) | `hard_skills` | "Không có thông tin cụ thể" |
| 15 | Kỹ năng mềm (Soft skills) | `soft_skills` | "Không có thông tin cụ thể" |
| 16 | Ngoại ngữ & Trình độ | `languages` | "Không có thông tin cụ thể" |
| 17 | Chứng chỉ chuyên môn | `certifications` | "Không có thông tin cụ thể" |
| 18 | Dự án tiêu biểu | `projects` | "Không có thông tin cụ thể" |
| 19 | Giải thưởng / Thành tích | `awards` | "Không có thông tin cụ thể" |
| 20 | Mức lương mong muốn | `expected_salary` | "Không có thông tin cụ thể" |
| 21 | Ngôn ngữ của CV | `cv_language` | "Không có thông tin cụ thể" |
| 22 | Tên file gốc | `source_file` | Tên tệp thực tế |

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### 1. Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### 2. Cấu hình API Key
- Lấy API Key miễn phí tại: [Google AI Studio](https://aistudio.google.com/app/apikey)
- Bạn có thể tạo file `.env` từ `.env.example`:
  ```env
  GEMINI_API_KEY=your_actual_api_key
  ```
  *(Hoặc nhập trực tiếp API Key trên giao diện thanh bên của ứng dụng Web)*

### 3. Khởi chạy Giao diện Web
```bash
streamlit run app.py
```
Trình duyệt sẽ tự động mở tại địa chỉ: `http://localhost:8501`.


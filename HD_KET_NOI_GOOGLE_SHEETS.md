# 📘 Hướng Dẫn: Đồng Bộ Dữ Liệu Lên Google Sheets & Đưa Ứng Dụng Lên Cloud

Tài liệu này hướng dẫn bạn thực hiện 2 việc:
1. **Kết nối Google Sheet (Chỉ mất 2 phút theo Phương án A - Webhook)**.
2. **Đưa ứng dụng lên Cloud (Streamlit Community Cloud)** để cả đội ngũ nhân sự cùng truy cập từ xa.

---

## PHẦN 1: Cấu Hình Google Sheets (Mất đúng 2 phút)

Bạn không cần tài khoản Google Cloud hay thẻ tín dụng. Hãy làm theo các bước sau:

### Bước 1: Tạo Google Sheet mới
1. Truy cập [sheets.new](https://sheets.new) để mở một bảng tính Google Sheet mới.
2. Đặt tên bảng tính, ví dụ: **`Hồ Sơ Tuyển Dụng - Quét CV`**.

### Bước 2: Dán mã Webhook
1. Trên thanh công cụ của Google Sheet, bấm vào: **Tiện ích mở rộng** *(Extensions)* $\rightarrow$ chọn **Apps Script**.
2. Một trang soạn thảo code sẽ mở ra. Xóa sạch mọi dòng code mặc định trong đó.
3. Mở file [`google_apps_script.js`](./google_apps_script.js) trong thư mục dự án này, **copy toàn bộ nội dung** và dán vào Apps Script.
4. Bấm biểu tượng đĩa mềm 💾 **Lưu dự án** *(Save project)*.

### Bước 3: Triển khai Web App (Deploy)
1. Ở góc trên cùng bên phải màn hình Apps Script, bấm nút **Triển khai** *(Deploy)* $\rightarrow$ chọn **Triển khai dưới dạng ứng dụng web mới** *(New deployment)*.
2. Điền thông tin như sau:
   - **Chọn loại:** Nhấn biểu tượng bánh răng $\rightarrow$ Chọn *Ứng dụng web (Web app)*.
   - **Mô tả:** `CV Parser API`
   - **Thực thi dưới dạng (Execute as):** `Tôi` *(Me)*
   - **Ai có quyền truy cập (Who has access):** `Bất kỳ ai` *(Anyone)* $\leftarrow$ **QUAN TRỌNG NHẤT** (để ứng dụng gửi dữ liệu qua được).
3. Bấm nút **Triển khai** *(Deploy)*.
4. Nếu Google hiện cửa sổ *"Ủy quyền truy cập"* *(Authorize access)*:
   - Chọn tài khoản Google của bạn.
   - Bấm vào chữ nhỏ **Nâng cao** *(Advanced)* $\rightarrow$ Chọn **Đi tới CV Parser API (không an toàn)** *(Go to CV Parser API)*.
   - Bấm **Cho phép** *(Allow)*.
5. Sau khi triển khai xong, bạn sẽ nhận được một đường link dạng:
   `https://script.google.com/macros/s/AKfycb.../exec`
   👉 **Copy đường link này!**

### Bước 4: Dán link vào ứng dụng Quét CV
- **Cách 1 (Ngay trên giao diện Web):** Mở app Streamlit, ở thanh bên trái tìm ô **"🔗 Google Sheets Webhook URL"** $\rightarrow$ dán link vào và bấm **"🔌 Kiểm tra kết nối Google Sheet"**.
- **Cách 2 (Lưu lâu dài vào .env):** Mở file `.env` thêm dòng:
  ```env
  GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/AKfycb.../exec
  ```

🎉 **Xong!** Từ bây giờ, mỗi khi bạn hoặc bất kỳ ai quét CV, dữ liệu sẽ **tự động nhảy trực tiếp vào file Google Sheet** này trong nháy mắt!

---

## PHẦN 2: Đưa Ứng Dụng Lên Cloud (Streamlit Community Cloud)

Để nhiều người trong công ty có thể truy cập cùng lúc từ mọi máy tính hoặc điện thoại:

### Bước 1: Tạo Git Repository & Đẩy Code Lên GitHub
1. Mở Terminal trong VS Code và khởi tạo git (nếu chưa có):
   ```bash
   git init
   git add .
   git commit -m "Khoi tao he thong Quet CV ket noi Google Sheets"
   ```
2. Lên [github.com](https://github.com), bấm **New repository** (đặt tên ví dụ: `quet-cv-ai`, có thể chọn chế độ **Private** để bảo mật code của bạn).
3. Đẩy code lên GitHub theo lệnh hướng dẫn của GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/quet-cv-ai.git
   git branch -M main
   git push -u origin main
   ```

### Bước 2: Deploy lên Streamlit Cloud
1. Truy cập [share.streamlit.io](https://share.streamlit.io) và đăng nhập bằng tài khoản GitHub của bạn.
2. Bấm nút **Create app** (hoặc **New app**).
3. Điền thông tin:
   - **Repository:** Chọn `YOUR_USERNAME/quet-cv-ai`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Bấm vào **Advanced settings...** (hoặc sau khi deploy vào menu *Settings -> Secrets*):
   Dán các biến bí mật vào:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   GOOGLE_SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycb.../exec"
   ```
5. Bấm **Deploy!**

Sau 1-2 phút, ứng dụng của bạn sẽ hoạt động trực tiếp tại địa chỉ công khai:
👉 `https://YOUR_APP_NAME.streamlit.app`

Bạn chỉ cần gửi đường link này cho các đồng nghiệp tuyển dụng, mọi người chỉ việc truy cập bằng trình duyệt để tải CV lên, và toàn bộ kết quả bóc tách sẽ tự động đổ dồn về đúng **1 file Google Sheet duy nhất của phòng ban**!


import os
from pathlib import Path
from dotenv import load_dotenv

# Tải biến môi trường từ tệp .env nếu có
load_dotenv()

# Đường dẫn gốc của dự án
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"

# Giá trị chuẩn hóa mặc định khi trường thông tin không có trong CV
DEFAULT_MISSING_VALUE = "Không có thông tin cụ thể"

# Các định dạng tài liệu được hỗ trợ
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"]

# Cấu hình mô hình Gemini AI
DEFAULT_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
FALLBACK_MODEL_NAME = "gemini-3.1-flash-lite"

# Cấu hình tối ưu hóa & nén ảnh
MAX_IMAGE_DIMENSION = 1800  # Kích thước chiều dài tối đa (px)
JPEG_QUALITY = 85           # Chất lượng nén ảnh JPEG

# Cấu hình cơ chế Retry & Rate Limiting
MAX_RETRIES = 5             # Số lần thử lại tối đa khi gặp lỗi 429
MIN_RETRY_WAIT = 2          # Thời gian chờ tối thiểu (giây)
MAX_RETRY_WAIT = 30         # Thời gian chờ tối đa (giây)

# Lấy API Key từ môi trường
def get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")

# Lấy Google Sheets Webhook URL từ môi trường
def get_google_sheet_webhook_url() -> str:
    return os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "")


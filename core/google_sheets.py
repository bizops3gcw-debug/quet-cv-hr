import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import requests

from models.schema import ResumeData, FIELD_MAPPING, VIETNAMESE_COLUMNS

logger = logging.getLogger(__name__)

REVERSE_FIELD_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}


class GoogleSheetClient:
    """
    Client kết nối và đồng bộ dữ liệu với Google Sheets qua Google Apps Script Webhook API:
    - Đồng bộ thời gian thực (Real-time Sync).
    - Tự động chống trùng lặp trực tiếp trên Google Sheets (theo Số điện thoại & Email).
    - Hỗ trợ tải dữ liệu từ Google Sheets về ứng dụng.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()

    def is_configured(self) -> bool:
        """Kiểm tra xem webhook URL đã được cấu hình hợp lệ chưa."""
        return bool(self.webhook_url and "script.google.com" in self.webhook_url)

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra kết nối tới Google Sheets Webhook."""
        if not self.is_configured():
            return False, "Chưa nhập Webhook URL hoặc URL không hợp lệ (phải bắt đầu bằng https://script.google.com/...)"

        try:
            # Gửi GET request kiểm tra
            resp = requests.get(self.webhook_url, timeout=45, allow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    return True, f"Kết nối Google Sheet thành công! Hiện có {data.get('count', 0)} dòng dữ liệu."
                else:
                    return False, f"Google Sheet phản hồi lỗi: {data.get('message', 'Không rõ')}"
            else:
                return False, f"Lỗi HTTP {resp.status_code} khi kết nối Google Sheet."
        except Exception as e:
            return False, f"Không thể kết nối tới Google Sheet: {str(e)}"

    def sync_resumes(self, resumes: List[ResumeData]) -> Dict[str, Any]:
        """
        Đẩy danh sách ứng viên lên Google Sheets:
        - Tự động bỏ qua các ứng viên bị trùng lặp trên Google Sheets.
        - Trả về kết quả: {status, added, duplicates, skipped, message}
        """
        if not self.is_configured():
            return {"status": "error", "message": "Google Sheet Webhook URL chưa được cấu hình."}

        if not resumes:
            return {"status": "success", "added": 0, "duplicates": 0, "message": "Không có dữ liệu để đồng bộ."}

        # Chuyển đổi thành danh sách các bản ghi có tên cột Tiếng Việt
        payload = {
            "action": "append",
            "resumes": [r.to_vietnamese_dict() for r in resumes],
        }

        try:
            resp = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=45,
                allow_redirects=True,
            )

            if resp.status_code == 200:
                data = resp.json()
                return data
            else:
                return {
                    "status": "error",
                    "message": f"Lỗi HTTP {resp.status_code} từ Google Apps Script Webhook.",
                }
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ Google Sheet: {e}")
            return {"status": "error", "message": str(e)}

    def fetch_resumes(self) -> Tuple[List[ResumeData], Optional[str]]:
        """
        Tải toàn bộ danh sách ứng viên hiện có từ Google Sheet về hệ thống.
        """
        if not self.is_configured():
            return [], "Google Sheet Webhook URL chưa được cấu hình."

        try:
            resp = requests.get(self.webhook_url, timeout=45, allow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    rows = data.get("data", [])
                    resumes = []
                    for row in rows:
                        row_dict = {}
                        for vn_col, val in row.items():
                            if vn_col in REVERSE_FIELD_MAPPING:
                                field_key = REVERSE_FIELD_MAPPING[vn_col]
                                row_dict[field_key] = val
                        if row_dict.get("full_name"):
                            resumes.append(ResumeData.model_validate(row_dict))
                    return resumes, None
                else:
                    return [], data.get("message")
            return [], f"Lỗi HTTP {resp.status_code}"
        except Exception as e:
            return [], str(e)


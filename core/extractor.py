import json
import logging
from typing import List, Optional
from PIL import Image

import google.generativeai as genai
from pydantic import ValidationError

from config import (
    DEFAULT_MODEL_NAME,
    FALLBACK_MODEL_NAME,
    DEFAULT_MISSING_VALUE,
)
from models.schema import ResumeData, ResumeGeminiSchema

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Bạn là một chuyên gia bóc tách hồ sơ ứng viên (Resume/CV Parser AI) hàng đầu thế giới.
Nhiệm vụ của bạn là phân tích toàn diện tài liệu CV (bằng hình ảnh hoặc văn bản) và trích xuất chính xác các trường dữ liệu theo đúng cấu trúc JSON được yêu cầu.

CÁC NGUYÊN TẮC BẮT BUỘC:
1. XỬ LÝ BỐ CỤC ĐA DẠNG:
   - CV có thể được thiết kế 1 cột, 2 cột (Canva, TopCV), bảng biểu, infographic hoặc các khối thông tin độc lập.
   - Hãy quan sát kỹ toàn bộ bố cục trang để đọc đúng mạch thông tin, không làm lẫn lộn giữa cột bên trái (thường chứa Liên hệ, Kỹ năng) và cột bên phải (thường chứa Kinh nghiệm, Học vấn).

2. QUY TẮC BÓC TÁCH CHI TIẾT (ĐẶC BIỆT CHO THỰC TẬP SINH / SINH VIÊN):
   - Cột 'email': Phải trích xuất chính xác địa chỉ email (VD: abc@gmail.com) vào trường riêng biệt.
   - Cột 'university': Trích xuất riêng Tên trường Đại học/Cao đẳng (VD: Đại học Văn Lang, UEH, HCMUTE, Đại học Luật TP.HCM, ĐH Kinh tế - Luật...).
   - Cột 'major': Trích xuất riêng Chuyên ngành đào tạo (VD: Luật Kinh tế, Quản trị Nhân lực, Quản trị Kinh doanh, English for Business...).
   - Cột 'gpa': Trích xuất điểm trung bình tích lũy GPA nếu ứng viên có ghi (VD: "3.21/4.0", "3.57/4", "8.2/10"). Nếu không ghi điểm rõ ràng thì điền "Không có thông tin cụ thể".
   - Cột 'graduation_year': Trích xuất năm tốt nghiệp thực tế hoặc năm tốt nghiệp dự kiến (lấy con số năm cuối cùng trong niên khóa học tập, VD: niên khóa 2022-2026 thì lấy "2026", 2023-2027 thì lấy "2027").
   - Cột 'extracurricular_activities': Trích xuất toàn bộ các hoạt động ngoại khóa, câu lạc bộ, tình nguyện (Mùa hè xanh, Tiếp sức mùa thi), ban chấp hành đoàn hội, dự án xã hội. TUYỆT ĐỐI KHÔNG gộp phần này vào Kinh nghiệm làm việc (work_experience_details) hay Dự án (projects).

3. XỬ LÝ ĐA NGÔN NGỮ (TIẾNG VIỆT, TIẾNG ANH & SONG NGỮ):
   - Hệ thống tự động hiểu cả tiếng Việt và tiếng Anh.
   - Điền trường 'cv_language' là 'Tiếng Việt', 'Tiếng Anh' hoặc 'Song ngữ'.
   - Giữ nguyên các thuật ngữ chuyên ngành kỹ thuật, tên công cụ, framework (ví dụ: Python, Docker, React, Spring Boot, B2B Sales, PMP...).

4. NGUYÊN TẮC TRƯỜNG DỮ LIỆU THIẾU:
   - Nếu bất kỳ trường thông tin nào KHÔNG xuất hiện hoặc không được ứng viên đề cập trong CV, bạn PHẢI điền chính xác chuỗi: "Không có thông tin cụ thể".
   - Tuyệt đối không tự bịa đặt, suy đoán hoặc điền thông tin không có trong tài liệu.

5. ĐỊNH DẠNG ĐẦU RA:
   - Xuất dữ liệu dưới dạng JSON tuân thủ nghiêm ngặt theo schema được cung cấp.
"""


class ResumeExtractor:
    """
    Bộ bóc tách CV sử dụng Gemini Vision / Multimodal API với tính năng ép kiểu Structured Output.
    """

    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL_NAME):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=self.api_key)

    def extract(
        self,
        images: List[Image.Image],
        text_content: str = "",
        filename: str = "",
        translate_to_vietnamese: bool = False,
    ) -> ResumeData:
        """
        Thực hiện bóc tách dữ liệu từ các trang ảnh hoặc văn bản của CV.
        """
        # Chuẩn bị prompt bổ sung nếu người dùng muốn dịch tóm tắt sang Tiếng Việt
        user_prompt = f"Tệp CV cần bóc tách: '{filename}'.\n"
        if translate_to_vietnamese:
            user_prompt += (
                "LƯU Ý ĐẶC BIỆT: Hãy dịch các phần mô tả chi tiết (Kinh nghiệm, Mục tiêu, Dự án) "
                "sang Tiếng Việt rõ ràng, dễ hiểu. Giữ nguyên các từ khóa kỹ thuật chuyên môn.\n"
            )
        else:
            user_prompt += "Giữ nguyên ngôn ngữ gốc của phần mô tả công việc, kỹ năng và dự án.\n"

        if text_content:
            user_prompt += f"\n--- NỘI DUNG VĂN BẢN TRÍCH XUẤT TỪ FILE ---\n{text_content}\n"

        # Danh sách các nội dung đầu vào gửi cho Gemini (bao gồm văn bản prompt + các trang ảnh nén)
        contents = [user_prompt]
        if images:
            contents.extend(images)

        # Cấu hình Structured Output ép kiểu theo TypedDict schema chuẩn Google
        generation_config = {
            "temperature": 0.1,
            "response_mime_type": "application/json",
            "response_schema": ResumeGeminiSchema,
        }

        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                system_instruction=SYSTEM_PROMPT,
            )
            response = model.generate_content(contents)
            return self._parse_response(response.text, filename)
        except Exception as e:
            logger.warning(f"Lỗi khi gọi mô hình {self.model_name}: {e}. Đang thử mô hình dự phòng {FALLBACK_MODEL_NAME}...")
            try:
                fallback_model = genai.GenerativeModel(
                    model_name=FALLBACK_MODEL_NAME,
                    generation_config=generation_config,
                    system_instruction=SYSTEM_PROMPT,
                )
                response = fallback_model.generate_content(contents)
                return self._parse_response(response.text, filename)
            except Exception as e2:
                logger.error(f"Lỗi khi bóc tách file {filename}: {e2}")
                raise e2

    def _parse_response(self, response_text: str, filename: str) -> ResumeData:
        """Parse và validate chuỗi JSON trả về từ Gemini."""
        try:
            data_dict = json.loads(response_text)
            data_dict["source_file"] = filename
            resume_data = ResumeData.model_validate(data_dict)
            return resume_data
        except (json.JSONDecodeError, ValidationError) as err:
            logger.error(f"Lỗi parse JSON cho file {filename}: {err}")
            # Fallback tạo một đối tượng mặc định với tên file
            return ResumeData(source_file=filename)


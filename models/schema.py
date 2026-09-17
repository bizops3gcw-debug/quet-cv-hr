from typing import Optional, Dict, Any, TypedDict
from pydantic import BaseModel, Field, field_validator, model_validator
from config import DEFAULT_MISSING_VALUE

# Bảng ánh xạ từ mã trường sang Tên cột Tiếng Việt hiển thị trên Excel/Dashboard/Google Sheets
FIELD_MAPPING: Dict[str, str] = {
    "full_name": "Họ và tên",
    "phone": "Số điện thoại",
    "email": "Email",
    "date_of_birth": "Ngày / Năm sinh",
    "gender": "Giới tính",
    "address": "Địa chỉ / Nơi cư trú",
    "social_links": "Liên kết cá nhân (LinkedIn/GitHub/Portfolio)",
    "target_position": "Vị trí ứng tuyển / Chức danh",
    "career_objective": "Mục tiêu nghề nghiệp / Tóm tắt",
    "highest_degree": "Trình độ học vấn cao nhất",
    "university": "Tên trường Đại học / Cao đẳng",
    "major": "Chuyên ngành đào tạo",
    "gpa": "Điểm GPA",
    "graduation_year": "Năm tốt nghiệp (Dự kiến)",
    "education_details": "Chi tiết học vấn",
    "years_of_experience": "Tổng số năm kinh nghiệm",
    "work_experience_details": "Chi tiết kinh nghiệm làm việc",
    "hard_skills": "Kỹ năng chuyên môn (Hard skills)",
    "soft_skills": "Kỹ năng mềm (Soft skills)",
    "languages": "Ngoại ngữ & Trình độ",
    "certifications": "Chứng chỉ chuyên môn",
    "extracurricular_activities": "Hoạt động ngoại khóa",
    "projects": "Dự án tiêu biểu",
    "awards": "Giải thưởng / Thành tích",
    "expected_salary": "Mức lương mong muốn",
    "cv_language": "Ngôn ngữ của CV",
    "source_file": "Tên file gốc",
}

VIETNAMESE_COLUMNS = list(FIELD_MAPPING.values())


class ResumeGeminiSchema(TypedDict, total=False):
    """Schema chuẩn TypedDict cho Google Generative AI response_schema."""
    full_name: str
    phone: str
    email: str
    date_of_birth: str
    gender: str
    address: str
    social_links: str
    target_position: str
    career_objective: str
    highest_degree: str
    university: str
    major: str
    gpa: str
    graduation_year: str
    education_details: str
    years_of_experience: str
    work_experience_details: str
    hard_skills: str
    soft_skills: str
    languages: str
    certifications: str
    extracurricular_activities: str
    projects: str
    awards: str
    expected_salary: str
    cv_language: str



class ResumeData(BaseModel):
    """
    Cấu trúc dữ liệu bóc tách từ CV.
    Mọi trường bị thiếu sẽ tự động được gán DEFAULT_MISSING_VALUE ('Không có thông tin cụ thể').
    """

    # Nhóm 1: Thông tin cá nhân & Liên hệ
    full_name: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Họ và tên đầy đủ của ứng viên. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    phone: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Số điện thoại liên hệ. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    email: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Địa chỉ email liên hệ. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    date_of_birth: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Ngày sinh hoặc năm sinh của ứng viên (định dạng DD/MM/YYYY hoặc YYYY). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    gender: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Giới tính (Nam, Nữ). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    address: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Địa chỉ, quận/huyện, tỉnh/thành phố nơi cư trú. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    social_links: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Đường dẫn LinkedIn, GitHub, Portfolio, Website cá nhân. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )

    # Nhóm 2: Vị trí & Mục tiêu
    target_position: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Vị trí ứng tuyển hoặc chức danh nghề nghiệp hiện tại. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    career_objective: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Tóm tắt giới thiệu bản thân hoặc mục tiêu nghề nghiệp. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )

    # Nhóm 3: Học vấn & Đào tạo (Các trường lọc độc lập cho HR)
    highest_degree: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Trình độ học vấn cao nhất (Đại học, Thạc sĩ, Tiến sĩ, Cao đẳng...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    university: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Tên trường Đại học / Cao đẳng / Cơ sở đào tạo (Ví dụ: Đại học Văn Lang, ĐH Kinh tế - Luật, HCMUTE, UEH...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    major: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Chuyên ngành học của ứng viên (Ví dụ: Luật Kinh tế, Quản trị Nhân sự, Quản trị Kinh doanh, Kế toán...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    gpa: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Điểm trung bình tích lũy GPA nếu ứng viên có đề cập (Ví dụ: '3.21/4.0', '3.57/4', '8.2/10'). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    graduation_year: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Năm tốt nghiệp thực tế hoặc năm tốt nghiệp dự kiến (Ví dụ: '2026', '2027', 'Đã tốt nghiệp 2024'). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    education_details: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Chi tiết tổng quan các trường đã học, chuyên ngành, niên khóa. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )

    # Nhóm 4: Kinh nghiệm làm việc
    years_of_experience: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Ước tính tổng số năm kinh nghiệm làm việc (ví dụ: '2 năm', '5 năm', 'Mới tốt nghiệp'). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    work_experience_details: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Lịch sử quá trình làm việc: các công ty, chức vụ, thời gian làm việc, nhiệm vụ chính và thành tích. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )

    # Nhóm 5: Kỹ năng & Năng lực
    hard_skills: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các kỹ năng chuyên môn kỹ thuật, công cụ, công nghệ (ví dụ: Python, SQL, Báo cáo thuế, SEO...). Giữ nguyên tên công nghệ gốc. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    soft_skills: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các kỹ năng mềm (Giao tiếp, làm việc nhóm, quản lý thời gian, giải quyết vấn đề...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    languages: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các ngoại ngữ và trình độ / chứng chỉ ngoại ngữ (ví dụ: Tiếng Anh - IELTS 7.0, Tiếng Nhật N2...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    certifications: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các chứng chỉ chuyên môn nghề nghiệp (ví dụ: AWS Certified, PMP, CPA, CFA...). Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )

    # Nhóm 6: Dự án & Bổ sung
    extracurricular_activities: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Toàn bộ các hoạt động ngoại khóa, câu lạc bộ, tình nguyện, đoàn hội, dự án cộng đồng. Không gộp vào kinh nghiệm làm việc. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    projects: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các dự án tiêu biểu ứng viên đã tham gia, sản phẩm nổi bật. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    awards: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Các giải thưởng, học bổng hoặc thành tích đã đạt được. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    expected_salary: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Mức lương mong muốn nếu có đề cập trong CV. Nếu không có thì ghi 'Không có thông tin cụ thể'."
    )
    cv_language: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Ngôn ngữ chính của CV: 'Tiếng Việt', 'Tiếng Anh' hoặc 'Song ngữ'. Nếu không xác định được thì ghi 'Không có thông tin cụ thể'."
    )
    source_file: str = Field(
        default=DEFAULT_MISSING_VALUE,
        description="Tên file CV gốc."
    )

    @model_validator(mode="before")
    @classmethod
    def clean_missing_and_normalize(cls, data: Any) -> Any:
        """
        Duyệt qua tất cả các trường để:
        1. Thay thế giá trị None, rỗng, khoảng trắng, 'N/A', 'null' bằng DEFAULT_MISSING_VALUE.
        2. Chuẩn hóa các trường phân loại (Giới tính, Học vấn, Ngôn ngữ CV).
        """
        if not isinstance(data, dict):
            return data

        cleaned = {}
        for k, v in data.items():
            if v is None:
                cleaned[k] = DEFAULT_MISSING_VALUE
            elif isinstance(v, str):
                v_strip = v.strip()
                if not v_strip or v_strip.lower() in ["none", "null", "n/a", "na", "unknown", "không rõ", "không có"]:
                    cleaned[k] = DEFAULT_MISSING_VALUE
                else:
                    cleaned[k] = v_strip
            elif isinstance(v, list):
                # Nếu LLM trả về danh sách, chuyển thành chuỗi ngăn cách bởi dấu phẩy hoặc chấm phẩy
                if not v:
                    cleaned[k] = DEFAULT_MISSING_VALUE
                else:
                    cleaned[k] = "; ".join(str(item).strip() for item in v if item)
            else:
                cleaned[k] = str(v).strip()

        # Chuẩn hóa Giới tính
        gender_raw = str(cleaned.get("gender", "")).lower()
        if gender_raw in ["male", "nam", "m"]:
            cleaned["gender"] = "Nam"
        elif gender_raw in ["female", "nữ", "nu", "f"]:
            cleaned["gender"] = "Nữ"

        # Chuẩn hóa Ngôn ngữ CV
        lang_raw = str(cleaned.get("cv_language", "")).lower()
        if any(x in lang_raw for x in ["việt", "vietnamese", "tiếng việt"]):
            cleaned["cv_language"] = "Tiếng Việt"
        elif any(x in lang_raw for x in ["anh", "english", "tiếng anh"]):
            cleaned["cv_language"] = "Tiếng Anh"
        elif any(x in lang_raw for x in ["bilingual", "song ngữ", "song ngu"]):
            cleaned["cv_language"] = "Song ngữ"

        # Chuẩn hóa Trình độ học vấn phổ biến
        degree_raw = str(cleaned.get("highest_degree", "")).lower()
        if "bachelor" in degree_raw or "cử nhân" in degree_raw or "đại học" in degree_raw:
            cleaned["highest_degree"] = "Đại học"
        elif "master" in degree_raw or "thạc sĩ" in degree_raw:
            cleaned["highest_degree"] = "Thạc sĩ"
        elif "phd" in degree_raw or "doctor" in degree_raw or "tiến sĩ" in degree_raw:
            cleaned["highest_degree"] = "Tiến sĩ"
        elif "college" in degree_raw or "cao đẳng" in degree_raw:
            cleaned["highest_degree"] = "Cao đẳng"
        elif "engineer" in degree_raw or "kỹ sư" in degree_raw:
            cleaned["highest_degree"] = "Kỹ sư"

        return cleaned

    def to_vietnamese_dict(self) -> Dict[str, str]:
        """Chuyển đổi thành từ điển có key là tên cột Tiếng Việt cho Excel/Dashboard."""
        raw_dict = self.model_dump()
        return {
            vietnamese_name: raw_dict.get(field_key, DEFAULT_MISSING_VALUE)
            for field_key, vietnamese_name in FIELD_MAPPING.items()
        }


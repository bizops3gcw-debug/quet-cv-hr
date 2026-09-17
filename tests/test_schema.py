import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.schema import ResumeData, FIELD_MAPPING, VIETNAMESE_COLUMNS
from config import DEFAULT_MISSING_VALUE


def test_missing_fields_default_value():
    """Kiểm tra: Bất kỳ trường nào không có dữ liệu đều trả về 'Không có thông tin cụ thể'."""
    data = {
        "full_name": "Nguyễn Văn A",
        "phone": None,
        "email": "",
        "address": "   ",
        "hard_skills": "N/A",
        "soft_skills": "null",
    }
    resume = ResumeData.model_validate(data)

    assert resume.full_name == "Nguyễn Văn A"
    assert resume.phone == DEFAULT_MISSING_VALUE
    assert resume.email == DEFAULT_MISSING_VALUE
    assert resume.address == DEFAULT_MISSING_VALUE
    assert resume.hard_skills == DEFAULT_MISSING_VALUE
    assert resume.soft_skills == DEFAULT_MISSING_VALUE
    assert resume.target_position == DEFAULT_MISSING_VALUE
    assert resume.expected_salary == DEFAULT_MISSING_VALUE


def test_normalization_gender_and_degree():
    """Kiểm tra: Chuẩn hóa các trường phân loại (Giới tính, Học vấn, Ngôn ngữ)."""
    data = {
        "full_name": "John Doe",
        "gender": "Male",
        "highest_degree": "Bachelor of Computer Science",
        "cv_language": "English",
    }
    resume = ResumeData.model_validate(data)

    assert resume.gender == "Nam"
    assert resume.highest_degree == "Đại học"
    assert resume.cv_language == "Tiếng Anh"


def test_vietnamese_dict_mapping():
    """Kiểm tra: Ánh xạ đầy đủ các cột Tiếng Việt cho Excel."""
    resume = ResumeData(full_name="Trần Thị B", target_position="Kế toán trưởng")
    vn_dict = resume.to_vietnamese_dict()

    assert "Họ và tên" in vn_dict
    assert vn_dict["Họ và tên"] == "Trần Thị B"
    assert "Vị trí ứng tuyển / Chức danh" in vn_dict
    assert vn_dict["Vị trí ứng tuyển / Chức danh"] == "Kế toán trưởng"
    assert vn_dict["Mức lương mong muốn"] == DEFAULT_MISSING_VALUE
    assert len(vn_dict) == len(VIETNAMESE_COLUMNS)


if __name__ == "__main__":
    test_missing_fields_default_value()
    test_normalization_gender_and_degree()
    test_vietnamese_dict_mapping()
    print(" Tất cả các bài kiểm tra Schema đã vượt qua thành công!")

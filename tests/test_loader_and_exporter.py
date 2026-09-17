import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from models.schema import ResumeData
from core.document_loader import DocumentLoader, cleanup_temp_files
from core.exporter import Exporter


def test_image_compression_and_loader():
    """Kiểm tra: Nạp ảnh và thuật toán nén ảnh kích thước lớn."""
    # Tạo một ảnh giả lập kích thước lớn (2400x3200 RGBA)
    large_img = Image.new("RGBA", (2400, 3200), color=(255, 100, 100, 255))
    buf = io.BytesIO()
    large_img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    loader = DocumentLoader()
    images, text = loader.load_document(img_bytes, "test_cv.png")

    assert len(images) == 1
    compressed = images[0]
    # Kích thước chiều lớn nhất không được vượt quá MAX_IMAGE_DIMENSION (1800)
    assert max(compressed.size) <= 1800
    assert compressed.mode == "RGB"
    print(f"Ảnh đã được nén từ (2400, 3200) thành công: {compressed.size}")


def test_exporter_excel_and_csv():
    """Kiểm tra: Xuất bảng Excel và CSV với tiếng Việt có dấu chuẩn xác."""
    sample_resumes = [
        ResumeData(
            full_name="Nguyễn Văn A",
            target_position="Lập trình viên Backend",
            phone="0987654321",
            email="nguyenvana@gmail.com",
            hard_skills="Python, Docker, PostgreSQL",
            years_of_experience="3 năm",
            cv_language="Tiếng Việt",
            source_file="NguyenVanA_CV.pdf",
        ),
        ResumeData(
            full_name="John Smith",
            target_position="Data Scientist",
            phone="Không có thông tin cụ thể",
            gender="Nam",
            hard_skills="Machine Learning, PyTorch",
            cv_language="Tiếng Anh",
            source_file="JohnSmith_CV.pdf",
        ),
    ]

    # Kiểm tra xuất Excel bytes
    excel_bytes = Exporter.export_excel(sample_resumes)
    assert len(excel_bytes) > 0
    assert excel_bytes.startswith(b"PK")  # ZIP header của file xlsx

    # Kiểm tra xuất CSV bytes
    csv_bytes = Exporter.export_csv(sample_resumes)
    assert len(csv_bytes) > 0
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "Họ và tên" in csv_text
    assert "Nguyễn Văn A" in csv_text
    assert "Lập trình viên Backend" in csv_text

    # Kiểm tra xuất JSON
    json_str = Exporter.export_json(sample_resumes)
    assert "John Smith" in json_str

    print(" Tất cả các bài kiểm tra Exporter và DocumentLoader đã vượt qua thành công!")


if __name__ == "__main__":
    test_image_compression_and_loader()
    test_exporter_excel_and_csv()

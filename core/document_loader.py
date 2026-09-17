import os
import io
import shutil
from pathlib import Path
from typing import List, Tuple, Union, Optional
from PIL import Image

from config import (
    TEMP_DIR,
    MAX_IMAGE_DIMENSION,
    JPEG_QUALITY,
    SUPPORTED_EXTENSIONS,
)

# Thử import pymupdf và docx
try:
    import pymupdf as fitz
    HAS_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAS_PYMUPDF = True
    except ImportError:
        HAS_PYMUPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class DocumentLoader:
    """
    Bộ nạp và tiền xử lý tài liệu CV:
    - Hỗ trợ định dạng PDF, DOCX, Ảnh (PNG, JPG, JPEG, WEBP).
    - Tự động nén và tối ưu hóa độ phân giải hình ảnh/PDF scan để tiết kiệm token và tăng tốc độ xử lý.
    - Bảo đảm an toàn dữ liệu cá nhân (PII) với cơ chế quản lý tệp tạm.
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def load_document(self, file_path_or_bytes: Union[str, Path, bytes], filename: str) -> Tuple[List[Image.Image], str]:
        """
        Nạp tài liệu từ đường dẫn hoặc byte stream:
        Trả về:
            - List[Image.Image]: Danh sách các trang đã được nén tối ưu (cho Vision AI đọc layout/ảnh).
            - str: Nội dung văn bản số trích xuất được (nếu là DOCX hoặc PDF digital).
        """
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Định dạng tệp '{ext}' không được hỗ trợ. Các định dạng hợp lệ: {SUPPORTED_EXTENSIONS}")

        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                file_bytes = f.read()
        else:
            file_bytes = file_path_or_bytes

        if ext == ".pdf":
            return self._load_pdf(file_bytes)
        elif ext in [".docx", ".doc"]:
            return self._load_docx(file_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            return self._load_image(file_bytes)
        else:
            raise ValueError(f"Không thể xử lý định dạng: {ext}")

    def _load_pdf(self, file_bytes: bytes) -> Tuple[List[Image.Image], str]:
        """Xử lý file PDF: Render các trang thành ảnh nén và trích xuất text số nếu có."""
        images = []
        extracted_text = ""

        if HAS_PYMUPDF:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text_parts = []
            
            # Chỉ lấy tối đa 5 trang đầu tiên (thông thường CV chỉ 1-3 trang)
            max_pages = min(len(doc), 5)
            for page_idx in range(max_pages):
                page = doc[page_idx]
                text_parts.append(page.get_text())

                # Render trang thành ảnh với độ phân giải tiêu chuẩn (DPI ~ 150)
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                compressed_img = self._compress_image(img)
                images.append(compressed_img)

            doc.close()
            extracted_text = "\n".join(text_parts).strip()
        else:
            # Trường hợp chưa có PyMuPDF, mở bằng PIL (chỉ hỗ trợ nếu là single frame hoặc thư viện phụ)
            raise RuntimeError("Thư viện 'pymupdf' chưa được cài đặt để đọc file PDF.")

        return images, extracted_text

    def _load_docx(self, file_bytes: bytes) -> Tuple[List[Image.Image], str]:
        """Xử lý file Word DOCX: Trích xuất các đoạn văn và bảng biểu."""
        if not HAS_DOCX:
            raise RuntimeError("Thư viện 'python-docx' chưa được cài đặt để đọc file Word.")

        doc_io = io.BytesIO(file_bytes)
        doc = docx.Document(doc_io)
        
        text_parts = []
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_parts.append(" | ".join(row_text))

        extracted_text = "\n".join(text_parts)
        # DOCX là văn bản thuần, không cần danh sách ảnh trang
        return [], extracted_text

    def _load_image(self, file_bytes: bytes) -> Tuple[List[Image.Image], str]:
        """Xử lý tệp hình ảnh trực tiếp (PNG, JPG, WEBP)."""
        img = Image.open(io.BytesIO(file_bytes))
        compressed_img = self._compress_image(img)
        return [compressed_img], ""

    def _compress_image(self, img: Image.Image) -> Image.Image:
        """
        Tối ưu hóa dung lượng & nén ảnh:
        - Chuyển hệ màu RGBA -> RGB với nền trắng.
        - Resize nếu kích thước vượt quá MAX_IMAGE_DIMENSION.
        - Nén JPEG chất lượng JPEG_QUALITY (85%).
        """
        # Chuyển đổi RGBA sang RGB nếu cần
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize tỷ lệ nếu ảnh quá lớn
        width, height = img.size
        max_dim = max(width, height)
        if max_dim > MAX_IMAGE_DIMENSION:
            scale = MAX_IMAGE_DIMENSION / float(max_dim)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Nén JPEG in-memory
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        buffer.seek(0)
        return Image.open(buffer)


def cleanup_temp_files(temp_dir: Optional[Path] = None):
    """
    Xóa sạch thư mục tạm thời để bảo vệ quyền riêng tư dữ liệu cá nhân (PII).
    Được gọi ngay sau khi quét xong hoặc khi đóng phiên làm việc.
    """
    target_dir = Path(temp_dir) if temp_dir else TEMP_DIR
    if target_dir.exists():
        for item in target_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception:
                pass

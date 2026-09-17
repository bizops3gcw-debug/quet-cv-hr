import hashlib
import re
from typing import List, Tuple, Set, Dict, Optional
from pathlib import Path
import pandas as pd

from models.schema import ResumeData, FIELD_MAPPING, VIETNAMESE_COLUMNS
from config import DEFAULT_MISSING_VALUE

REVERSE_FIELD_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}


def normalize_phone(phone_str: str) -> str:
    """Chuẩn hóa số điện thoại chỉ giữ lại các chữ số."""
    if not phone_str or phone_str == DEFAULT_MISSING_VALUE:
        return ""
    digits = re.sub(r"\D", "", phone_str)
    if digits.startswith("84") and len(digits) >= 10:
        digits = "0" + digits[2:]
    return digits


def normalize_email(email_str: str) -> str:
    """Chuẩn hóa email về chữ thường."""
    if not email_str or email_str == DEFAULT_MISSING_VALUE:
        return ""
    return email_str.strip().lower()


def compute_file_hash(file_bytes: bytes) -> str:
    """Tính mã băm SHA-256 của tệp để nhận diện nội dung tệp duy nhất."""
    return hashlib.sha256(file_bytes).hexdigest()


class Deduplicator:
    """
    Bộ xử lý chống trùng lặp và đồng bộ dữ liệu bền vững:
    1. Chống quét lại tệp cũ (File-level deduplication).
    2. Chống trùng lặp hồ sơ ứng viên (Identity-level deduplication theo SĐT, Email, Tên).
    3. Đảm bảo dữ liệu trong file Excel luôn được tích lũy (không bị mất khi xóa tệp tải lên).
    """

    @staticmethod
    def load_existing_from_excel(excel_path: str = "ket_qua_quet_cv.xlsx") -> List[ResumeData]:
        """Đọc danh sách ứng viên đã lưu trong file Excel bền vững."""
        path = Path(excel_path)
        if not path.exists():
            return []

        try:
            df = pd.read_excel(path, dtype=str)
            resumes = []
            for _, row in df.iterrows():
                row_dict = {}
                for col_name, val in row.items():
                    if col_name in REVERSE_FIELD_MAPPING:
                        field_key = REVERSE_FIELD_MAPPING[col_name]
                        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
                            row_dict[field_key] = DEFAULT_MISSING_VALUE
                        else:
                            val_str = str(val).strip()
                            # Chuẩn hóa nếu SĐT bị mất số 0 ở đầu do Excel
                            if field_key == "phone" and val_str.isdigit() and len(val_str) == 9:
                                val_str = "0" + val_str
                            row_dict[field_key] = val_str

                if row_dict.get("full_name") and row_dict["full_name"] != DEFAULT_MISSING_VALUE:
                    resumes.append(ResumeData.model_validate(row_dict))

            # Tự động loại bỏ trùng lặp nếu trong file đã có sẵn bản ghi trùng
            deduped_resumes, _ = Deduplicator.deduplicate_resumes(resumes)
            return deduped_resumes
        except Exception as e:
            print(f"Lỗi khi nạp dữ liệu từ {excel_path}: {e}")
            return []

    @staticmethod
    def filter_unscanned_files(
        uploaded_files: List[Tuple[str, bytes]],
        existing_resumes: List[ResumeData],
    ) -> Tuple[List[Tuple[str, bytes]], List[str]]:
        """
        Lọc ra các tệp THỰC SỰ MỚI cần quét, bỏ qua các tệp đã được quét trong hệ thống.
        Trả về: (danh sách file mới, danh sách tên file bị bỏ qua vì đã quét)
        """
        # Tập hợp tên file đã quét
        scanned_filenames = {r.source_file.strip().lower() for r in existing_resumes if r.source_file}

        new_files = []
        skipped_files = []

        for fname, fbytes in uploaded_files:
            clean_name = fname.strip().lower()
            if clean_name in scanned_filenames:
                skipped_files.append(fname)
            else:
                new_files.append((fname, fbytes))

        return new_files, skipped_files

    @staticmethod
    def is_candidate_duplicate(candidate: ResumeData, existing_list: List[ResumeData]) -> Tuple[bool, str]:
        """
        Kiểm tra xem ứng viên mới có bị trùng lặp với ứng viên nào đã có trong danh sách hay không.
        Tiêu chí kiểm tra:
        1. Trùng Email (nếu có email cụ thể)
        2. Trùng Số điện thoại (nếu có SĐT cụ thể)
        3. Trùng cả Họ tên + Vị trí (khi cả SĐT và Email đều thiếu)
        """
        cand_email = normalize_email(candidate.email)
        cand_phone = normalize_phone(candidate.phone)
        cand_name = candidate.full_name.strip().lower()

        for idx, exist in enumerate(existing_list):
            exist_email = normalize_email(exist.email)
            exist_phone = normalize_phone(exist.phone)
            exist_name = exist.full_name.strip().lower()

            # 1. Trùng Email
            if cand_email and exist_email and cand_email == exist_email:
                return True, f"Trùng Email ({candidate.email}) với ứng viên '{exist.full_name}'"

            # 2. Trùng Số điện thoại
            if cand_phone and exist_phone and cand_phone == exist_phone:
                return True, f"Trùng Số điện thoại ({candidate.phone}) với ứng viên '{exist.full_name}'"

            # 3. Trùng Tên và file giống nhau
            if cand_name == exist_name and cand_name != DEFAULT_MISSING_VALUE.lower():
                if candidate.source_file.strip().lower() == exist.source_file.strip().lower():
                    return True, f"Trùng tên '{candidate.full_name}' và cùng tên tệp '{candidate.source_file}'"

        return False, ""

    @staticmethod
    def deduplicate_resumes(resumes: List[ResumeData]) -> Tuple[List[ResumeData], int]:
        """
        Duyệt và loại bỏ các bản ghi trùng lặp trong một danh sách ResumeData, giữ lại bản ghi đầu tiên.
        Trả về: (danh sách đã lọc sạch, số lượng bản ghi trùng đã loại bỏ)
        """
        unique_resumes: List[ResumeData] = []
        duplicate_count = 0

        for r in resumes:
            is_dup, reason = Deduplicator.is_candidate_duplicate(r, unique_resumes)
            if is_dup:
                duplicate_count += 1
            else:
                unique_resumes.append(r)

        return unique_resumes, duplicate_count


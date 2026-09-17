import io
import json
from typing import List, Dict, Any, Union
from pathlib import Path

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from models.schema import ResumeData, FIELD_MAPPING, VIETNAMESE_COLUMNS


class Exporter:
    """
    Bộ xuất dữ liệu ra các định dạng bảng tính:
    - Excel (.xlsx) với định dạng chuyên nghiệp, tự động căn cột, bọc văn bản và tô màu tiêu đề.
    - CSV chuẩn UTF-8-sig (hỗ trợ hiển thị tiếng Việt trên mọi phiên bản Excel không bị lỗi font).
    - JSON chuẩn hóa.
    """

    @staticmethod
    def to_dataframe(resumes: List[ResumeData]) -> pd.DataFrame:
        """Chuyển danh sách ResumeData thành DataFrame với tiêu đề cột Tiếng Việt."""
        records = [r.to_vietnamese_dict() for r in resumes]
        if not records:
            return pd.DataFrame(columns=VIETNAMESE_COLUMNS)
        df = pd.DataFrame(records)
        # Đảm bảo thứ tự cột theo đúng VIETNAMESE_COLUMNS
        existing_cols = [c for c in VIETNAMESE_COLUMNS if c in df.columns]
        return df[existing_cols]

    @staticmethod
    def export_excel(resumes: List[ResumeData], output_path: Union[str, Path, None] = None) -> bytes:
        """
        Xuất dữ liệu ra file Excel với định dạng đẹp mắt.
        Nếu output_path là None, trả về bytes trong bộ nhớ.
        """
        df = Exporter.to_dataframe(resumes)
        output_stream = io.BytesIO()

        # Tạo file Excel bằng openpyxl engine
        with pd.ExcelWriter(output_stream, engine="openpyxl") as writer:
            sheet_name = "Danh_Sach_Ung_Vien"
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]

            # Định dạng cho dòng Header
            header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Viền ô mỏng
            thin_border = Border(
                left=Side(style="thin", color="D9D9D9"),
                right=Side(style="thin", color="D9D9D9"),
                top=Side(style="thin", color="D9D9D9"),
                bottom=Side(style="thin", color="D9D9D9"),
            )

            # Định dạng cho ô dữ liệu
            data_font = Font(name="Segoe UI", size=10)
            data_align_left = Alignment(horizontal="left", vertical="top", wrap_text=True)
            data_align_center = Alignment(horizontal="center", vertical="top")

            # Áp dụng style cho Header
            worksheet.row_dimensions[1].height = 35
            for col_idx, cell in enumerate(worksheet[1], start=1):
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = thin_border

            # Áp dụng style cho các ô dữ liệu (Để chiều cao tự động co giãn theo độ dài văn bản)
            for row_idx in range(2, worksheet.max_row + 1):
                # Không gán chiều cao cố định để Excel tự động giãn dòng theo nội dung
                for col_idx in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    cell.font = data_font
                    cell.border = thin_border
                    
                    # Căn giữa cho các trường ngắn
                    col_name = df.columns[col_idx - 1]
                    if col_name in ["Số điện thoại", "Giới tính", "Ngày / Năm sinh", "Ngôn ngữ của CV", "Tổng số năm kinh nghiệm", "Điểm GPA", "Năm tốt nghiệp (Dự kiến)"]:
                        cell.alignment = data_align_center
                    else:
                        cell.alignment = data_align_left

            # Tự động điều chỉnh độ rộng cột
            for col_idx, col in enumerate(worksheet.columns, start=1):
                max_len = 0
                col_letter = get_column_letter(col_idx)
                for cell in col:
                    val_str = str(cell.value or "")
                    # Nếu là dòng header
                    if cell.row == 1:
                        max_len = max(max_len, len(val_str) + 4)
                    else:
                        # Với nội dung nhiều dòng, lấy độ dài dòng đầu tiên
                        first_line = val_str.split("\n")[0]
                        max_len = max(max_len, min(len(first_line), 40))

                # Giới hạn độ rộng cột từ 15 đến 50 ký tự
                col_width = max(15, min(max_len + 2, 50))
                worksheet.column_dimensions[col_letter].width = col_width

            # Đóng băng dòng tiêu đề (Freeze pane)
            worksheet.freeze_panes = "B2"

        excel_bytes = output_stream.getvalue()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(excel_bytes)

        return excel_bytes

    @staticmethod
    def export_csv(resumes: List[ResumeData], output_path: Union[str, Path, None] = None) -> bytes:
        """Xuất CSV với mã hóa UTF-8 with BOM (utf-8-sig) chống lỗi font tiếng Việt."""
        df = Exporter.to_dataframe(resumes)
        csv_str = df.to_csv(index=False, encoding="utf-8-sig")
        csv_bytes = csv_str.encode("utf-8-sig")

        if output_path:
            with open(output_path, "wb") as f:
                f.write(csv_bytes)

        return csv_bytes

    @staticmethod
    def export_json(resumes: List[ResumeData], output_path: Union[str, Path, None] = None) -> str:
        """Xuất JSON dạng danh sách bản ghi chuẩn hóa."""
        records = [r.model_dump() for r in resumes]
        json_str = json.dumps(records, ensure_ascii=False, indent=2)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)

        return json_str


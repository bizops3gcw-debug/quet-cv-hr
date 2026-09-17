import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Đảm bảo in Tiếng Việt & Emoji chuẩn UTF-8 trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Tải biến môi trường
load_dotenv()

from config import (
    DEFAULT_MODEL_NAME,
    FALLBACK_MODEL_NAME,
    SUPPORTED_EXTENSIONS,
    get_api_key,
    get_google_sheet_webhook_url,
)
from core.google_sheets import GoogleSheetClient
from models.schema import ResumeData, VIETNAMESE_COLUMNS
from core.document_loader import DocumentLoader
from core.extractor import ResumeExtractor
from core.batch_processor import BatchProcessor
from core.exporter import Exporter
from core.deduplicator import Deduplicator


def main():
    parser = argparse.ArgumentParser(description="Quét CV và xuất dữ liệu trực tiếp vào Sheet (Excel/CSV)")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="input_cvs",
        help="Thư mục chứa các tệp CV cần quét (mặc định: input_cvs)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Gemini API Key (nếu không nhập sẽ lấy từ file .env hoặc hỏi trực tiếp)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Dịch tóm tắt phần mô tả sang Tiếng Việt (mặc định: giữ nguyên ngôn ngữ gốc)",
    )
    parser.add_argument(
        "--output-excel",
        type=str,
        default="ket_qua_quet_cv.xlsx",
        help="Tên file Excel xuất ra (mặc định: ket_qua_quet_cv.xlsx)",
    )

    args = parser.parse_args()

    # 1. Xác định API Key
    api_key = args.api_key or get_api_key()
    if not api_key:
        print("=" * 60)
        print(" CHƯA TÌM THẤY GEMINI API KEY!")
        print("Bạn có thể lấy API Key miễn phí tại: https://aistudio.google.com/app/apikey")
        print("=" * 60)
        api_key = input("👉 Nhập Gemini API Key của bạn vào đây: ").strip()
        if not api_key:
            print("❌ Lỗi: Cần có API Key để quét và trích xuất dữ liệu qua AI Vision.")
            sys.exit(1)
        
        # Lưu vào .env để các lần sau không cần nhập lại
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nGEMINI_API_KEY={api_key}\n")
        print(" Đã lưu API Key vào file .env cho các lần chạy tiếp theo!\n")

    # 2. Tìm kiếm các file CV trong thư mục đầu vào
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"❌ Thư mục '{args.input_dir}' không tồn tại. Đang tạo mới...")
        input_path.mkdir(parents=True, exist_ok=True)
        print(f"👉 Vui lòng copy các file CV (PDF, DOCX, Ảnh) vào thư mục '{args.input_dir}' rồi chạy lại lệnh.")
        sys.exit(0)

    cv_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not cv_files:
        print(f"⚠️ Không tìm thấy file CV nào trong thư mục '{args.input_dir}'.")
        print(f"Các định dạng được hỗ trợ: {SUPPORTED_EXTENSIONS}")
        sys.exit(0)

    # 3. Nạp danh sách đã quét từ trước để chống quét lại và bảo toàn dữ liệu
    excel_path = Path(args.output_excel)
    existing_resumes = Deduplicator.load_existing_from_excel(str(excel_path))
    print(f"📊 Đang có sẵn {len(existing_resumes)} ứng viên đã lưu trong file '{args.output_excel}'.")

    files_data = []
    for f in cv_files:
        with open(f, "rb") as file_obj:
            files_data.append((f.name, file_obj.read()))

    new_files, skipped_files = Deduplicator.filter_unscanned_files(files_data, existing_resumes)

    if skipped_files:
        print(f"⚡ Đã bỏ qua {len(skipped_files)} tệp đã quét trước đó (tiết kiệm thời gian):")
        for sf in skipped_files:
            print(f"   - [Bỏ qua] {sf}")

    if not new_files:
        print("\n Tất cả các tệp CV trong thư mục đều đã được quét trước đó. Không có tệp mới cần quét!")
        resumes = existing_resumes
    else:
        print(f"\n🚀 Bắt đầu quét {len(new_files)} tệp mới bằng Gemini Vision AI...\n")
        loader = DocumentLoader()
        extractor = ResumeExtractor(api_key=api_key, model_name=DEFAULT_MODEL_NAME)
        processor = BatchProcessor(extractor=extractor, document_loader=loader)

        def print_progress(current, total, filename, msg):
            print(f"[{current}/{total}] {msg}")

        scanned_resumes = processor.process_batch(
            files=new_files,
            translate_to_vietnamese=args.translate,
            progress_callback=print_progress,
        )

        # Chống trùng lặp ứng viên trước khi gộp vào danh sách
        added_count = 0
        resumes = list(existing_resumes)
        for r in scanned_resumes:
            is_dup, reason = Deduplicator.is_candidate_duplicate(r, resumes)
            if is_dup:
                print(f"⚠️ Bỏ qua ứng viên trùng lặp: {r.full_name} ({reason})")
            else:
                resumes.append(r)
                added_count += 1

        print(f"\n💾 Đã thêm thành công {added_count} ứng viên mới vào bảng tính Excel...")
        Exporter.export_excel(resumes, output_path=excel_path)

        # Tự động đồng bộ lên Google Sheet nếu có Webhook URL
        webhook_url = get_google_sheet_webhook_url()
        if webhook_url and added_count > 0:
            print("\n☁️ Đang đồng bộ ứng viên mới lên Google Sheets...")
            gs_client = GoogleSheetClient(webhook_url)
            new_candidates = [r for r in scanned_resumes if not any(d.full_name == r.full_name for d in existing_resumes)]
            sync_res = gs_client.sync_resumes(new_candidates)
            if sync_res.get("status") == "success":
                print(f" Đã đẩy thành công {sync_res.get('added', 0)} ứng viên mới vào Google Sheet!")
            else:
                print(f"⚠️ Không thể đồng bộ Google Sheet: {sync_res.get('message')}")

    print("=" * 60)
    print("🎉 HOÀN THÀNH QUÉT CV VÀ NẠP DỮ LIỆU THÀNH CÔNG!")
    print(f"👉 File Excel kết quả: {excel_path.resolve()}")
    print("=" * 60)

    # 5. In bảng xem trước kết quả trực tiếp trên Terminal
    df = Exporter.to_dataframe(resumes)
    preview_cols = [
        "Họ và tên",
        "Số điện thoại",
        "Email",
        "Vị trí ứng tuyển / Chức danh",
        "Trình độ học vấn cao nhất",
        "Tổng số năm kinh nghiệm",
        "Ngôn ngữ của CV",
    ]
    existing_preview = [c for c in preview_cols if c in df.columns]
    print("\n📋 BẢNG XEM TRƯỚC KẾT QUẢ TRÍCH XUẤT:")
    print(df[existing_preview].to_string(index=False))
    print(f"\n💡 Bạn có thể mở trực tiếp file '{args.output_excel}' ngay trong thanh Explorer bên trái của VS Code hoặc bằng Microsoft Excel để xem đầy đủ 27 cột dữ liệu!")


if __name__ == "__main__":
    main()


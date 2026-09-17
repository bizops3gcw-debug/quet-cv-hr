import os
import streamlit as st
import pandas as pd
from datetime import datetime

from config import (
    DEFAULT_MISSING_VALUE,
    DEFAULT_MODEL_NAME,
    FALLBACK_MODEL_NAME,
    SUPPORTED_EXTENSIONS,
    get_api_key,
)
from models.schema import ResumeData, VIETNAMESE_COLUMNS
from core.document_loader import DocumentLoader, cleanup_temp_files
from core.extractor import ResumeExtractor
from core.batch_processor import BatchProcessor
from core.exporter import Exporter
from core.deduplicator import Deduplicator
from core.google_sheets import GoogleSheetClient


def get_config_val(key: str, default: str = "") -> str:
    """Đọc cấu hình từ st.secrets (khi deploy Streamlit Cloud) hoặc .env (khi chạy local)."""
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()


# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="Hệ Thống Quét CV Thông Minh",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Khởi tạo Session State và tự động nạp dữ liệu đã lưu từ file Excel ket_qua_quet_cv.xlsx
if "resumes" not in st.session_state:
    st.session_state.resumes = Deduplicator.load_existing_from_excel("ket_qua_quet_cv.xlsx")
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []


def main():
    # --- THANH BÊN (SIDEBAR) ---
    with st.sidebar:
        st.title("⚙️ Cấu Hình Hệ Thống")
        st.markdown("---")

        # Cấu hình API Key (Cloud & Local)
        env_key = get_config_val("GEMINI_API_KEY", get_api_key())
        api_key_input = st.text_input(
            "🔑 Gemini API Key:",
            value=env_key,
            type="password",
            help="Lấy API Key miễn phí tại: https://aistudio.google.com/app/apikey",
        )
        if not api_key_input:
            st.warning("⚠️ Vui lòng nhập Gemini API Key để bắt đầu quét CV.")
            st.markdown("[👉 Bấm vào đây để lấy API Key miễn phí](https://aistudio.google.com/app/apikey)")
        else:
            st.success(" Đã nhận diện API Key")

        # Cấu hình Google Sheets Webhook
        st.markdown("---")
        st.subheader("📊 Đồng Bộ Google Sheets")
        env_webhook = get_config_val("GOOGLE_SHEET_WEBHOOK_URL", "")
        webhook_input = st.text_input(
            "🔗 Google Sheets Webhook URL:",
            value=env_webhook,
            type="password",
            help="Dán URL Webhook Apps Script từ Google Sheet của bạn để tự động lưu dữ liệu lên đám mây.",
        )
        if webhook_input:
            gs_client = GoogleSheetClient(webhook_input)
            if st.button("🔌 Kiểm tra kết nối Google Sheet"):
                with st.spinner("Đang kết nối tới Google Sheet..."):
                    ok, msg = gs_client.test_connection()
                    if ok:
                        st.success(f" {msg}")
                    else:
                        st.error(f"❌ {msg}")

        # Lựa chọn mô hình
        model_options = ["gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-flash-latest"]
        selected_model = st.selectbox(
            "🤖 Mô hình AI:",
            options=model_options,
            index=0 if DEFAULT_MODEL_NAME in model_options else 0,
            help="Gemini Flash có tốc độ quét cực nhanh và tối ưu chi phí.",
        )

        st.markdown("---")
        st.subheader("🌐 Tùy Chọn Đa Ngôn Ngữ")
        translate_option = st.checkbox(
            "Dịch tóm tắt sang Tiếng Việt",
            value=False,
            help="Nếu bật, các phần mô tả công việc/kỹ năng trong CV tiếng Anh sẽ được dịch tóm tắt sang tiếng Việt. Mặc định giữ nguyên thuật ngữ chuyên môn gốc.",
        )

        st.markdown("---")
        st.subheader("🔒 Bảo Mật & Quyền Riêng Tư")
        st.info("Hệ thống tự động xóa toàn bộ các tệp tạm (temp files) ngay sau khi quét xong để bảo vệ thông tin cá nhân (PII).")

        if st.button("🗑️ Xóa dữ liệu hiện tại (Reset)"):
            st.session_state.resumes = []
            cleanup_temp_files()
            st.rerun()

    # --- KHU VỰC NỘI DUNG CHÍNH ---
    st.title("📄 Hệ Thống Quét CV & Bóc Tách Hồ Sơ Hàng Loạt")
    st.caption("Giải pháp trích xuất tự động dữ liệu ứng viên từ mọi bố cục CV (Canva, TopCV, scan, ảnh, văn bản).")

    # Các thẻ thông số nhanh (Metrics)
    col1, col2, col3, col4 = st.columns(4)
    total_scanned = len(st.session_state.resumes)
    vn_cvs = sum(1 for r in st.session_state.resumes if r.cv_language == "Tiếng Việt")
    en_cvs = sum(1 for r in st.session_state.resumes if r.cv_language == "Tiếng Anh")
    other_cvs = total_scanned - vn_cvs - en_cvs

    with col1:
        st.metric("Tổng số CV đã quét", total_scanned)
    with col2:
        st.metric("CV Tiếng Việt", vn_cvs)
    with col3:
        st.metric("CV Tiếng Anh", en_cvs)
    with col4:
        st.metric("CV Song ngữ / Khác", other_cvs)

    st.markdown("---")

    # Tạo 3 Tabs chức năng
    tab1, tab2, tab3 = st.tabs([
        "📤 1. Tải Lên & Quét Hàng Loạt",
        "📊 2. Bảng Dữ Liệu Ứng Viên",
        "🔍 3. Chi Tiết Từng Hồ Sơ",
    ])

    # ==========================================
    # TAB 1: TẢI LÊN & QUÉT CV HÀNG LOẠT
    # ==========================================
    with tab1:
        st.subheader("Tải lên hồ sơ ứng viên (Hỗ trợ PDF, Word DOCX, Ảnh PNG/JPG)")
        st.caption("🛡️ **Bảo toàn dữ liệu vĩnh viễn:** Toàn bộ hồ sơ đã quét luôn được lưu an toàn trong file `ket_qua_quet_cv.xlsx`. Việc bạn xóa bớt tệp khỏi khung tải lên dưới đây **KHÔNG BAO GIỜ** làm mất dữ liệu đã quét!")

        uploaded_files = st.file_uploader(
            "Chọn một hoặc nhiều tệp CV cùng lúc:",
            type=["pdf", "docx", "png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            help="Kéo thả danh sách tệp CV vào đây để xử lý hàng loạt.",
        )

        # Nếu chưa có API Key ở thanh bên hoặc môi trường, hiển thị ngay trên màn hình chính
        effective_api_key = api_key_input or get_api_key()
        if not effective_api_key:
            st.warning("⚠️ **Bạn chưa nhập Gemini API Key.** Bạn có thể lấy Key miễn phí tại: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)")
            effective_api_key = st.text_input(
                "🔑 Nhập Gemini API Key tại đây:",
                type="password",
                placeholder="Dán API Key (bắt đầu bằng AIzaSy...)",
                key="main_api_key_input"
            )
            if effective_api_key:
                # Lưu vào .env
                with open(".env", "a", encoding="utf-8") as env_file:
                    env_file.write(f"\nGEMINI_API_KEY={effective_api_key.strip()}\n")
                st.success(" Đã lưu API Key vào hệ thống! Vui lòng bấm Quét.")

        if uploaded_files:
            # Đọc danh sách tệp tải lên
            files_data = [(f.name, f.read()) for f in uploaded_files]

            # 1. Cơ chế chống quét lại: Phân loại file mới vs file đã quét
            new_files, skipped_files = Deduplicator.filter_unscanned_files(files_data, st.session_state.resumes)

            if skipped_files:
                st.info(f"⚡ **Đã bỏ qua {len(skipped_files)} tệp đã quét trước đó** (tiết kiệm thời gian & quota API): " + ", ".join(f"`{f}`" for f in skipped_files[:3]) + (f" và {len(skipped_files)-3} tệp khác..." if len(skipped_files) > 3 else ""))

            if new_files:
                st.success(f"✨ Tìm thấy **{len(new_files)} tệp CV mới** cần quét.")
                start_btn = st.button(
                    f"🚀 Bắt đầu Quét {len(new_files)} CV Mới",
                    type="primary",
                    disabled=not effective_api_key
                )

                if start_btn:
                    if not effective_api_key:
                        st.error("Vui lòng nhập API Key trước khi bắt đầu!")
                        return

                    # Khởi tạo các module xử lý
                    loader = DocumentLoader()
                    extractor = ResumeExtractor(api_key=effective_api_key, model_name=selected_model)
                    processor = BatchProcessor(extractor=extractor, document_loader=loader)

                    # Khởi tạo thanh tiến độ
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def on_progress(current, total, filename, msg):
                        progress = current / total
                        progress_bar.progress(progress)
                        status_text.markdown(f"⏳ **{msg}**")

                    with st.spinner(f"Hệ thống đang quét {len(new_files)} hồ sơ mới..."):
                        scanned_resumes = processor.process_batch(
                            files=new_files,
                            translate_to_vietnamese=translate_option,
                            progress_callback=on_progress,
                        )

                    # 2. Cơ chế chống trùng lặp ứng viên (theo SĐT, Email, Tên)
                    added_count = 0
                    duplicate_candidates = []
                    for r in scanned_resumes:
                        is_dup, reason = Deduplicator.is_candidate_duplicate(r, st.session_state.resumes)
                        if is_dup:
                            duplicate_candidates.append(f"{r.full_name} ({reason})")
                        else:
                            st.session_state.resumes.append(r)
                            added_count += 1

                    # Tự động xuất và lưu file Excel tích lũy bền vững
                    Exporter.export_excel(st.session_state.resumes, "ket_qua_quet_cv.xlsx")

                    # 3. Tự động đồng bộ lên Google Sheets nếu đã cấu hình
                    if webhook_input and added_count > 0:
                        with st.spinner("Đang đồng bộ ứng viên mới lên Google Sheets..."):
                            gs_client = GoogleSheetClient(webhook_input)
                            new_valid_resumes = [r for r in scanned_resumes if not any(d in r.full_name for d in duplicate_candidates)]
                            sync_res = gs_client.sync_resumes(new_valid_resumes)
                            if sync_res.get("status") == "success":
                                st.success(f"📊 **Đã đồng bộ tự động {sync_res.get('added', 0)} ứng viên mới vào Google Sheets!**")
                            else:
                                st.warning(f"⚠️ Lỗi đồng bộ Google Sheets: {sync_res.get('message')}")

                    progress_bar.progress(1.0)
                    if duplicate_candidates:
                        st.warning("⚠️ Đã bỏ qua các ứng viên bị trùng lặp: " + "; ".join(duplicate_candidates))
                    
                    status_text.success(f"🎉 Hoàn thành! Đã thêm thành công **{added_count}** ứng viên mới vào hệ thống.")
                    st.balloons()
                    st.info("👉 Bạn hãy chuyển sang **Tab 2: Bảng Dữ Liệu Ứng Viên** để xem bảng tổng hợp hoặc tải file.")
            else:
                st.warning(" Tất cả các tệp bạn đang chọn đều đã được quét trước đó và có sẵn trong bảng dữ liệu. Không cần quét lại!")

    # ==========================================
    # TAB 2: BẢNG DỮ LIỆU ỨNG VIÊN & XUẤT FILE
    # ==========================================
    with tab2:
        if not st.session_state.resumes:
            st.info("Chưa có dữ liệu. Vui lòng tải tệp lên ở Tab 1 và bấm 'Bắt đầu Quét'.")
        else:
            # Thanh công cụ tiện ích (Đồng bộ Google Sheets & Dọn dẹp trùng)
            tb_col1, tb_col2, tb_col3 = st.columns([2, 2, 4])
            with tb_col1:
                if webhook_input:
                    if st.button("🔄 Tải lại từ Google Sheets"):
                        with st.spinner("Đang tải dữ liệu từ Google Sheets..."):
                            gs_client = GoogleSheetClient(webhook_input)
                            remote_resumes, err = gs_client.fetch_resumes()
                            if err:
                                st.error(f"Lỗi tải từ Google Sheets: {err}")
                            else:
                                # Gộp với dữ liệu hiện tại và loại bỏ trùng
                                merged, removed = Deduplicator.deduplicate_resumes(st.session_state.resumes + remote_resumes)
                                st.session_state.resumes = merged
                                Exporter.export_excel(st.session_state.resumes, "ket_qua_quet_cv.xlsx")
                                st.success(f" Đã đồng bộ {len(remote_resumes)} dòng từ Google Sheets!")
                                st.rerun()

            with tb_col2:
                if st.button("🧹 Quét sạch bản ghi trùng"):
                    clean_resumes, dup_count = Deduplicator.deduplicate_resumes(st.session_state.resumes)
                    st.session_state.resumes = clean_resumes
                    Exporter.export_excel(st.session_state.resumes, "ket_qua_quet_cv.xlsx")
                    st.success(f" Đã loại bỏ {dup_count} bản ghi trùng lặp!")
                    st.rerun()

            df = Exporter.to_dataframe(st.session_state.resumes)

            # Thanh công cụ lọc & tìm kiếm
            col_search, col_filter = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Tìm kiếm theo Tên, Vị trí hoặc Kỹ năng:", "")
            with col_filter:
                lang_filter = st.selectbox(
                    "Lọc theo Ngôn ngữ CV:",
                    options=["Tất cả", "Tiếng Việt", "Tiếng Anh", "Song ngữ"],
                )

            # Áp dụng bộ lọc
            filtered_df = df.copy()
            if lang_filter != "Tất cả":
                filtered_df = filtered_df[filtered_df["Ngôn ngữ của CV"] == lang_filter]
            if search_query:
                q = search_query.lower()
                mask = (
                    filtered_df["Họ và tên"].str.lower().str.contains(q)
                    | filtered_df["Vị trí ứng tuyển / Chức danh"].str.lower().str.contains(q)
                    | filtered_df["Kỹ năng chuyên môn (Hard skills)"].str.lower().str.contains(q)
                )
                filtered_df = filtered_df[mask]

            st.write(f"Hiển thị **{len(filtered_df)} / {len(df)}** ứng viên:")
            st.dataframe(filtered_df, use_container_width=True, height=400)

            # Khu vực tải xuống (Export Center) - Hỗ trợ cả Excel và CSV
            st.markdown("---")
            st.subheader("📥 Tải Báo Cáo Tuyển Dụng")
            
            col_dl1, col_dl2 = st.columns(2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            with col_dl1:
                excel_bytes = Exporter.export_excel(st.session_state.resumes)
                st.download_button(
                    label="📊 Tải Bảng Excel (.xlsx)",
                    data=excel_bytes,
                    file_name=f"ket_qua_quet_cv_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )
            
            with col_dl2:
                csv_bytes = Exporter.export_csv(st.session_state.resumes)
                st.download_button(
                    label="📑 Tải Bảng CSV (.csv chuẩn tiếng Việt)",
                    data=csv_bytes,
                    file_name=f"ket_qua_quet_cv_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    # ==========================================
    # TAB 3: CHI TIẾT TỪNG HỒ SƠ ỨNG VIÊN
    # ==========================================
    with tab3:
        if not st.session_state.resumes:
            st.info("Chưa có hồ sơ nào được quét.")
        else:
            candidate_names = [
                f"{idx + 1}. {r.full_name} - {r.target_position} ({r.source_file})"
                for idx, r in enumerate(st.session_state.resumes)
            ]
            selected_idx = st.selectbox("Chọn ứng viên để xem chi tiết:", range(len(candidate_names)), format_func=lambda i: candidate_names[i])

            resume = st.session_state.resumes[selected_idx]

            # Hiển thị thông tin dạng Card chuyên nghiệp
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"### 👤 {resume.full_name}")
                st.markdown(f"- **Vị trí mục tiêu:** {resume.target_position}")
                st.markdown(f"- **Số điện thoại:** `{resume.phone}`")
                st.markdown(f"- **Email:** `{resume.email}`")
                st.markdown(f"- **Ngày sinh:** {resume.date_of_birth} | **Giới tính:** {resume.gender}")
                st.markdown(f"- **Nơi cư trú:** {resume.address}")
                st.markdown(f"- **Liên kết:** {resume.social_links}")
                st.markdown(f"- **Mức lương kỳ vọng:** {resume.expected_salary}")

            with col_info2:
                st.markdown("### 🎓 Học Vấn & Kinh Nghiệm")
                st.markdown(f"- **Trường:** {resume.university}")
                st.markdown(f"- **Chuyên ngành:** {resume.major}")
                st.markdown(f"- **Điểm GPA:** `{resume.gpa}` | **Năm tốt nghiệp:** `{resume.graduation_year}`")
                st.markdown(f"- **Trình độ cao nhất:** {resume.highest_degree}")
                st.markdown(f"- **Tổng số năm kinh nghiệm:** {resume.years_of_experience}")
                st.markdown(f"- **Ngôn ngữ CV:** `{resume.cv_language}`")
                st.markdown(f"- **Tên file gốc:** `{resume.source_file}`")

            st.markdown("---")

            col_detail1, col_detail2 = st.columns(2)
            with col_detail1:
                with st.expander("💼 Chi tiết Kinh nghiệm làm việc", expanded=True):
                    st.write(resume.work_experience_details)

                with st.expander("📚 Chi tiết Học vấn (Tổng quan)", expanded=True):
                    st.write(resume.education_details)

                with st.expander("🎯 Mục tiêu nghề nghiệp / Giới thiệu", expanded=False):
                    st.write(resume.career_objective)

            with col_detail2:
                with st.expander("🎪 Hoạt động Ngoại khóa & Đoàn hội (Intern Focus)", expanded=True):
                    st.write(resume.extracurricular_activities)

                with st.expander("🛠️ Kỹ năng Chuyên môn (Hard skills)", expanded=True):
                    st.write(resume.hard_skills)

                with st.expander("🤝 Kỹ năng Mềm (Soft skills)", expanded=False):
                    st.write(resume.soft_skills)

                with st.expander("🌐 Ngoại ngữ & Chứng chỉ", expanded=False):
                    st.markdown(f"**Ngoại ngữ:** {resume.languages}")
                    st.markdown(f"**Chứng chỉ:** {resume.certifications}")

                with st.expander("🚀 Dự án & Giải thưởng", expanded=False):
                    st.markdown(f"**Dự án:** {resume.projects}")
                    st.markdown(f"**Giải thưởng:** {resume.awards}")


if __name__ == "__main__":
    main()


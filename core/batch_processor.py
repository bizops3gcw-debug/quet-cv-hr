import time
import logging
from typing import List, Dict, Any, Callable, Optional, Tuple
from pathlib import Path

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from config import (
    MAX_RETRIES,
    MIN_RETRY_WAIT,
    MAX_RETRY_WAIT,
    DEFAULT_MISSING_VALUE,
)
from models.schema import ResumeData
from core.document_loader import DocumentLoader, cleanup_temp_files
from core.extractor import ResumeExtractor

logger = logging.getLogger(__name__)


def is_transient_error(exception: BaseException) -> bool:
    """Kiểm tra xem lỗi có phải do nghẽn mạng hoặc Rate Limit (429 / Quota) để thử lại."""
    err_str = str(exception).lower()
    transient_indicators = [
        "429",
        "quota",
        "resource_exhausted",
        "rate limit",
        "too many requests",
        "timeout",
        "connection",
        "temporary",
    ]
    return any(indicator in err_str for indicator in transient_indicators)


class BatchProcessor:
    """
    Bộ xử lý quét CV hàng loạt:
    - Hỗ trợ cơ chế tự động thử lại (Exponential Backoff) khi gặp lỗi Quota/429.
    - Cách ly lỗi: 1 file hỏng không làm dừng toàn bộ tiến trình.
    - Cập nhật tiến độ theo thời gian thực (Progress callback).
    """

    def __init__(
        self,
        extractor: ResumeExtractor,
        document_loader: Optional[DocumentLoader] = None,
    ):
        self.extractor = extractor
        self.loader = document_loader or DocumentLoader()

    def _create_retry_extract_func(self):
        """Tạo hàm bóc tách được bao bọc bởi tenacity retry decorator."""
        @retry(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=1.5, min=MIN_RETRY_WAIT, max=MAX_RETRY_WAIT),
            retry=retry_if_exception(is_transient_error),
            reraise=True,
        )
        def _extract_with_retry(images, text, filename, translate):
            return self.extractor.extract(
                images=images,
                text_content=text,
                filename=filename,
                translate_to_vietnamese=translate,
            )

        return _extract_with_retry

    def process_file(
        self,
        file_bytes: bytes,
        filename: str,
        translate_to_vietnamese: bool = False,
    ) -> Tuple[ResumeData, Optional[str]]:
        """
        Xử lý bóc tách 1 tệp CV:
        Trả về (ResumeData, error_message)
        """
        try:
            # 1. Nạp và tối ưu hóa tài liệu
            images, text = self.loader.load_document(file_bytes, filename)

            # 2. Bóc tách bằng AI với cơ chế thử lại tự động
            retry_func = self._create_retry_extract_func()
            resume_data = retry_func(images, text, filename, translate_to_vietnamese)
            return resume_data, None

        except Exception as e:
            err_msg = f"Lỗi xử lý file {filename}: {str(e)}"
            logger.error(err_msg)
            # Tạo bản ghi lỗi để bảng kết quả vẫn ghi nhận file
            error_data = ResumeData(
                source_file=filename,
                career_objective=f"Không thể trích xuất do lỗi: {str(e)}",
            )
            return error_data, err_msg

    def process_batch(
        self,
        files: List[Tuple[str, bytes]],
        translate_to_vietnamese: bool = False,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
    ) -> List[ResumeData]:
        """
        Xử lý một danh sách nhiều tệp CV.
        Args:
            files: Danh sách các tuple (filename, file_bytes).
            translate_to_vietnamese: Tùy chọn dịch tóm tắt sang tiếng Việt.
            progress_callback: Hàm callback nhận (current_idx, total, filename, status_text).
        """
        total = len(files)
        results: List[ResumeData] = []

        try:
            for idx, (filename, file_bytes) in enumerate(files, start=1):
                if progress_callback:
                    progress_callback(idx, total, filename, f"Đang quét CV ({idx}/{total}): {filename}...")

                data, error = self.process_file(file_bytes, filename, translate_to_vietnamese)
                results.append(data)

                # Khoảng nghỉ nhỏ 0.3s để giảm áp lực RPM lên API
                time.sleep(0.3)

        finally:
            # Dọn dẹp các tệp tạm để bảo vệ quyền riêng tư (PII)
            cleanup_temp_files()

        return results


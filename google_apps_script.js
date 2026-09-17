/**
 * GOOGLE APPS SCRIPT - WEBHOOK ĐỒNG BỘ DỮ LIỆU QUÉT CV
 * 
 * HƯỚNG DẪN CÀI ĐẶT TRONG 2 PHÚT:
 * 1. Mở tệp Google Sheet bạn muốn lưu dữ liệu.
 * 2. Trên thanh menu, chọn: Tiện ích mở rộng (Extensions) -> Apps Script.
 * 3. Xóa toàn bộ mã cũ và dán toàn bộ đoạn code này vào.
 * 4. Bấm nút "Lưu" (biểu tượng đĩa mềm 💾).
 * 5. Bấm nút "Triển khai" (Deploy) ở góc trên bên phải -> Chọn "Triển khai dưới dạng ứng dụng web mới" (New deployment).
 * 6. Cấu hình triển khai:
 *    - Mô tả: "CV Webhook API"
 *    - Thực thi dưới dạng (Execute as): "Tôi" (Me)
 *    - Ai có quyền truy cập (Who has access): "Bất kỳ ai" (Anyone) -> QUAN TRỌNG!
 * 7. Bấm "Triển khai" -> Cấp quyền truy cập nếu Google hỏi.
 * 8. Copy "URL của ứng dụng web" (Web App URL) và dán vào ứng dụng Quét CV!
 */

// Danh sách 27 cột Tiếng Việt chuẩn (Đã tách riêng Trường, Chuyên ngành, GPA, Năm tốt nghiệp, Hoạt động ngoại khóa)
const HEADERS = [
  "Họ và tên",
  "Số điện thoại",
  "Email",
  "Ngày / Năm sinh",
  "Giới tính",
  "Địa chỉ / Nơi cư trú",
  "Liên kết cá nhân (LinkedIn/GitHub/Portfolio)",
  "Vị trí ứng tuyển / Chức danh",
  "Mục tiêu nghề nghiệp / Tóm tắt",
  "Trình độ học vấn cao nhất",
  "Tên trường Đại học / Cao đẳng",
  "Chuyên ngành đào tạo",
  "Điểm GPA",
  "Năm tốt nghiệp (Dự kiến)",
  "Chi tiết học vấn",
  "Tổng số năm kinh nghiệm",
  "Chi tiết kinh nghiệm làm việc",
  "Kỹ năng chuyên môn (Hard skills)",
  "Kỹ năng mềm (Soft skills)",
  "Ngoại ngữ & Trình độ",
  "Chứng chỉ chuyên môn",
  "Hoạt động ngoại khóa",
  "Dự án tiêu biểu",
  "Giải thưởng / Thành tích",
  "Mức lương mong muốn",
  "Ngôn ngữ của CV",
  "Tên file gốc"
];

function doGet(e) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Tự động chữa lành dòng 1 (Self-Healing Header): Nếu dòng 1 chưa đủ hoặc không khớp 27 cột
    if (sheet.getLastRow() > 0) {
      const currentCols = sheet.getLastColumn();
      const firstRow = sheet.getRange(1, 1, 1, Math.max(currentCols, HEADERS.length)).getValues()[0];
      if (currentCols < HEADERS.length || firstRow[10] !== HEADERS[10]) {
        sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
        formatHeader(sheet);
      }
    }

    const data = sheet.getDataRange().getValues();
    
    if (data.length <= 1) {
      return ContentService.createTextOutput(JSON.stringify({ status: "success", count: 0, data: [] }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    const headers = data[0];
    const rows = [];
    
    for (let i = 1; i < data.length; i++) {
      const rowObj = {};
      for (let j = 0; j < headers.length; j++) {
        rowObj[headers[j]] = data[i][j] !== undefined ? String(data[i][j]) : "";
      }
      rows.push(rowObj);
    }
    
    return ContentService.createTextOutput(JSON.stringify({ status: "success", count: rows.length, data: rows }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    const resumes = payload.resumes || [];
    
    if (!resumes || resumes.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "Không có dữ liệu ứng viên" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const action = payload.action || "append";

    // 1. NẾU LÀ ACTION LÀM MỚI TOÀN BỘ (RESET & SYNC)
    if (action === "reset_and_sync") {
      sheet.clear();
      sheet.appendRow(HEADERS);
      formatHeader(sheet);

      let addedCount = 0;
      for (let i = 0; i < resumes.length; i++) {
        const r = resumes[i];
        const rowData = HEADERS.map(col => {
          const val = r[col];
          return (val !== undefined && val !== null && String(val).trim() !== "") ? String(val).trim() : "Không có thông tin cụ thể";
        });
        sheet.appendRow(rowData);
        addedCount++;
      }

      formatDataCells(sheet);

      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        action: "reset_and_sync",
        added: addedCount,
        total_rows: sheet.getLastRow(),
        message: "Đã làm mới toàn bộ bảng tính và đồng bộ 27 cột thành công!"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // 2. NẾU LÀ ACTION APPEND BÌNH THƯỜNG
    // Nếu sheet trống hoặc số cột ở dòng 1 chưa đủ 27 cột chuẩn -> Cập nhật Header
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      formatHeader(sheet);
    } else {
      const currentCols = sheet.getLastColumn();
      const firstRow = sheet.getRange(1, 1, 1, Math.max(currentCols, HEADERS.length)).getValues()[0];
      if (currentCols < HEADERS.length || firstRow[10] !== HEADERS[10]) {
        // Tự động nâng cấp dòng 1 lên 27 cột chuẩn
        sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
        formatHeader(sheet);
      }
    }

    // Đọc dữ liệu hiện có để chống trùng lặp (theo SĐT và Email)
    const existingData = sheet.getDataRange().getValues();
    const existingPhones = new Set();
    const existingEmails = new Set();
    
    // Cột SĐT là cột 2 (index 1), Email là cột 3 (index 2)
    for (let r = 1; r < existingData.length; r++) {
      const phone = cleanPhone(String(existingData[r][1] || ""));
      const email = String(existingData[r][2] || "").trim().toLowerCase();
      if (phone && phone !== "không có thông tin cụ thể") existingPhones.add(phone);
      if (email && email !== "không có thông tin cụ thể") existingEmails.add(email);
    }

    let addedCount = 0;
    let duplicateCount = 0;
    const skippedDetails = [];

    // Thêm các ứng viên không bị trùng
    for (let i = 0; i < resumes.length; i++) {
      const r = resumes[i];
      const phone = cleanPhone(String(r["Số điện thoại"] || ""));
      const email = String(r["Email"] || "").trim().toLowerCase();
      
      let isDuplicate = false;
      let dupReason = "";
      
      if (phone && phone !== "không có thông tin cụ thể" && existingPhones.has(phone)) {
        isDuplicate = true;
        dupReason = "Trùng Số điện thoại: " + phone;
      } else if (email && email !== "không có thông tin cụ thể" && existingEmails.has(email)) {
        isDuplicate = true;
        dupReason = "Trùng Email: " + email;
      }

      if (isDuplicate) {
        duplicateCount++;
        skippedDetails.push((r["Họ và tên"] || "Ứng viên") + " (" + dupReason + ")");
      } else {
        // Tạo dòng dữ liệu theo đúng thứ tự 27 cột
        const rowData = HEADERS.map(col => {
          const val = r[col];
          return (val !== undefined && val !== null && String(val).trim() !== "") ? String(val).trim() : "Không có thông tin cụ thể";
        });
        
        sheet.appendRow(rowData);
        if (phone && phone !== "không có thông tin cụ thể") existingPhones.add(phone);
        if (email && email !== "không có thông tin cụ thể") existingEmails.add(email);
        addedCount++;
      }
    }

    formatDataCells(sheet);

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      added: addedCount,
      duplicates: duplicateCount,
      skipped: skippedDetails,
      total_rows: sheet.getLastRow()
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function cleanPhone(str) {
  if (!str) return "";
  let digits = str.replace(/\D/g, "");
  if (digits.startsWith("84") && digits.length >= 10) {
    digits = "0" + digits.substring(2);
  }
  return digits;
}

function formatHeader(sheet) {
  const headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
  headerRange.setBackground("#1F4E78");
  headerRange.setFontColor("#FFFFFF");
  headerRange.setFontWeight("bold");
  headerRange.setHorizontalAlignment("center");
  sheet.setFrozenRows(1);
}

function formatDataCells(sheet) {
  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, HEADERS.length)
         .setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP)
         .setVerticalAlignment("top");
  }
}


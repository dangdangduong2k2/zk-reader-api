# Changelog

## 0.1.0a1 — 2026-09-28

- Repo độc lập cho API Python + HTTP loopback, giao tiếp serial trực tiếp trên OS sở hữu reader.
- Không phụ thuộc DLL Windows, Nation hoặc COM ảo; runtime pySerial.
- Info, công suất chung, EPC inventory, bộ lọc, đọc các bank, ghi EPC/User có selector, địa chỉ thường/mở rộng.
- Kiểm tra CRC/frame/address, gom inventory nhiều frame, deadline và khóa transaction; không tự retry ghi.
- Simulator, golden packet test từ SDK, test HTTP/đọc/ghi, ví dụ client và Markdown/OpenAPI.

Alpha: chưa nghiệm thu API serial mới trên phần cứng thật và macOS/Linux. Không kế thừa kết quả nghiệm thu từ bridge Windows dùng DLL.

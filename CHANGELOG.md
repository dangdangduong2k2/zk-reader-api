# Changelog

## 0.1.0a3 — 2026-09-29

- Thêm `Reader.query()` và GET/POST `/v1/query` cho Q/Session gốc Ex10 CFG9 (0xEB/0xEA), không dùng cache để giả phản hồi module.
- Get trước Set; sửa riêng Q hoặc Session giữ nguyên trường còn lại; đọc lại sau Set và báo lỗi nếu không khớp. `persist=true` lưu cả cặp theo giao thức module.
- Hỗ trợ Session 255 Auto trong CFG9; inventory thường vẫn dùng tham số mỗi lời gọi, mặc định Q=4/Session=0. Không đổi hành vi inventory của alpha 2.
- Cập nhật OpenAPI, hướng dẫn Python/HTTP, ví dụ cấu hình, tài liệu giới hạn và link bộ cài Windows dành cho người dùng Nation.
- 54 test tự động đạt trên Windows. CFG9 mới được kiểm thử bằng serial giả và HTTP loopback; chưa nghiệm thu Q/Session qua Python trên module thật, macOS/Linux hoặc RF đọc/ghi qua API.

## 0.1.0a2 — 2026-09-28

- Thêm Get/Set band và dải kênh tần số qua 0x9E/0x22; hỗ trợ kênh cố định khi min=max.
- Thêm Get/Set link profile ZK legacy và extended qua 0x7F; giữ nguyên ID ZK, không giả lập ánh xạ profile Nation.
- Sửa công suất: Get vector thực tế từng anten qua 0x94, Set vector qua 0x2F; cho phép ANT1–ANT4 khác mức.
- Get độc lập trước/sau Set để kiểm tra khả năng hỗ trợ và đọc lại kết quả; không báo thành công nếu không khớp.
- Thay đổi response power: thêm powers_dbm; dbm=null và scope=per_antenna khi các mức khác nhau.
- Sửa auto profile ưu tiên extended: module thật trả legacy 0 nhưng profile đang dùng là extended 146.
- 46 test đạt; ba nhóm Set/Get cấu hình đã thử trên module 4 anten firmware 2.8 ở Windows và khôi phục trạng thái cũ. Chưa nghiệm thu đọc/ghi RF qua API mới hoặc macOS/Linux.

## 0.1.0a1 — 2026-09-28

- Repo độc lập cho API Python + HTTP loopback, giao tiếp serial trực tiếp trên OS sở hữu reader.
- Không phụ thuộc DLL Windows, Nation hoặc COM ảo; runtime pySerial.
- Info, công suất chung, EPC inventory, bộ lọc, đọc các bank, ghi EPC/User có selector, địa chỉ thường/mở rộng.
- Kiểm tra CRC/frame/address, gom inventory nhiều frame, deadline và khóa transaction; không tự retry ghi.
- Simulator, golden packet test từ SDK, test HTTP/đọc/ghi, ví dụ client và Markdown/OpenAPI.

Alpha: chưa nghiệm thu API serial mới trên phần cứng thật và macOS/Linux. Không kế thừa kết quả nghiệm thu từ bridge Windows dùng DLL.

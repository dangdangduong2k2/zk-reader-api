# Xử lý lỗi

| Hiện tượng | Cách kiểm tra |
|---|---|
| Không thấy cổng | Chạy `python -m zk_reader_api.server --list-ports`; kiểm tra nguồn/cáp/driver USB của adapter |
| Permission denied trên Linux | Kiểm tra quyền thiết bị serial và nhóm của tài khoản theo cấu hình distro; không cần chạy cả ứng dụng bằng root |
| Access denied/busy trên Windows | Đóng Nation/demo ZK/terminal; nếu bridge cũ đang chạy, dừng `NationZkComBridge` trước khi dùng cùng reader |
| macOS không có `/dev/cu.*` phù hợp | Cần adapter và driver tương thích phiên bản macOS/kiến trúc máy; không cài driver Windows lên macOS |
| ImportError/không tìm thấy lệnh | Dùng Python của venv đã `pip install .`; gọi `python -m zk_reader_api.server` thay executable ngoài PATH |
| Unauthorized HTTP | Token thay đổi mỗi lần khởi động nếu không dùng token-file; gửi Bearer header đúng |
| Browser bị chặn | API cục bộ không bật CORS; gọi từ backend/desktop hoặc thư viện Python |
| Timeout | Kiểm tra đúng COM/baud, module ở chế độ đáp lệnh, không bị chương trình khác giữ. Chờ lượt cũ kết thúc, đóng/mở lại reader |
| CRC/command/address sai | Kiểm tra đường truyền/protocol/model. Transport bị khóa để tránh nhận dữ liệu cũ; không bỏ CRC để tiếp tục |
| Unsupported reader-info format | Reader khác profile đã triển khai; lưu byte phản hồi qua công cụ chẩn đoán riêng, bổ sung profile có test trước khi hỗ trợ |
| Inventory trả tags rỗng | Kiểm tra anten, thẻ, vùng đọc, power, selector; HTTP 200 không bảo đảm có thẻ |
| HTTP 422 | Reader đã trả status lỗi; giữ command/status/detail_hex khi chẩn đoán |
| Write ACK nhưng EPC không hiện đúng | Đọc lại EPC và PC. API không tự sửa PC khi thay độ dài EPC |
| Mất ACK ghi / lỗi restore | Kết quả ghi có thể đã xảy ra. Không gửi lại ngay; kiểm tra anten rồi đọc thẻ bằng TID selector |
| Reader busy | Gọi tuần tự. Một tiến trình sở hữu reader; mỗi lệnh ghép chọn anten/read/write/restore được khóa cùng nhau |

Khi báo lỗi: ghi phiên bản API, OS/Python, model/firmware, baud/antenna, endpoint, mã lỗi và bước tái hiện. Không đưa token, password thật, EPC/TID khách hàng hoặc cấu hình riêng lên issue public.

Các lỗi reconnect/persistence của bridge Nation cũ không được mang sang nguyên trạng: API này không có COM ảo và không dùng handler Nation. Tuy nhiên vẫn cần kiểm thử reconnect và persistence riêng, không suy ra đã hết mọi lỗi chỉ vì đổi kiến trúc.

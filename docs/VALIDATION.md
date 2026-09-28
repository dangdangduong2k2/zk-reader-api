# Kiểm chứng — 0.1.0 alpha

## Đã chạy

- 25 bài kiểm thử đạt trên Windows/Python 3.14, gồm chạy lại bằng wheel cài trong venv riêng; hợp đồng OpenAPI 3.1 đã qua validator.
- Unit/integration test Python trên Windows với backend serial giả và HTTP thật trên loopback.
- Byte command đối chiếu với SDK DLL gốc qua TCP reader giả: info, inventory không mask/có mask, power, antenna, read, write.
- Frame phân mảnh, nhiều frame inventory nối tiếp, CRC sai, sai command/address, thiếu phản hồi và không tự retry ghi.
- Inventory chọn anten/lọc, phân biệt không có thẻ với lỗi anten, giữ trạng thái partial.
- Mô phỏng ghi User rồi đọc lại, đổi EPC bằng selector TID, khôi phục anten, báo lỗi restore sau ACK.
- Kiểm tra đầu vào trước serial I/O: vùng nhớ, số anten, độ dài hex, địa chỉ tràn, giới hạn công suất.
- HTTP kiểm tra token, Host/Origin, tham số, reader busy, vòng đọc/ghi mô phỏng.

Danh sách test có trong `tests/test_api.py`; chạy lại bằng `python -m unittest discover -s tests -v`. Mẫu EPC/TID/password trong test đều là dữ liệu tổng hợp.

## Chưa nghiệm thu

- **API serial mới chưa chạy trên reader thật.** Khi làm bản này, COM49 không hiện trong danh sách cổng; không mở COM khác để đoán thiết bị.
- Chưa chạy trực tiếp trên máy macOS/Linux hoặc Mac Apple Silicon. Mã Python/pySerial tránh phụ thuộc Windows; điều này là thiết kế khả chuyển, không phải bằng chứng nghiệm thu từng OS/adapter.
- Chưa kiểm chứng profile reader-info 12 byte trên thiết bị hiện tại, bản 1 anten, RF đủ 4 anten, đọc/ghi địa chỉ mở rộng, mất nguồn, USB rút/cắm lại, tải dài hạn.
- Kết quả reader thật của **rs232-bridge 0.4 dùng DLL** không được tính là test phần cứng cho API thuần serial này.
- CI có matrix Windows/macOS/Linux nhưng tài khoản GitHub trước đó bị chặn Actions do billing. Không coi workflow tồn tại là CI đã chạy thành công; xem kết quả run thực tế.

## Checklist nghiệm thu tại bên tích hợp

1. Ghi OS, Python, model/firmware reader, adapter USB, baud, số anten.
2. `info()` đúng định dạng, đọc công suất và antenna mask.
3. Inventory từng anten có thẻ, không có thẻ, lọc đúng/không khớp; kiểm tra RSSI raw.
4. Đọc EPC/TID/User/Reserved đúng thẻ và phạm vi, đối chiếu với công cụ hãng.
5. Trên thẻ thử: lưu dữ liệu gốc, ghi một word User, đọc lại, khôi phục. Tiếp theo thử EPC với full TID selector.
6. Công suất tạm thời thay đổi và đọc lại; persistence thử riêng sau power-cycle.
7. Thử timeout/rút USB trong các bước đọc; với ghi phải đọc lại để xác định kết quả, không lặp lại tự động.
8. Kiểm tra reconnect sau khi reader kết thúc lượt cũ, chạy dài hạn và ứng dụng gọi đồng thời.

Chỉ nâng trạng thái tương thích của model/OS khi có kết quả thực tế ghi lại. Bản phát hành alpha phục vụ tích hợp và nghiệm thu, chưa phải bản sản xuất đã chứng nhận.

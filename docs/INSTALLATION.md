# Cài đặt và kết nối

## Mô hình

```text
Reader ZK → adapter USB/RS232 → máy Windows/macOS/Linux
                                ├─ ứng dụng Python dùng Reader trực tiếp
                                └─ server Python cục bộ ← ứng dụng bất kỳ gọi HTTP
```

Cả hai cách đều giao tiếp cổng vật lý trên OS đang chạy. Không cần Nation COM Port, com0com hoặc máy Windows khác. HTTP trong bản này chỉ nghe loopback; không triển khai dịch vụ mạng công cộng.

## Chuẩn bị Python

Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m zk_reader_api.server --list-ports
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m zk_reader_api.server --list-ports
```

Có thể thay `.` bằng đường dẫn wheel tải từ release, ví dụ `zk_reader_api-0.1.0a1-py3-none-any.whl`. pip cần Internet để lấy pySerial nếu chưa có. Wheel Python thuần không chứa DLL hoặc driver thiết bị; không có EXE dùng chung mọi OS.

## Chọn cổng vật lý

| OS | Ví dụ | Kiểm tra |
|---|---|---|
| Windows | `COM49` | Device Manager → Ports; đóng Nation/bridge nếu đang giữ reader |
| macOS Intel/Apple Silicon | `/dev/cu.usbserial-XXXX` hoặc `/dev/cu.SLAB_USBtoUART` | Dùng tên thật từ `--list-ports`; cần driver adapter hỗ trợ máy đang dùng |
| Linux | `/dev/ttyUSB0`, `/dev/ttyACM0` | Tài khoản cần quyền truy cập thiết bị serial theo cấu hình distro |

Adapter USB/serial phải được OS nhận trước. Baud mặc định 115200 phải khớp cấu hình module; API không tự đổi baud/frequency trong reader. Chọn `--antennas 1` hoặc `4` đúng phần cứng, không phải số anten đang đọc trong một lượt.

Ví dụ chạy bằng Python trong venv:

```sh
python -m zk_reader_api.server --port COM49 --baud 115200 --antennas 4
```

Thay lệnh Python và tên cổng cho OS tương ứng. Không mở cùng reader bằng hai ứng dụng. Trên Windows đang có bản bridge, dừng dịch vụ `NationZkComBridge` trước khi dùng COM vật lý cho API; chỉ làm trên máy đang chuyển sang API.

## Token API

Mặc định mỗi lần chạy server tạo token mới và in ra terminal. Truyền qua header `Authorization: Bearer TOKEN`, không để trong URL. Muốn token cố định, tạo file chỉ chứa chuỗi ngẫu nhiên dài ít nhất 24 ký tự và dùng `--token-file PATH`. Không commit file token.

HTTP phục vụ ứng dụng desktop/backend cục bộ; không bật CORS cho trang web. Tích hợp trình duyệt nên qua backend của ứng dụng. Ctrl+C đóng server và COM; một lệnh đang gửi có thể cần hoàn tất timeout trước khi tiến trình thoát.

## Nghiệm thu trước khi triển khai

Kiểm tra thông tin reader → inventory từng anten → đọc TID/User → đặt/đọc lại công suất → ghi thẻ thử và đọc lại. Ghi nhận model, firmware, adapter, OS và Python. Hiện chưa có bằng chứng reader thật chạy API mới trên ba OS; xem [VALIDATION.md](VALIDATION.md).

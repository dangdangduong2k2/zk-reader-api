# Phát triển

## Cấu trúc

```text
src/zk_reader_api/
  protocol.py     CRC, frame, serial, deadline, transaction lock
  reader.py       info/power/region/profile/query/inventory/read/write, validate và antenna restore
  configuration.py bảng band/channel ZK, quy đổi kHz và kiểm tra dải kênh
  simulation.py   một thẻ tổng hợp, xử lý command frame trong RAM
  server.py       HTTP loopback, token, JSON, điều phối thao tác
  errors.py       lỗi thiết bị, transport, protocol, restore
tests/            golden frame, transport, API và HTTP
examples/         Python trực tiếp và Node.js qua HTTP
docs/openapi.json hợp đồng HTTP
```

HTTP không gọi DLL hay shell. Cả thư viện và server dùng cùng lớp Reader. Simulator đi qua cùng bộ đóng/gỡ frame nhưng chỉ mô phỏng một tập con phần cứng; test golden byte độc lập giúp tránh kiểm tra chỉ dựa vào simulator.

## Cài cho lập trình viên

```sh
python -m venv .venv
# Chọn python trong venv theo OS
python -m pip install -e .
python -m unittest discover -s tests -v
python examples/python_direct.py
python -m zk_reader_api.server --simulate
```

Test HTTP dùng port ngẫu nhiên trên loopback, không cần quyền admin/driver COM ảo. Không dùng reader thật trong CI. Workflow matrix là Windows/macOS/Linux với Python 3.10/3.12; việc test có chạy hay không tùy trạng thái Actions của tài khoản.

## Nguyên tắc mở rộng

- Thêm lệnh từ tài liệu firmware/model phù hợp và capture độc lập; không suy đoán packet layout.
- Thêm test trước các đường ghi/phá khóa/thay cấu hình. Không báo thành công khi lệnh chưa hỗ trợ.
- Phân biệt terminal status và continuation. Đừng retry thao tác ghi chỉ vì transport không nhận ACK.
- Một transaction giữ khóa từ chọn anten tới khôi phục; không chèn lệnh của thread khác giữa chừng.
- Giữ raw status thiết bị, không gán RSSI thành dBm khi chưa có công thức xác nhận.
- Muốn hỗ trợ profile reader-info khác, thêm parser theo layout được kiểm chứng; không nhận mọi độ dài bằng cách bỏ byte cuối.

## Đóng gói

```sh
python -m pip install build
python -m build
```

Kết quả `dist/*.whl` và `dist/*.tar.gz`. Wheel `py3-none-any` là Python thuần, không chứng nhận reader đã chạy trên mọi OS. Người nhận cài wheel bằng `python -m pip install PATH.whl`.

Trước release: chạy test, xác nhận docs/OpenAPI khớp route/validation, cập nhật CHANGELOG/VALIDATION, tạo tag, upload wheel/sdist cùng SHA256. Source ZIP/TAR tự có trên GitHub. Không phát hành SDK DLL, log máy, token hoặc dữ liệu thẻ thật. Không cần EXE Windows cho thư viện đa nền tảng này.

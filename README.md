# ZK Reader API

**Python SDK + HTTP API cục bộ cho module RFID ZK Ex10 cắm trực tiếp vào Windows, macOS hoặc Linux.** Giao tiếp serial bằng Python/pySerial, không cần máy Windows trung gian, DLL ZK, phần mềm Nation hoặc driver COM ảo.

Đây là repo riêng với [rs232-bridge](https://github.com/dangdangduong2k2/rs232-bridge). Ứng dụng mới gọi API này; phần mềm Nation cũ không tự chuyển sang dùng HTTP.

**0.1.0 alpha 2 — đã thử Set/Get tần số, link profile và công suất từng anten trên module thật 4 anten, firmware 2.8, Windows.** 46 test tự động đạt. Chưa nghiệm thu macOS/Linux và đọc/ghi RF qua API mới. Cần driver USB/RS232 phù hợp với adapter trên OS đang dùng. Không phải API cho mọi sản phẩm ZK.

## Cài và chạy

Cần Python 3.10+. Tải [bản phát hành](https://github.com/dangdangduong2k2/zk-reader-api/releases) hoặc clone:

```sh
git clone https://github.com/dangdangduong2k2/zk-reader-api.git
cd zk-reader-api
python -m pip install .
python -m zk_reader_api.server --list-ports
```

Trên macOS/Linux có thể dùng `python3` thay `python`. Khuyến nghị cài trong môi trường ảo; xem [INSTALLATION.md](docs/INSTALLATION.md).

```sh
# Thử API không cần phần cứng
python -m zk_reader_api.server --simulate

# Chỉ chạy một trong các lệnh phù hợp với máy/cổng thực tế
python -m zk_reader_api.server --port COM49 --baud 115200 --antennas 4
python3 -m zk_reader_api.server --port /dev/cu.usbserial-XXXX --antennas 4
python3 -m zk_reader_api.server --port /dev/ttyUSB0 --antennas 4
```

Server in URL `http://127.0.0.1:8765` và token. Ứng dụng C#, Java, Go, Node.js, Python… chạy trên cùng máy dùng token để gọi HTTP. Thư viện Python cũng dùng trực tiếp, không cần HTTP.

```python
from zk_reader_api import Reader

with Reader.open("/dev/cu.usbserial-XXXX", antennas=4) as reader:
    print(reader.info())
    print(reader.inventory(antennas=[1, 2]))
```

## Chức năng

| Chức năng | API HTTP |
|---|---|
| Trạng thái tiến trình | `GET /health` |
| Thông tin reader | `GET /v1/reader` |
| Đọc / đặt công suất chung hoặc riêng từng anten | `GET /v1/power`, `POST /v1/power` |
| Đọc / đặt band và dải kênh tần số, hoặc kênh cố định | `GET /v1/region`, `POST /v1/region` |
| Đọc / đặt link profile ZK | `GET /v1/profile`, `GET /v1/profile/extended`, `POST /v1/profile` |
| Đọc EPC, chọn anten, lọc EPC/TID/User | `POST /v1/inventory` |
| Đọc vùng Reserved/EPC/TID/User | `POST /v1/read` |
| Ghi vùng EPC/User có bộ chọn thẻ | `POST /v1/write` |

Mỗi inventory là một lượt hữu hạn. Ứng dụng đọc liên tục bằng cách gọi tuần tự; dừng bằng cách ngừng gọi. Không tự retry lệnh ghi khi timeout. Không hỗ trợ Lock/Kill, firmware, GPIO, 6B, FastID/phase hoặc toàn bộ SDK hãng trong bản này.

## Tài liệu

- [Cài đặt từng hệ điều hành](docs/INSTALLATION.md)
- [API HTTP/Python, tham số và mã lỗi](docs/API.md)
- [OpenAPI 3.1](docs/openapi.json)
- [Giao thức serial và đối chiếu SDK](docs/PROTOCOL.md)
- [Kiểm thử và giới hạn](docs/VALIDATION.md)
- [Xử lý lỗi](docs/TROUBLESHOOTING.md)
- [Phát triển và đóng gói](docs/DEVELOPMENT.md)
- [Ví dụ Python](examples/python_direct.py), [Node.js](examples/client.mjs)
- [Thành phần bên thứ ba](THIRD_PARTY_NOTICES.md), [changelog](CHANGELOG.md)

```sh
python -m unittest discover -s tests -v
```

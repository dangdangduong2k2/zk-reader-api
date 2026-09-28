# API v1

Base URL: `http://127.0.0.1:8765`. Tất cả endpoint cần `Authorization: Bearer TOKEN`. POST dùng `Content-Type: application/json`. Có [OpenAPI](openapi.json) để nhập vào công cụ API/generate client.

## Quy ước

- Anten đánh số từ 1, tối đa theo cấu hình 1 hoặc 4.
- `bank`: 0 Reserved, 1 EPC, 2 TID, 3 User. Write chỉ cho phép 1 và 3.
- Địa chỉ đọc/ghi `word_address` tính bằng word 16 bit; địa chỉ bộ lọc `bit_address` tính bằng bit.
- Chuỗi hex không có khoảng trắng, `0x` hoặc dấu phân cách. Password đúng 8 ký tự hex.
- Tất cả kết quả thành công có `simulated`. Không dùng dữ liệu mô phỏng làm kết quả vận hành.
- Thư viện Python có cùng tên tham số; ví dụ `reader.inventory(**body)` hoặc `reader.write(**body)`.

## Selector

```json
{"bank": 2, "bit_address": 0, "hex": "E28000000000000000000001"}
```

Đây là TID **minh họa**. Phải thay bằng dữ liệu đọc được từ thẻ thật. Selector bắt buộc cho đọc/ghi, tùy chọn cho inventory. Cần đúng ba trường; `bank` 1–3, `bit_address` 0–16383, `hex` 1–31 byte và phạm vi không vượt 16384 bit. Bản này hỗ trợ bộ lọc theo số byte nguyên, không có bit-length lẻ.

Bộ lọc có thể khớp nhiều thẻ; API không bảo đảm duy nhất. Dùng full TID phù hợp hoặc đặt một thẻ thử trong vùng thao tác. Full EPC bắt đầu ở bit 32 của bank 1 (bỏ CRC và PC).

## Thông tin và công suất

`GET /health`: phiên bản, cờ mô phỏng, trạng thái transport; không gửi lệnh RF/serial. `connected=true` chưa chứng minh reader còn cắm nếu chưa có lệnh mới.

`GET /v1/reader`: address, firmware, reader_type, protocol_bits, configured_antennas, power_dbm, antenna_mask, frequency_bytes, check_antenna. Số anten là cấu hình khi mở API, không phải tự phát hiện chính xác model.

`GET /v1/power` đọc công suất từng anten từ lệnh ZK `0x94`. Đặt cùng một mức cho tất cả anten bằng:

```json
{"dbm": 22, "persist": false}
```

Hoặc đặt riêng ANT1–ANT4:

```json
{"powers_dbm": [20, 21, 22, 23], "persist": false}
```

Chỉ gửi một trong `dbm` hoặc `powers_dbm`. Mọi giá trị nguyên 0–30; mảng phải đủ số anten đã cấu hình (1 hoặc 4). `persist` mặc định false. API đọc lại toàn bộ cổng để đối chiếu, không suy ra công suất ANT2–4 từ ANT1. Firmware không hỗ trợ query từng anten trả lỗi rõ ràng và không gửi Set.

```json
{"dbm": null, "powers_dbm": [20,21,22,23], "scope":"per_antenna", "simulated":true}
```

**Thay đổi từ alpha 1:** `dbm` có thể là null khi các cổng khác nhau; `powers_dbm` luôn chứa giá trị từng cổng. Nếu tất cả bằng nhau, `dbm` là giá trị chung và `scope` là global. Không dùng trường `power_dbm` trong reader-info để suy ra công suất từng anten.

## Tần số hoạt động

`GET /v1/region` đọc band và khoảng kênh thực tế. `POST /v1/region` đặt band và dải kênh liên tục:

```json
{"band":27,"min_channel":0,"max_channel":7,"persist":false}
```

Ví dụ trên dùng mã band 27 trong bảng firmware ZK; kết quả `frequencies_khz` từ 918750 tới 922250 kHz, bước 500 kHz. Muốn một tần số cố định, đặt min=max; band 27, kênh 3 là 920250 kHz.

`min_channel`/`max_channel` là chỉ số kênh ZK, không phải kênh Nation. API kiểm tra bảng ở `configuration.py` và đọc lại bằng `0x9E` sau Set `0x22`. Không hỗ trợ danh sách kênh rời rạc; không thay thế bằng khoảng rộng hơn một cách âm thầm.

Kết quả gồm `band`, `min_channel`, `max_channel`, `band_name`, `frequencies_khz`, `table_known`, `simulated`. Nếu firmware trả band ngoài bảng hoặc phạm vi chưa xác định, giữ giá trị gốc và trả `table_known=false`, tần số null. Bảng band là định nghĩa trong SDK, không phải xác nhận phạm vi được phép phát ở nơi triển khai.

Python: `reader.region()` để đọc; `reader.region(band=27, min_channel=3, max_channel=3)` để đặt kênh cố định.

## Link profile / EPC Baseband

- `GET /v1/profile`: tự chọn định dạng, ưu tiên extended để đọc profile thực tế trên Gen2X.
- `GET /v1/profile/extended`: đọc định dạng extended 2 byte trên firmware hỗ trợ.
- `POST /v1/profile`: đặt profile bằng lệnh `0x7F`, rồi gửi Get độc lập để đối chiếu.

```json
{"profile_id":7,"format":"auto","persist":false}
```

```json
{"profile_id":241,"format":"extended","persist":false}
```

`format` mặc định auto: thử đọc extended; chỉ chuyển sang legacy nếu reader trả lỗi định dạng/lệnh rõ ràng `0xFD/0xFE`. Không fallback sau timeout/CRC hoặc sau một lần Set. Legacy nhận ID 0–63; extended nhận ID 0–65535. Không phải mọi ID trong khoảng đều được firmware hỗ trợ; reader có thể trả lỗi. API không tự đổi sang profile gần giống.

Trên module Gen2X đã thử, Get legacy trả 0 trong khi profile extended thực tế là 146. Vì vậy không ép legacy trên module mới. `format` trong kết quả là định dạng đã dùng (legacy hoặc extended), không phải auto.

Kết quả ví dụ: `{"profile_id":146,"format":"extended","namespace":"zk","simulated":false}`. **Đây là ID ZK, không phải chỉ số dropdown Nation/R2000.** Ví dụ tài liệu Ex10 ghi ZK profile 7 là Miller4, BLF 250 kHz, Tari 20 µs; Nation mode 1 trong tài liệu có Tari 25 µs. Không coi hai chế độ tương đương chỉ vì cùng Miller/BLF.

Python: `reader.profile()` hoặc `reader.profile(format="extended")` để đọc; `reader.profile(241, format="extended")` để đặt.

Với cả power, region và profile, `persist=true` yêu cầu firmware lưu khi mất nguồn. API chỉ xác nhận readback trong phiên, chưa nghiệm thu power-cycle. Những lệnh này sửa cấu hình phần cứng nên không tự lặp sau mất phản hồi.

## Inventory

`POST /v1/inventory`

```json
{"antennas": [1, 2], "scan_time": 3, "q": 4, "session": 0, "target": 0}
```

| Trường | Mặc định / phạm vi |
|---|---|
| antennas | Tất cả anten cấu hình; danh sách không rỗng, không trùng |
| scan_time | 3; 3–20 đơn vị 100 ms cho mỗi anten |
| q | 4; 0–15 |
| session | 0; 0–3 |
| target | 0; 0=A, 1=B |
| selector | Không lọc nếu bỏ qua |

```json
{"tags":[{"epc":"E20000000000000000000001","antenna":1,"rssi_raw":65}],"rounds":[{"antenna":1,"status":1,"partial":false}],"simulated":true}
```

`rssi_raw` là byte gốc, không gán đơn vị dBm. `rounds[].status`: 1 hoàn tất, 2 hết thời gian inventory, 4 bộ nhớ reader đầy, 251 không có thẻ thao tác được. 2/4 vẫn trả dữ liệu nhưng đánh dấu partial. Status 3 được gom với các frame tiếp theo trước khi trả HTTP.

Một lượt không chống trùng giữa các anten/lần gọi. Muốn đọc liên tục, gọi tuần tự endpoint trong vòng lặp. Muốn dừng, ngừng gửi lượt mới; lượt đang chạy hoàn tất hoặc timeout. Không có endpoint Start/Stop nền hoặc callback/WebSocket trong alpha này.

## Đọc bộ nhớ

`POST /v1/read`

```json
{"antenna":1,"bank":2,"word_address":0,"words":6,"selector":{"bank":1,"bit_address":32,"hex":"E20000000000000000000001"},"password":"00000000"}
```

`words` 1–120; `word_address` 0–65535 và không tràn phạm vi. Address >255 dùng lệnh mở rộng. API chọn tạm anten và khôi phục mask trên module 4 anten. Module 1 anten không gửi lệnh multiplexing.

Kết quả: `{"hex":"E28000000000000000000001","words":6,"simulated":true}`. Thẻ thiếu bộ nhớ/khóa/password sai trả lỗi thiết bị; không tự cắt ngắn dữ liệu.

## Ghi EPC/User

`POST /v1/write`

```json
{"antenna":1,"bank":3,"word_address":0,"hex":"1234ABCD","selector":{"bank":2,"bit_address":0,"hex":"E28000000000000000000001"},"password":"00000000"}
```

`hex` từ 1–32 word (2–64 byte), theo giới hạn tài liệu serial. EPC bank 1 không cho ghi word 0 (CRC). Ghi EPC từ word 2 thay nội dung; API **không tự sửa PC word 1**, nên thay độ dài EPC cần người tích hợp xử lý PC chính xác. Có thể gửi PC + EPC bắt đầu từ word 1. Dùng selector TID khi đổi EPC để vẫn đọc lại được thẻ.

Kết quả: `{"acknowledged":true,"verified":false,"words":2,"simulated":true}`. Reader đã ACK không có nghĩa đã đọc lại xác minh; bên gọi phải gọi `/v1/read` để so sánh.

API gửi lệnh ghi đúng một lần, không tự retry. HTTP/serial timeout hoặc mất phản hồi có thể xảy ra sau khi thẻ đã đổi dữ liệu. Không gửi lại tự động; kết nối lại và đọc kiểm chứng bằng selector ổn định trước.

## Mã lỗi HTTP

| HTTP | error | Ý nghĩa |
|---|---|---|
| 400 | invalid_parameters / invalid_json_body | Tham số, kiểu dữ liệu, JSON không hợp lệ |
| 401 | unauthorized | Thiếu/sai token |
| 403 | invalid_host / browser_origin_not_allowed | Host không phải loopback hợp lệ hoặc request từ browser origin |
| 404 | route_not_found | Sai endpoint/method GET/POST |
| 409 | reader_busy | Một thao tác đang chạy; đọc có thể gọi lại sau |
| 411 / 413 / 415 | content_length_required / body_too_large / expected_application_json | Sai cấu trúc HTTP body; tối đa 8192 byte |
| 422 | device_error | Reader trả status lỗi, kèm command/status/detail_hex gốc |
| 502 | protocol_error | CRC/frame/định dạng không hỗ trợ hoặc dữ liệu phản hồi không đúng |
| 502 | antenna_restore_failed | Không khôi phục được anten; kiểm tra action_succeeded và trạng thái thiết bị |
| 503 | transport_error | Timeout/I/O, phải đóng và mở lại reader/server |

Một số status thiết bị: `5` sai password, `248` lỗi anten, `251` không có thẻ thao tác được, `252` lỗi thẻ (chi tiết trong detail_hex), `253` sai tham số. Giữ giá trị số gốc khi báo lỗi.

`action_succeeded=true` nghĩa thao tác đã nhận phản hồi hợp lệ trước khi lỗi restore. `false` không bảo đảm thẻ chưa bị ghi; có thể mất ACK. Sau CRC/timeout, transport bị khóa để không nhận nhầm phản hồi cũ. Chờ reader kết thúc lượt cũ rồi đóng/mở lại; không có tự reconnect/replay lệnh.

## Ví dụ gọi HTTP

macOS/Linux terminal, thay TOKEN bằng token server:

```sh
curl -H 'Authorization: Bearer TOKEN' http://127.0.0.1:8765/v1/reader
curl -X POST -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"antennas":[1],"scan_time":3}' http://127.0.0.1:8765/v1/inventory
```

PowerShell:

```powershell
$headers = @{ Authorization = 'Bearer TOKEN' }
Invoke-RestMethod http://127.0.0.1:8765/v1/inventory -Method Post -Headers $headers -ContentType application/json -Body '{"antennas":[1]}'
```

Đặt timeout client ít nhất 15 giây cho tối đa 4 anten. Hủy request phía client không hoàn tác lệnh đã gửi reader.

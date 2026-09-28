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

`GET /v1/power` trả `dbm`, `scope: "global"`. Đặt bằng:

```json
{"dbm": 22, "persist": false}
```

`dbm` nguyên 0–30; `persist` mặc định false. API đọc lại ngay để đối chiếu. `persist=true` yêu cầu module lưu khi mất nguồn, chưa nghiệm thu power-cycle. Chưa có API công suất riêng anten.

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

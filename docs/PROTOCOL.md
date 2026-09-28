# Giao thức serial và nguồn đối chiếu

## Nguồn

Nguồn chính là tài liệu **UHF RFID Reader Series User Manual V2.25.doc**, trong `Ex10 Module SDK V6.8/english/Manual/` do người dùng cung cấp. Không đưa toàn bộ SDK/tài liệu độc quyền vào repo. Các mục dùng: 3 (frame/CRC), 8.2.1–8.2.3 (inventory/read/write), 8.2.18–8.2.19 (địa chỉ mở rộng), 8.4.1 (info), 8.4.6 (power), 8.4.8 (antenna).

Đối chiếu bổ sung: gọi `UHFReader288.dll` x64 từ SDK vào một TCP reader giả trên loopback, ghi lại byte DLL gửi. Không nối thiết bị, không ghi lên thẻ. DLL chỉ dùng làm công cụ đối chiếu ngoài repo, không phải dependency của API.

Serial dùng [pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html), 8 data bit, no parity, 1 stop bit, không hardware/software flow control. Đường dẫn thiết bị phụ thuộc OS.

## Frame

Command:

```text
Len | Address | Command | Payload... | CRC low | CRC high
```

Response:

```text
Len | Address | Command | Status | Payload... | CRC low | CRC high
```

`Len` đếm mọi byte sau chính nó. Giới hạn command payload 251 byte. Địa chỉ 255 là broadcast cho **một reader point-to-point**; sau phản hồi đầu tiên API dùng address thực tế. Không triển khai bus RS485 nhiều reader.

CRC16 khởi tạo `0xFFFF`, đa thức phản chiếu `0x8408`, không final XOR, CRC thấp trước. CRC tính trên toàn bộ frame có CRC phải bằng 0.

Transport chỉ có một lệnh đang chờ, kiểm tra CRC/command/address, nhận frame chia nhỏ và nhiều frame liên tiếp. Inventory status 3 chưa kết thúc: tiếp tục đọc đến status cuối. Giới hạn 2048 frame và timeout 3 giây/lệnh. Timeout/CRC/lỗi I/O làm transport mất đồng bộ; không gửi tiếp hoặc tự lặp lệnh ghi.

## Lệnh triển khai

| Hex | Ý nghĩa | Payload |
|---|---|---|
| 21 | Info | Rỗng; phản hồi profile cổ điển 12 byte |
| 2F | Set power | 1 byte áp dụng chung, hoặc đủ 1/4 byte cho từng anten; bit7=1 là không lưu mất nguồn |
| 94 | Get antenna powers | Rỗng; kết quả phải có đúng 1/4 byte theo module cấu hình |
| 22 | Set region (format 2) | flag 0=lưu/1=không lưu, band, max channel, min channel |
| 9E | Get region | Rỗng; kết quả band, max channel, min channel |
| 7F | Link profile | Legacy: bit7=Set, bit6=không lưu, ID 6 bit. Extended: opt 0=Get/1=Set lưu/2=Set không lưu và ID 2 byte big-endian |
| 3F | Antenna mask | bit0–3 tương ứng anten 1–4; bit7=1 không lưu |
| 01 | Inventory | Q, session, mask tùy chọn, target, 0x80+antenna-1, scantime |
| 02 / 15 | Read | 0xFF, bank, word address 1/2 byte, count, password, selector |
| 03 / 16 | Write | word count, 0xFF, bank, word address 1/2 byte, data, password, selector |

Selector: bank 1 byte, bit address 2 byte big-endian, bit length 1 byte, mask data. API chỉ xuất mask có độ dài là bội số 8 bit, tối đa 248 bit. Word/address nhiều byte dùng big-endian; CRC dùng little-endian.

Ví dụ ghi User một word, lọc TID `E280` tại bit 32 (mẫu thử, không phải nhận dạng thẻ thật):

```text
14 00 03 01 FF 03 00 12 34 00 00 00 00 02 00 20 10 E2 80 FA F6
```

Các mẫu byte độc lập từ DLL được cố định trong `tests/test_api.py::test_vendor_golden_frames`, gồm info, inventory có/không mask, power, antenna, read và write.

## Giới hạn profile

Tài liệu có ví dụ Len của info không khớp bảng trường. Bản này giải theo bảng 12 byte; độ dài khác trả lỗi rõ ràng, không đoán offset. Từ alpha 2, frequency bytes `FF FF` được giữ nguyên và dùng lệnh `0x9E` để đọc band/kênh riêng. Cần capture phản hồi thực tế trước khi mở rộng model.

Inventory chỉ giải EPC/RSSI cơ bản. FastID/phase bị từ chối nếu xuất hiện; không gán nhầm dữ liệu thành EPC. Không tự đổi vùng tần số khi mở reader; chỉ đổi qua lời gọi Set region rõ ràng. Chưa có API đổi baud của thiết bị, firmware, password hay lock/kill. Write 1–32 word theo tài liệu wire, khác giới hạn lớp chuyển Nation cũ.

Alpha 2 có thêm capture độc lập từ DLL hãng cho `GetAntennaPower`, `SetAntennaPower`, `ExtGetRegion`, `ExtSetRegion`, `SetProfile`, `SetExtProfile`. Ví dụ `GetAntennaPower` phát `04 00 94 FF 88`; tài liệu có dòng response ghi `0x51` không nhất quán, DLL và module thật thử với reply `0x94` đều giải thành công. Ba nhóm lệnh cấu hình đã Set/Get trên module thật; chi tiết [VALIDATION.md](VALIDATION.md).

Profile mặc định auto ưu tiên extended. Legacy có thể vẫn trả thành công nhưng là trường cũ không phản ánh profile đang chạy trên Gen2X (đã gặp legacy 0 / extended 146). Chỉ fallback đọc legacy khi extended trả status FD/FE; không đoán từ ID nhỏ và không fallback sau lỗi transport/Set.

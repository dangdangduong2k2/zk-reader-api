import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from zk_reader_api import Reader, DeviceError, ProtocolError, TransportError, RestoreError
from zk_reader_api.protocol import SerialTransport, command_frame, crc16, decode_response
from zk_reader_api.server import ApiServer
from zk_reader_api.simulation import MemorySerial

SELECTOR = {"bank": 2, "bit_address": 0, "hex": "E28000000000000000000001"}


def response(cmd, data=b"", status=0, address=0):
    wire = bytes((len(data)+5, address, cmd, status)) + data
    return wire + crc16(wire).to_bytes(2, "little")


class ScriptedSerial:
    def __init__(self, replies, fragment=1):
        self.replies = list(replies)
        self.pending = bytearray()
        self.writes = []
        self.fragment = fragment
        self.timeout = .001
        self.closed = False

    def write(self, frame):
        self.writes.append(frame)
        if self.replies:
            self.pending.extend(self.replies.pop(0))
        return len(frame)

    def read(self, n):
        if not self.pending:
            time.sleep(min(self.timeout, .001))
        n = min(n, self.fragment)
        data = bytes(self.pending[:n])
        del self.pending[:n]
        return data

    def close(self):
        self.closed = True


class ProtocolTests(unittest.TestCase):
    def test_vendor_golden_frames(self):
        # Independently captured from the supplied x64 vendor DLL against a local fake TCP reader.
        vectors = [(255, 0x21, "", "04ff211995"),
                   (0, 1, "0400008003", "0900010400008003e347"),
                   (0, 1, "040002000010e280008003", "0f0001040002000010e2800080036c65"),
                   (0, 0x2F, "96", "05002f96323c"),
                   (0, 0x3F, "82", "05003f8206ff"),
                   (0, 2, "06e2000000000000000000000102000600000000", "18000206e20000000000000000000001020006000000003a3e"),
                   (0, 3, "01ff030012340000000002002010e280", "14000301ff030012340000000002002010e280faf6")]
        for address, command, payload, expected in vectors:
            with self.subTest(command=command, payload=payload):
                self.assertEqual(command_frame(address, command, bytes.fromhex(payload)).hex(), expected)

    def test_reader_builds_vendor_inventory_and_write_payloads(self):
        serial = ScriptedSerial([response(1, status=0xFB), response(1, status=0xFB)])
        reader = Reader(SerialTransport(serial, address=0))
        reader.inventory([1])
        reader.inventory([1], selector={"bank": 2, "bit_address": 0, "hex": "E280"})
        self.assertEqual([w.hex() for w in serial.writes],
                         ["0900010400008003e347", "0f0001040002000010e2800080036c65"])
        info = bytes.fromhex("02087502000016030F000001")
        serial = ScriptedSerial([response(0x21, info), response(0x3F), response(3), response(0x3F)])
        reader = Reader(SerialTransport(serial, address=0))
        reader.write(antenna=2, bank=3, word_address=0, hex="1234",
                     selector={"bank": 2, "bit_address": 32, "hex": "E280"})
        self.assertEqual(serial.writes[1].hex(), "05003f8206ff")
        self.assertEqual(serial.writes[2].hex(), "14000301ff030012340000000002002010e280faf6")

    def test_fragmented_response_resolves_broadcast(self):
        serial = ScriptedSerial([response(0x21, bytes(12), address=7)])
        transport = SerialTransport(serial)
        self.assertEqual(transport.exchange(0x21)[0].address, 7)
        self.assertEqual(transport.address, 7)

    def test_crc_failure_poisoned_transport_no_retry(self):
        raw = bytearray(response(0x21))
        raw[-1] ^= 1
        serial = ScriptedSerial([raw])
        transport = SerialTransport(serial)
        with self.assertRaises(ProtocolError):
            transport.exchange(0x21)
        with self.assertRaises(TransportError):
            transport.exchange(0x21)
        self.assertEqual(len(serial.writes), 1)

    def test_missing_write_reply_not_retried(self):
        serial = ScriptedSerial([])
        transport = SerialTransport(serial, timeout=.01)
        with self.assertRaises(TransportError):
            transport.exchange(3, b"example")
        self.assertEqual(len(serial.writes), 1)
        self.assertTrue(transport.failed)

    def test_wrong_command_and_address_rejected(self):
        for reply in (response(0x2F), response(0x21, address=1)):
            transport = SerialTransport(ScriptedSerial([reply]), address=0)
            with self.assertRaises(ProtocolError):
                transport.exchange(0x21)

    def test_inventory_continuation(self):
        first = response(1, bytes.fromhex("010102123441"), 3)
        last = response(1, bytes.fromhex("010102567842"), 2)
        serial = ScriptedSerial([first+last], fragment=50)
        reader = Reader(SerialTransport(serial))
        result = reader.inventory([1])
        self.assertEqual([t["epc"] for t in result["tags"]], ["1234", "5678"])
        self.assertTrue(result["rounds"][0]["partial"])

    def test_invalid_inventory_records(self):
        for data in (b"", bytes.fromhex("0200"), bytes.fromhex("0101051234"),
                     bytes.fromhex("010182123441"), bytes.fromhex("010000")):
            reader = Reader(SerialTransport(ScriptedSerial([response(1, data, 1)])))
            with self.subTest(data=data), self.assertRaises(ProtocolError):
                reader.inventory([1])

    def test_no_tags_and_hardware_error_distinguished(self):
        reader = Reader(SerialTransport(ScriptedSerial([response(1, status=0xFB), response(1, status=0xF8)])))
        self.assertEqual(reader.inventory([1])["tags"], [])
        with self.assertRaises(DeviceError) as error:
            reader.inventory([1])
        self.assertEqual(error.exception.status, 0xF8)

    def test_command_size_and_response_length(self):
        with self.assertRaises(ValueError):
            command_frame(0, 1, bytes(252))
        with self.assertRaises(ProtocolError):
            decode_response(bytes(6))


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.reader = Reader.simulate()

    def tearDown(self):
        self.reader.close()

    def test_info_and_power(self):
        self.assertTrue(self.reader.info()["simulated"])
        self.assertEqual(self.reader.power(22)["dbm"], 22)

    def test_single_antenna_no_multiplexing(self):
        with Reader.simulate(1) as reader:
            self.assertEqual(reader.info()["antenna_mask"], 1)
            reader.write(antenna=1, bank=3, word_address=0, hex="ABCD", selector=SELECTOR)
            self.assertEqual(reader.read(antenna=1, bank=3, word_address=0, words=1, selector=SELECTOR)["hex"], "ABCD")

    def test_inventory_all_and_filter(self):
        tags = self.reader.inventory()["tags"]
        self.assertEqual([t["antenna"] for t in tags], [1, 2, 3, 4])
        self.assertEqual(len(self.reader.inventory([2], selector=SELECTOR)["tags"]), 1)
        missing = dict(SELECTOR, hex="FFFF")
        self.assertEqual(self.reader.inventory([1], selector=missing)["tags"], [])

    def test_user_write_read_and_restore(self):
        result = self.reader.write(antenna=2, bank=3, word_address=1, hex="1234ABCD", selector=SELECTOR)
        self.assertTrue(result["acknowledged"])
        self.assertFalse(result["verified"])
        self.assertEqual(self.reader.read(antenna=2, bank=3, word_address=1, words=2, selector=SELECTOR)["hex"], "1234ABCD")
        self.assertEqual(self.reader.info()["antenna_mask"], 15)

    def test_epc_change_tid_selector_keeps_working(self):
        self.reader.write(antenna=1, bank=1, word_address=2, hex="ABCD", selector=SELECTOR)
        self.assertTrue(self.reader.inventory([1])["tags"][0]["epc"].startswith("ABCD"))
        self.assertEqual(self.reader.read(antenna=1, bank=1, word_address=2, words=1, selector=SELECTOR)["hex"], "ABCD")

    def test_device_error_preserves_antenna(self):
        with self.assertRaises(DeviceError) as error:
            self.reader.write(antenna=1, bank=3, word_address=0, hex="1234", selector=SELECTOR, password="11111111")
        self.assertEqual(error.exception.status, 5)
        self.assertEqual(self.reader.info()["antenna_mask"], 15)

    def test_validate_before_any_hardware_io(self):
        serial = ScriptedSerial([])
        reader = Reader(SerialTransport(serial))
        cases = [lambda: reader.power(True), lambda: reader.power(31),
                 lambda: reader.inventory([1, 1]), lambda: reader.inventory([5]),
                 lambda: reader.inventory([1], scan_time=0),
                 lambda: reader.write(antenna=1, bank=0, word_address=0, hex="1234", selector=SELECTOR),
                 lambda: reader.write(antenna=1, bank=3, word_address=0, hex="12", selector=SELECTOR),
                 lambda: reader.write(antenna=1, bank=3, word_address=0, hex="1234", selector={}),
                 lambda: reader.read(antenna=1, bank=2, word_address=65535, words=2, selector=SELECTOR)]
        for case in cases:
            with self.assertRaises(ValueError):
                case()
        self.assertEqual(serial.writes, [])

    def test_unsupported_info_format(self):
        for data in (bytes(10), bytes(13)):
            reader = Reader(SerialTransport(ScriptedSerial([response(0x21, data)])))
            with self.assertRaises(ProtocolError):
                reader.info()

    def test_restore_failure_reports_completed_write(self):
        data = bytes.fromhex("02087502000016030F000001")
        serial = ScriptedSerial([response(0x21, data), response(0x3F), response(3), response(0x3F, status=0xFD)])
        reader = Reader(SerialTransport(serial))
        with self.assertRaises(RestoreError) as error:
            reader.write(antenna=1, bank=3, word_address=0, hex="1234", selector=SELECTOR)
        self.assertTrue(error.exception.action_succeeded)
        self.assertEqual(sum(w[2] == 3 for w in serial.writes), 1)

    def test_extended_address_wire_order(self):
        data = bytes.fromhex("02087502000016030F000001")
        serial = ScriptedSerial([response(0x21, data), response(0x3F), response(0x16), response(0x3F)])
        reader = Reader(SerialTransport(serial))
        reader.write(antenna=1, bank=3, word_address=0x1234, hex="ABCD", selector=SELECTOR)
        self.assertEqual(serial.writes[2][2:10], bytes.fromhex("1601ff031234abcd"))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = "test-only-token-not-a-credential"
        cls.server = ApiServer(("127.0.0.1", 0), Reader.simulate(), cls.token)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(3)
        cls.server.server_close()
        cls.server.reader.close()

    def call(self, path, body=None, headers=None):
        headers = {"Authorization": "Bearer "+self.token, "Content-Type": "application/json", **(headers or {})}
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.url+path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as r:
            with r:
                return r.code, json.load(r)

    def test_auth_and_origin(self):
        self.assertEqual(self.call("/health", headers={"Authorization": ""})[0], 401)
        self.assertEqual(self.call("/health", headers={"Origin": "https://example.com"})[0], 403)
        self.assertEqual(self.call("/health", headers={"Host": "evil.example"})[0], 403)

    def test_health_and_reader(self):
        self.assertTrue(self.call("/health")[1]["simulated"])
        self.assertEqual(self.call("/v1/reader")[0], 200)

    def test_read_write_http_roundtrip(self):
        args = {"antenna": 1, "bank": 3, "word_address": 0, "selector": SELECTOR}
        self.assertEqual(self.call("/v1/write", {**args, "hex": "BEEF"})[0], 200)
        self.assertEqual(self.call("/v1/read", {**args, "words": 1})[1]["hex"], "BEEF")

    def test_inventory_power(self):
        self.assertEqual(len(self.call("/v1/inventory", {"antennas": [1]})[1]["tags"]), 1)
        self.assertEqual(self.call("/v1/power", {"dbm": 21})[1]["dbm"], 21)

    def test_invalid_and_busy(self):
        self.assertEqual(self.call("/v1/inventory", {"antennas": [5]})[0], 400)
        self.assertEqual(self.call("/v1/power", {})[0], 400)
        self.assertEqual(self.call("/v1/power", {"dbm": None})[0], 400)
        self.assertEqual(self.call("/v1/write", {})[0], 400)
        self.assertEqual(self.call("/v1/inventory", {"surprise": 1})[0], 400)
        self.assertEqual(self.call("/missing")[0], 404)
        with self.server.operation_lock:
            self.assertEqual(self.call("/v1/reader")[0], 409)


if __name__ == "__main__":
    unittest.main()

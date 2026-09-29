import unittest

from zk_reader_api import Reader, DeviceError, ProtocolError
from zk_reader_api.protocol import SerialTransport
from test_api import ScriptedSerial, response
import test_api


class QueryTests(unittest.TestCase):
    def test_first_get_and_external_change_read_device_each_time(self):
        serial = ScriptedSerial([response(0xEB, b"\x06\x01"), response(0xEB, b"\x09\x03")])
        reader = Reader(SerialTransport(serial))
        self.assertEqual(reader.query(), {"q": 6, "session": 1, "simulated": False})
        self.assertEqual(reader.query(), {"q": 9, "session": 3, "simulated": False})
        self.assertEqual([(w[2], w[3:-2]) for w in serial.writes], [(0xEB, b"\x09")] * 2)

    def test_partial_set_preserves_native_other_field_and_persist_flags(self):
        for arguments, expected, payload in [
            ({"q": 10}, (10, 1), b"\x01\x09\x0a\x01"),
            ({"session": 3, "persist": True}, (6, 3), b"\x00\x09\x06\x03"),
            ({"q": 15, "session": 255}, (15, 255), b"\x01\x09\x0f\xff"),
        ]:
            with self.subTest(arguments=arguments):
                serial = ScriptedSerial([response(0xEB, b"\x06\x01"), response(0xEA),
                                         response(0xEB, bytes(expected))])
                result = Reader(SerialTransport(serial)).query(**arguments)
                self.assertEqual((result["q"], result["session"]), expected)
                self.assertEqual([(w[2], w[3:-2]) for w in serial.writes],
                                 [(0xEB, b"\x09"), (0xEA, payload), (0xEB, b"\x09")])

    def test_malformed_or_unsupported_preflight_never_sets(self):
        for data in (b"", b"\x06", b"\x06\x01\x00", b"\x10\x01", b"\x06\x04"):
            serial = ScriptedSerial([response(0xEB, data)])
            with self.assertRaises(ProtocolError):
                Reader(SerialTransport(serial)).query(q=7)
            self.assertEqual(len(serial.writes), 1)
        serial = ScriptedSerial([response(0xEB, status=0xEE)])
        with self.assertRaises(DeviceError):
            Reader(SerialTransport(serial)).query(q=7)
        self.assertEqual(len(serial.writes), 1)

    def test_bad_ack_or_readback_never_reports_success_or_retries(self):
        for replies, count in [
            ([response(0xEA, b"\x00")], 2),
            ([response(0xEA, status=0xFD)], 2),
            ([response(0xEA), response(0xEB, b"\x06\x01")], 3),
            ([response(0xEA), response(0xEB, b"\x07")], 3),
        ]:
            serial = ScriptedSerial([response(0xEB, b"\x06\x01"), *replies])
            with self.assertRaises((ProtocolError, DeviceError)):
                Reader(SerialTransport(serial)).query(q=7)
            self.assertEqual(len(serial.writes), count)
            self.assertEqual(sum(w[2] == 0xEA for w in serial.writes), 1)

    def test_invalid_inputs_no_io(self):
        serial = ScriptedSerial([])
        reader = Reader(SerialTransport(serial))
        for arguments in ({"q": -1}, {"q": 16}, {"q": True}, {"q": 1.5},
                          {"session": 4}, {"session": 254}, {"session": 256},
                          {"session": True}, {"session": "1"}, {"persist": 1}):
            with self.assertRaises(ValueError):
                reader.query(**arguments)
        self.assertEqual(serial.writes, [])

    def test_simulator_roundtrip_and_inventory_defaults_are_independent(self):
        with Reader.simulate() as reader:
            self.assertEqual(reader.query()["q"], 6)
            self.assertEqual(reader.query(q=9, session=255)["session"], 255)
            packets = []
            original = reader.transport.serial.write
            def capture(wire):
                packets.append(wire)
                return original(wire)
            reader.transport.serial.write = capture
            reader.inventory(antennas=[1])
            self.assertEqual(packets[0][2:5], b"\x01\x04\x00")
            self.assertEqual(reader.query(), {"q": 9, "session": 255, "simulated": True})


class QueryHttpTests(unittest.TestCase):
    setUpClass = classmethod(test_api.HttpTests.setUpClass.__func__)
    tearDownClass = classmethod(test_api.HttpTests.tearDownClass.__func__)
    call = test_api.HttpTests.call

    def test_get_partial_set_and_auto(self):
        self.assertEqual(self.call('/v1/query')[0], 200)
        status, result = self.call('/v1/query', {"q": 8, "session": 2})
        self.assertEqual((status, result["q"], result["session"]), (200, 8, 2))
        status, result = self.call('/v1/query', {"session": 255, "persist": True})
        self.assertEqual((status, result["q"], result["session"]), (200, 8, 255))
        self.assertEqual(self.call('/v1/query')[1], result)

    def test_invalid_posts(self):
        for body in ({}, {"persist": True}, {"q": None}, {"q": 4, "session": None},
                     {"q": True}, {"session": 4}, {"q": 16}, {"q": 4, "extra": 1}):
            self.assertEqual(self.call('/v1/query', body)[0], 400)

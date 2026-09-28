import unittest

from zk_reader_api import Reader, DeviceError, ProtocolError
from zk_reader_api.configuration import BANDS, validate_region
from zk_reader_api.protocol import SerialTransport
from test_api import ScriptedSerial, response
import test_api


class ConfigurationTests(unittest.TestCase):
    def test_golden_individual_power_set_and_readback(self):
        serial = ScriptedSerial([response(0x94, bytes([10]*4)), response(0x2F),
                                 response(0x94, bytes([20,21,22,23]))])
        reader = Reader(SerialTransport(serial, address=0))
        result = reader.power(powers_dbm=[20,21,22,23])
        self.assertEqual([w.hex() for w in serial.writes],
                         ["040094ff88", "08002f949596975226", "040094ff88"])
        self.assertEqual(result["powers_dbm"], [20,21,22,23])
        self.assertIsNone(result["dbm"])
        self.assertEqual(result["scope"], "per_antenna")

    def test_global_power_readback_all_antennas(self):
        serial = ScriptedSerial([response(0x94, bytes([10]*4)), response(0x2F),
                                 response(0x94, bytes([22]*4))])
        reader = Reader(SerialTransport(serial, address=0))
        self.assertEqual(reader.power(22)["dbm"], 22)
        self.assertEqual(serial.writes[1].hex(), "05002f96323c")

    def test_power_mismatch_not_acknowledged(self):
        serial = ScriptedSerial([response(0x94, bytes([10]*4)), response(0x2F),
                                 response(0x94, bytes([22,22,21,22]))])
        with self.assertRaisesRegex(ProtocolError, "readback"):
            Reader(SerialTransport(serial)).power(22)

    def test_wrong_antenna_count_fails_before_set(self):
        serial = ScriptedSerial([response(0x94, b"\x14")])
        with self.assertRaises(ProtocolError):
            Reader(SerialTransport(serial)).power(powers_dbm=[20]*4)
        self.assertEqual([f[2] for f in serial.writes], [0x94])

    def test_unsupported_power_query_never_fabricates_values(self):
        serial = ScriptedSerial([response(0x94, status=0xFE)])
        with self.assertRaises(DeviceError):
            Reader(SerialTransport(serial)).power(22)
        self.assertEqual([f[2] for f in serial.writes], [0x94])

    def test_golden_region_set_and_readback(self):
        serial = ScriptedSerial([response(0x9E, bytes([1,19,0])), response(0x22),
                                 response(0x9E, bytes([1,19,0]))])
        result = Reader(SerialTransport(serial, address=0)).region(1,0,19)
        self.assertEqual([w.hex() for w in serial.writes],
                         ["04009ea527", "08002201011300e422", "04009ea527"])
        self.assertEqual(result["frequencies_khz"][0], 920125)
        self.assertEqual(result["frequencies_khz"][-1], 924875)

    def test_fixed_frequency_vietnam(self):
        with Reader.simulate() as reader:
            result = reader.region(27, 3, 3)
            self.assertEqual(result["frequencies_khz"], [920250])
            self.assertEqual(reader.region(), result)

    def test_region_mismatch_and_unknown_band_reads(self):
        serial = ScriptedSerial([response(0x9E, bytes([1,19,0])), response(0x22),
                                 response(0x9E, bytes([1,19,0]))])
        with self.assertRaisesRegex(ProtocolError,"readback"):
            Reader(SerialTransport(serial)).region(27,0,7)
        reader = Reader(SerialTransport(ScriptedSerial([response(0x9E, bytes([250,7,0]))])))
        result = reader.region()
        self.assertFalse(result["table_known"])
        self.assertIsNone(result["frequencies_khz"])

    def test_documented_channel_boundaries(self):
        # Independent endpoints and counts from the manual, including split bands.
        expected = {1:(920125,924875,20),2:(902750,927250,50),4:(865100,867900,15),
                    6:(868000,868600,7),17:(920750,927250,14),21:(902750,927250,35),
                    27:(918750,922250,8),29:(917250,921250,4),33:(916200,919800,4)}
        for band,(first,last,count) in expected.items():
            self.assertEqual((BANDS[band][1][0],BANDS[band][1][-1],len(BANDS[band][1])),(first,last,count))
            with self.assertRaises(ValueError):
                validate_region(band,0,count)
        self.assertEqual(BANDS[21][1][10],915250)
        self.assertEqual(BANDS[29][1][1],920250)

    def test_golden_legacy_profile(self):
        serial = ScriptedSerial([response(0x7F,b"\x01"),response(0x7F,b"\x07"),response(0x7F,b"\x07")])
        result=Reader(SerialTransport(serial,address=0)).profile(7,format="legacy")
        self.assertEqual([w.hex() for w in serial.writes],
                         ["05007f007a1e","05007fc7c9ac","05007f007a1e"])
        self.assertEqual(result["profile_id"],7)
        self.assertEqual(result["namespace"],"zk")

    def test_golden_extended_profile(self):
        serial = ScriptedSerial([response(0x7F,b"\x00\x01"),response(0x7F,b"\x00\x07"),response(0x7F,b"\x00\x07")])
        result=Reader(SerialTransport(serial,address=0)).profile(7,format="extended")
        self.assertEqual([w.hex() for w in serial.writes],
                         ["07007f0000001dfc","07007f0200071a3d","07007f0000001dfc"])
        self.assertEqual(result["profile_id"],7)

    def test_extended_id_not_truncated(self):
        with Reader.simulate() as reader:
            self.assertEqual(reader.profile(241,format="extended")["profile_id"],241)
            self.assertEqual(reader.profile(format="extended")["profile_id"],241)

    def test_profile_mismatch_rejected(self):
        serial=ScriptedSerial([response(0x7F,b"\x01"),response(0x7F,b"\x07"),response(0x7F,b"\x01")])
        with self.assertRaisesRegex(ProtocolError,"readback"):
            Reader(SerialTransport(serial)).profile(7,format="legacy")

    def test_persist_flags(self):
        for method, args, cmd, offset, expected in [
            ("power",{"powers_dbm":[20,21,22,23]},0x2f,3,20),
            ("region",{"band":1,"min_channel":0,"max_channel":19},0x22,3,0),
            ("profile",{"profile_id":7,"format":"legacy"},0x7f,3,0x87),
            ("profile",{"profile_id":241,"format":"extended"},0x7f,3,1)]:
            with Reader.simulate() as reader:
                packets=[]
                original=reader.transport.serial.write
                def capture(data):
                    packets.append(data)
                    return original(data)
                reader.transport.serial.write=capture
                getattr(reader,method)(persist=True,**args)
                self.assertEqual(packets[1][2],cmd)
                self.assertEqual(packets[1][offset],expected)

    def test_invalid_parameters_before_io(self):
        serial=ScriptedSerial([])
        reader=Reader(SerialTransport(serial))
        cases=[lambda:reader.power(powers_dbm=[20]),lambda:reader.power(20,powers_dbm=[20]*4),
               lambda:reader.power(powers_dbm=[20,True,20,20]),lambda:reader.region(27,0,8),
               lambda:reader.region(27,3,2),lambda:reader.region(27,None,3),
               lambda:reader.region(5,0,3),lambda:reader.profile(64,format="legacy"),
               lambda:reader.profile(65536,format="extended"),lambda:reader.profile(7,persist=1)]
        for case in cases:
            with self.assertRaises(ValueError):case()
        self.assertEqual(serial.writes,[])

    def test_auto_prefers_actual_extended_profile(self):
        # Actual Ex10 Gen2X returned legacy 0 but extended 146; prefer extended.
        serial=ScriptedSerial([response(0x7F,bytes.fromhex('0092'))])
        result=Reader(SerialTransport(serial,address=0)).profile()
        self.assertEqual(result['profile_id'],146)
        self.assertEqual(result['format'],'extended')
        self.assertEqual(serial.writes[0].hex(),'07007f0000001dfc')

    def test_auto_legacy_fallback_only_after_explicit_rejection(self):
        serial=ScriptedSerial([response(0x7F,status=0xFD),response(0x7F,b'\x07')])
        result=Reader(SerialTransport(serial)).profile()
        self.assertEqual(result['format'],'legacy')
        self.assertEqual(result['profile_id'],7)
        self.assertEqual(len(serial.writes),2)

    def test_auto_does_not_hide_other_errors(self):
        serial=ScriptedSerial([response(0x7F,status=0xF9)])
        with self.assertRaises(DeviceError):Reader(SerialTransport(serial)).profile()
        self.assertEqual(len(serial.writes),1)

    def test_auto_read_after_extended_write(self):
        with Reader.simulate() as reader:
            reader.profile(241)
            self.assertEqual(reader.profile()['profile_id'],241)


class ConfigurationHttpTests(unittest.TestCase):
    setUpClass = classmethod(test_api.HttpTests.setUpClass.__func__)
    tearDownClass = classmethod(test_api.HttpTests.tearDownClass.__func__)
    call = test_api.HttpTests.call

    def test_config_roundtrips(self):
        self.assertEqual(self.call('/v1/power',{'powers_dbm':[20,21,22,23]})[1]['powers_dbm'],[20,21,22,23])
        self.assertIsNone(self.call('/v1/power')[1]['dbm'])
        self.assertEqual(self.call('/v1/region',{'band':27,'min_channel':0,'max_channel':7})[1]['band'],27)
        self.assertEqual(self.call('/v1/region')[1]['frequencies_khz'][-1],922250)
        self.assertEqual(self.call('/v1/profile',{'profile_id':7})[1]['profile_id'],7)
        self.assertEqual(self.call('/v1/profile')[1]['profile_id'],7)
        self.assertEqual(self.call('/v1/profile',{'profile_id':241,'format':'extended'})[1]['profile_id'],241)
        self.assertEqual(self.call('/v1/profile/extended')[1]['profile_id'],241)

    def test_config_post_requires_set_values(self):
        for path,body in [('/v1/power',{'powers_dbm':None}),('/v1/region',{}),('/v1/profile',{})]:
            self.assertEqual(self.call(path,body)[0],400)

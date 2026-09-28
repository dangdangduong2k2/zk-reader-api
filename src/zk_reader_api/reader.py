"""Portable high-level API for the documented Ex10 1/4-antenna profile."""
from contextlib import contextmanager
import re

from .errors import DeviceError, ProtocolError, RestoreError
from .protocol import SerialTransport, integer


def hex_bytes(value, name, minimum=0, maximum=256, words=False):
    if not isinstance(value, str) or len(value) % 2 or not re.fullmatch(r"[0-9a-fA-F]*", value):
        raise ValueError(f"{name} must be even-length hex without spaces")
    data = bytes.fromhex(value)
    if not minimum <= len(data) <= maximum or (words and len(data) % 2):
        raise ValueError(f"Invalid {name} byte/word length")
    return data


def selector_bytes(selector):
    if not isinstance(selector, dict) or set(selector) != {"bank", "bit_address", "hex"}:
        raise ValueError("selector requires exactly bank, bit_address, hex")
    bank = integer(selector["bank"], 1, 3, "selector.bank")
    address = integer(selector["bit_address"], 0, 16383, "selector.bit_address")
    data = hex_bytes(selector["hex"], "selector.hex", 1, 31)
    if address + len(data) * 8 > 16384:
        raise ValueError("Selector exceeds memory bit address range")
    return bytes((bank,)) + address.to_bytes(2, "big") + bytes((len(data) * 8,)) + data


def parse_inventory(reply, antenna):
    if reply.status == 0xFB:
        if reply.data:
            raise ProtocolError("Unexpected no-tag payload")
        return []
    if reply.status not in (1, 2, 3, 4):
        raise DeviceError(reply.command, reply.status, reply.data)
    data = reply.data
    if len(data) < 2 or data[0] != 1 << (antenna - 1):
        raise ProtocolError("Invalid inventory antenna/data")
    tags, offset = [], 2
    for _ in range(data[1]):
        if offset >= len(data):
            raise ProtocolError("Missing tag record")
        flags = data[offset]
        offset += 1
        length = flags & 63
        if flags & 0xC0 or length < 2 or length % 2 or offset + length + 1 > len(data):
            raise ProtocolError("Malformed or unsupported FastID/phase record")
        tags.append({"epc": data[offset:offset+length].hex().upper(),
                     "antenna": antenna, "rssi_raw": data[offset+length]})
        offset += length + 1
    if offset != len(data):
        raise ProtocolError("Unexpected inventory trailing data")
    return tags


class Reader:
    def __init__(self, transport, antennas=4, simulated=False):
        if type(antennas) is not int or antennas not in (1, 4):
            raise ValueError("antennas must be 1 or 4")
        self.transport, self.antennas, self.simulated = transport, antennas, simulated

    @classmethod
    def open(cls, port, baud=115200, antennas=4, address=255):
        # Validate before touching a physical serial port.
        if type(antennas) is not int or antennas not in (1, 4):
            raise ValueError("antennas must be 1 or 4")
        transport = SerialTransport.open(port, baud, address=address)
        reader = cls(transport, antennas)
        try:
            reader.info()
            return reader
        except BaseException:
            transport.close()
            raise

    @classmethod
    def simulate(cls, antennas=4):
        from .simulation import MemorySerial
        if type(antennas) is not int or antennas not in (1, 4):
            raise ValueError("antennas must be 1 or 4")
        return cls(SerialTransport(MemorySerial(antennas)), antennas, simulated=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.transport.close()

    def _call(self, command, payload=b""):
        reply = self.transport.exchange(command, payload)[0]
        if reply.status != 0:
            raise DeviceError(command, reply.status, reply.data)
        return reply.data

    def info(self):
        with self.transport.lock:
            data = self._call(0x21)
            # Manual length example conflicts with its table; use the table's 12-byte format.
            if len(data) != 12 or data[4:6] == b"\xff\xff":
                raise ProtocolError("Unsupported reader-info format; expected classic 12-byte profile")
            return {"simulated": self.simulated, "address": self.transport.address,
                    "firmware": f"{data[0]}.{data[1]}", "reader_type": data[2],
                    "protocol_bits": data[3], "configured_antennas": self.antennas,
                    "power_dbm": data[6], "antenna_mask": data[8] & 15,
                    "frequency_bytes": data[4:6].hex().upper(), "check_antenna": data[11]}

    def power(self, dbm=None, persist=False):
        if type(persist) is not bool:
            raise ValueError("persist must be boolean")
        if dbm is not None:
            integer(dbm, 0, 30, "dbm")
        with self.transport.lock:
            if dbm is not None:
                self._call(0x2F, bytes((dbm | (0 if persist else 128),)))
            actual = self.info()["power_dbm"]
            if dbm is not None and actual != dbm:
                raise ProtocolError("Power readback mismatch; setting may have changed")
            return {"dbm": actual, "scope": "global", "simulated": self.simulated}

    def inventory(self, antennas=None, scan_time=3, q=4, session=0, target=0, selector=None):
        if antennas is None:
            antennas = list(range(1, self.antennas + 1))
        if not isinstance(antennas, (list, tuple)) or not 1 <= len(antennas) <= self.antennas:
            raise ValueError("antennas must be a nonempty list")
        for antenna in antennas:
            integer(antenna, 1, self.antennas, "antenna")
        if len(set(antennas)) != len(antennas):
            raise ValueError("Duplicate antennas")
        integer(scan_time, 3, 20, "scan_time")
        integer(q, 0, 15, "q")
        integer(session, 0, 3, "session")
        integer(target, 0, 1, "target")
        mask = b"" if selector is None else selector_bytes(selector)
        tags, rounds = [], []
        with self.transport.lock:
            for antenna in antennas:
                payload = bytes((q, session)) + mask + bytes((target, 0x80 + antenna - 1, scan_time))
                replies = self.transport.exchange(1, payload, inventory=True)
                for reply in replies:
                    tags.extend(parse_inventory(reply, antenna))
                rounds.append({"antenna": antenna, "status": replies[-1].status,
                               "partial": replies[-1].status in (2, 4)})
        return {"tags": tags, "rounds": rounds, "simulated": self.simulated}

    @contextmanager
    def _selected_antenna(self, antenna):
        with self.transport.lock:
            if self.antennas == 1:
                yield
                return
            previous = self.info()["antenna_mask"]
            if previous == 0:
                raise ProtocolError("Cannot restore empty antenna mask")
            succeeded, cause = False, None
            try:
                self._call(0x3F, bytes((0x80 | (1 << (antenna - 1)),)))
                yield
                succeeded = True
            except BaseException as error:
                cause = error
                raise
            finally:
                try:
                    self._call(0x3F, bytes((0x80 | previous,)))
                except Exception as restore_error:
                    raise RestoreError(succeeded, cause or restore_error) from restore_error

    def read(self, *, antenna, bank, word_address, words, selector, password="00000000"):
        integer(antenna, 1, self.antennas, "antenna")
        integer(bank, 0, 3, "bank")
        integer(word_address, 0, 65535, "word_address")
        integer(words, 1, 120, "words")
        if word_address + words > 65536:
            raise ValueError("Read address wraps")
        mask = selector_bytes(selector)
        pwd = hex_bytes(password, "password", 4, 4)
        extended = word_address > 255
        payload = b"\xff" + bytes((bank,)) + word_address.to_bytes(2 if extended else 1, "big")
        payload += bytes((words,)) + pwd + mask
        with self._selected_antenna(antenna):
            data = self._call(0x15 if extended else 2, payload)
            if len(data) != words * 2:
                raise ProtocolError("Read response length does not match requested word count")
        return {"hex": data.hex().upper(), "words": words, "simulated": self.simulated}

    def write(self, *, antenna, bank, word_address, hex, selector, password="00000000"):
        integer(antenna, 1, self.antennas, "antenna")
        if type(bank) is not int or bank not in (1, 3):
            raise ValueError("Write supports EPC (1) and User (3) only")
        integer(word_address, 0, 65535, "word_address")
        if bank == 1 and word_address == 0:
            raise ValueError("Do not write EPC CRC word 0")
        data = hex_bytes(hex, "hex", 2, 64, words=True)
        if word_address + len(data)//2 > 65536:
            raise ValueError("Write address wraps")
        mask = selector_bytes(selector)
        pwd = hex_bytes(password, "password", 4, 4)
        extended = word_address > 255
        payload = bytes((len(data)//2, 255, bank)) + word_address.to_bytes(2 if extended else 1, "big")
        payload += data + pwd + mask
        with self._selected_antenna(antenna):
            reply = self._call(0x16 if extended else 3, payload)
            if reply:
                raise ProtocolError("Unexpected write response; verify tag before retrying")
        return {"acknowledged": True, "verified": False, "words": len(data)//2,
                "simulated": self.simulated}

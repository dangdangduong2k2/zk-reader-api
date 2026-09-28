"""Run after pip install .; default example never touches a real reader."""
from zk_reader_api import Reader

# For hardware replace with Reader.open("COM49", antennas=4),
# Reader.open("/dev/cu.usbserial-...", antennas=4) or Reader.open("/dev/ttyUSB0").
with Reader.simulate() as reader:
    print(reader.info())
    print(reader.inventory(antennas=[1]))
    print(reader.read(antenna=1, bank=2, word_address=0, words=6,
                      selector={"bank": 1, "bit_address": 32, "hex": "E20000000000000000000001"}))

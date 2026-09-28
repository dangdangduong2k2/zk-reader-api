"""Configuration examples on an in-memory reader; no physical hardware changed."""
from zk_reader_api import Reader

with Reader.simulate(antennas=4) as reader:
    print(reader.power(powers_dbm=[20, 21, 22, 23], persist=False))
    print(reader.power())
    print(reader.region(band=27, min_channel=3, max_channel=3, persist=False))
    print(reader.region())
    print(reader.profile(profile_id=241, format="auto", persist=False))
    print(reader.profile())

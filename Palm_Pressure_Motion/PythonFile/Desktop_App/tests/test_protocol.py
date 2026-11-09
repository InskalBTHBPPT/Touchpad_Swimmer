import struct
import tempfile
import unittest
from pathlib import Path

from palmlog.plg import parse_plg
from palmlog.protocol import (
    CHANNELS,
    RECORD_SIZE,
    STREAM_SAMPLE_LEN,
    PacketFramer,
    build_get_file,
    build_set_time,
    parse_chunk,
    parse_list_item,
    parse_sample,
    parse_status,
)


class ProtocolTests(unittest.TestCase):
    def test_status_16_and_legacy_14(self):
        pkt = bytearray(16)
        pkt[0] = 0x90
        pkt[1] = 1
        pkt[2] = 1
        pkt[11] = 3
        pkt[12] = 0
        struct.pack_into("<II", pkt, 3, 1_700_000_000, 0x1000)
        struct.pack_into("<H", pkt, 14, 3750)
        status = parse_status(bytes(pkt))
        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.measure)
        self.assertEqual(status.file_count, 3)
        self.assertEqual(status.battery_mv, 3750)
        self.assertEqual(status.free_bytes, 4 * 1024 * 1024 - 0x1000)
        # sisa kapasitas memakai 26 B/sample
        self.assertAlmostEqual(
            status.free_seconds or 0,
            ((4 * 1024 * 1024 - 0x1000) // 26) * 0.01,
            places=3,
        )
        legacy = parse_status(bytes(pkt[:14]))
        self.assertIsNotNone(legacy)
        assert legacy is not None
        self.assertIsNone(legacy.battery_mv)

    def test_stream_sample_29b_v4(self):
        # 0xB2 + seq + t_rel + 11×i16
        pkt = bytearray(STREAM_SAMPLE_LEN)
        pkt[0] = 0xB2
        struct.pack_into("<H", pkt, 1, 7)
        struct.pack_into("<I", pkt, 3, 1234)
        struct.pack_into("<11h", pkt, 7, 10, -20, 1000, 0, 0, -400, 0, 0, 100, 0, 0)
        self.assertEqual(len(pkt), 29)
        framer = PacketFramer()
        self.assertEqual(framer.feed(pkt[:12]), [])
        got = framer.feed(pkt[12:])
        self.assertEqual(got, [bytes(pkt)])
        sample = parse_sample(got[0])
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertEqual(sample.seq, 7)
        self.assertEqual(sample.t_rel_ms, 1234)
        self.assertEqual(sample.channels[0], 10)
        self.assertEqual(sample.channels[1], -20)
        self.assertEqual(sample.channels[2], 1000)
        phys = sample.physical_tuple()
        self.assertAlmostEqual(phys[2], 1.0)  # 1000 mg → 1 g
        self.assertAlmostEqual(phys[5], -40.0)  # -400 → -40 °/s

    def test_legacy_status_exact_notification(self):
        pkt = bytes([0x90]) + bytes(13)
        framer = PacketFramer()
        self.assertEqual(framer.feed(pkt), [pkt])

    def test_commands_and_list_chunk(self):
        self.assertEqual(build_set_time(0x0102030405060708)[0], 0x11)
        self.assertEqual(len(build_set_time(1)), 9)
        cmd = build_get_file("251007120000", 256, 100)
        self.assertEqual(len(cmd), 19)
        self.assertEqual(cmd[0], 0x21)
        item = bytearray(26)
        item[0] = 0xA1
        item[1:13] = b"251007120000"
        item[13] = 1
        struct.pack_into("<III", item, 14, 10, 256 + 260, 0x1000)
        parsed = parse_list_item(bytes(item))
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.name, "251007120000")
        self.assertEqual(parsed.n_records, 10)
        chunk = bytes([0xB1, 0]) + struct.pack("<IIH", 0, 20, 4) + b"PLG1"
        got = parse_chunk(chunk)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.data, b"PLG1")

    def test_plg_v4_roundtrip(self):
        raw = bytearray(256 + RECORD_SIZE * 2)
        raw[0:4] = b"PLG1"
        struct.pack_into("<HHBB", raw, 4, 4, 10, 11, 26)
        raw[10:22] = b"261007120000"
        struct.pack_into("<Q", raw, 22, 1_700_000_000_123)
        # rec0: t_rel=0, d1=500, d3=1000 → 1.0 g
        struct.pack_into("<I", raw, 256, 0)
        struct.pack_into("<11h", raw, 260, 500, 0, 1000, 0, 0, 0, 0, 0, 0, 0, 0)
        # rec1: t_rel=10, d1=1500, d3=2000 → 2.0 g
        struct.pack_into("<I", raw, 256 + 26, 10)
        struct.pack_into("<11h", raw, 260 + 26, 1500, 0, 2000, 0, 0, 0, 0, 0, 0, 0, 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "261007120000.bin"
            path.write_bytes(raw)
            plg = parse_plg(path)
        self.assertEqual(plg.count, 2)
        self.assertEqual(plg.version, 4)
        self.assertEqual(plg.record_size, 26)
        self.assertEqual(CHANNELS, 11)
        self.assertEqual(int(plg.raw[0, 0]), 500)
        self.assertAlmostEqual(float(plg.physical[0, 2]), 1.0)
        self.assertAlmostEqual(float(plg.physical[1, 2]), 2.0)
        self.assertEqual(int(plg.t_rel_ms[1]), 10)
        self.assertAlmostEqual(plg.time_s[1], 0.01)

    def test_plg_rejects_legacy_16b(self):
        raw = bytearray(256 + 32)
        raw[0:4] = b"PLG1"
        struct.pack_into("<HHBB", raw, 4, 2, 10, 8, 16)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.bin"
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                parse_plg(path)


if __name__ == "__main__":
    unittest.main()

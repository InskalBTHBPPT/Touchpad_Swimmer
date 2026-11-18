"""Madgwick diam: accel Z +1 g menjadi roll dan pitch dekat nol."""

import unittest

import numpy as np

from palmlog.attitude import madgwick_rpy_deg


class MadgwickLevelTest(unittest.TestCase):
    def test_level_roll_pitch_near_zero(self) -> None:
        n = 400
        time_s = np.arange(n, dtype=np.float64) * 0.01
        accel = np.zeros((n, 3), dtype=np.float64)
        accel[:, 2] = 1.0
        gyro = np.zeros((n, 3), dtype=np.float64)
        rpy = madgwick_rpy_deg(time_s, accel, gyro)
        self.assertEqual(rpy.shape, (n, 3))
        self.assertLess(abs(rpy[-1, 0]), 2.0)
        self.assertLess(abs(rpy[-1, 1]), 2.0)
        self.assertTrue(np.isfinite(rpy[-1]).all())


if __name__ == "__main__":
    unittest.main()

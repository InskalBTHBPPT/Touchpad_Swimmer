"""Madgwick diam: accel Z +1 g menjadi roll dan pitch dekat nol."""

import unittest

import numpy as np

from palmlog.attitude import attitude_rpy_deg, madgwick_rpy_deg


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

    def test_ekf_level_roll_pitch_near_zero(self) -> None:
        n = 200
        time_s = np.arange(n, dtype=np.float64) * 0.01
        accel = np.zeros((n, 3), dtype=np.float64)
        accel[:, 2] = 1.0
        gyro = np.zeros((n, 3), dtype=np.float64)
        rpy = attitude_rpy_deg(time_s, accel, gyro, method="ekf", axes=6)
        self.assertLess(abs(rpy[-1, 0]), 2.0)
        self.assertLess(abs(rpy[-1, 1]), 2.0)

    def test_nine_axis_stays_finite(self) -> None:
        n = 80
        time_s = np.arange(n, dtype=np.float64) * 0.01
        accel = np.zeros((n, 3), dtype=np.float64)
        accel[:, 2] = 1.0
        gyro = np.zeros((n, 3), dtype=np.float64)
        mag = np.tile(np.array([20.0, 5.0, -40.0]), (n, 1))
        for method in ("madgwick", "ekf"):
            rpy = attitude_rpy_deg(time_s, accel, gyro, mag, method=method, axes=9)
            self.assertEqual(rpy.shape, (n, 3))
            self.assertTrue(np.isfinite(rpy).all(), method)


if __name__ == "__main__":
    unittest.main()

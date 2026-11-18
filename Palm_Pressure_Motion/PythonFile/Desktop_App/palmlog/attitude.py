"""Roll, pitch, yaw dari accel dan gyro. Madgwick IMU, sama notebook komparasi."""

from __future__ import annotations

import numpy as np

G = 9.80665
# X tetap, Y dan Z dibalik. Sama catatan uji vs 3DM-GX5-25.
_AXIS = np.array([1.0, -1.0, -1.0])


def madgwick_rpy_deg(time_s: np.ndarray, accel_g: np.ndarray, gyro_dps: np.ndarray) -> np.ndarray:
    """Sudut dalam derajat, kolom roll, pitch, yaw.

    Accel dalam g, gyro dalam °/s. Magnetometer tidak dipakai.
    Yaw relatif, bukan heading kompas.
    """
    n = int(len(time_s))
    out = np.full((n, 3), np.nan, dtype=np.float64)
    if n < 2:
        return out

    from ahrs.filters import Madgwick
    from scipy.spatial.transform import Rotation

    acc_g = np.asarray(accel_g, dtype=np.float64) * _AXIS
    gyr_rads = np.deg2rad(np.asarray(gyro_dps, dtype=np.float64)) * _AXIS
    acc_ms2 = -acc_g * G
    dt = np.diff(np.asarray(time_s, dtype=np.float64))
    dt = dt[dt > 0]
    if dt.size == 0:
        return out
    frequency = 1.0 / float(np.median(dt))
    filt = Madgwick(gyr=gyr_rads, acc=acc_ms2, frequency=frequency)
    q_xyzw = np.column_stack([filt.Q[:, 1], filt.Q[:, 2], filt.Q[:, 3], filt.Q[:, 0]])
    euler = Rotation.from_quat(q_xyzw).as_euler("ZYX", degrees=True)
    out[:, 0] = euler[:, 2]
    out[:, 1] = euler[:, 1]
    out[:, 2] = euler[:, 0]
    return out

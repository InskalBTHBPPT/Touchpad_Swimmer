"""Roll, pitch, yaw. Madgwick atau EKF, 6 sumbu atau 9 sumbu."""

from __future__ import annotations

import numpy as np

G = 9.80665
# X tetap, Y dan Z dibalik. Sama catatan uji vs 3DM-GX5-25.
_AXIS = np.array([1.0, -1.0, -1.0])


def madgwick_rpy_deg(time_s: np.ndarray, accel_g: np.ndarray, gyro_dps: np.ndarray) -> np.ndarray:
    """Madgwick 6 sumbu. Accel dalam g, gyro dalam °/s."""
    return attitude_rpy_deg(time_s, accel_g, gyro_dps, method="madgwick", axes=6)


def attitude_rpy_deg(
    time_s: np.ndarray,
    accel_g: np.ndarray,
    gyro_dps: np.ndarray,
    mag_uT: np.ndarray | None = None,
    method: str = "madgwick",
    axes: int = 6,
) -> np.ndarray:
    """Sudut dalam derajat, kolom roll, pitch, yaw.

    Accel dalam g, gyro dalam °/s, magnetometer dalam µT.
    axes 6 memakai accel dan gyro. axes 9 menambahkan magnetometer.
    Yaw 6 sumbu relatif. Yaw 9 sumbu mengikuti arah medan magnet mentah.
    """
    n = int(len(time_s))
    out = np.full((n, 3), np.nan, dtype=np.float64)
    if n < 2:
        return out
    if axes not in (6, 9):
        raise ValueError(f"Jumlah sumbu harus 6 atau 9, dapat {axes}")
    name = method.strip().lower()
    if name not in ("madgwick", "ekf"):
        raise ValueError(f"Filter harus madgwick atau ekf, dapat {method}")
    if axes == 9 and mag_uT is None:
        raise ValueError("Magnetometer diperlukan untuk 9 sumbu")

    from scipy.spatial.transform import Rotation

    acc_g = np.asarray(accel_g, dtype=np.float64) * _AXIS
    gyr_rads = np.deg2rad(np.asarray(gyro_dps, dtype=np.float64)) * _AXIS
    acc_ms2 = -acc_g * G
    dt = np.diff(np.asarray(time_s, dtype=np.float64))
    dt = dt[dt > 0]
    if dt.size == 0:
        return out
    frequency = 1.0 / float(np.median(dt))
    kwargs = {"gyr": gyr_rads, "acc": acc_ms2, "frequency": frequency}
    if axes == 9:
        kwargs["mag"] = np.asarray(mag_uT, dtype=np.float64) * _AXIS
    if name == "madgwick":
        from ahrs.filters import Madgwick

        filt = Madgwick(**kwargs)
    else:
        from ahrs.filters import EKF

        filt = EKF(**kwargs)
    q_xyzw = np.column_stack([filt.Q[:, 1], filt.Q[:, 2], filt.Q[:, 3], filt.Q[:, 0]])
    euler = Rotation.from_quat(q_xyzw).as_euler("ZYX", degrees=True)
    out[:, 0] = euler[:, 2]
    out[:, 1] = euler[:, 1]
    out[:, 2] = euler[:, 0]
    return out

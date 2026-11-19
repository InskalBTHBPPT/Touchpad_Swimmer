"""Roll, pitch, yaw. Madgwick atau EKF, 6 sumbu atau 9 sumbu."""

from __future__ import annotations

import numpy as np

G = 9.80665
# X tetap, Y dan Z dibalik. Sama catatan uji vs 3DM-GX5-25.
_AXIS = np.array([1.0, -1.0, -1.0])
# Jendela diam: |gyro| di bawah 1,5 °/s, |accel| dekat 1 g, minimal 1 detik.
_STILL_GYRO_DPS = 1.5
_STILL_ACC_MIN_G = 0.85
_STILL_ACC_MAX_G = 1.15
_STILL_MIN_S = 1.0


def gyro_bias_hold(time_s: np.ndarray, accel_g: np.ndarray, gyro_dps: np.ndarray) -> np.ndarray:
    """Gyro dalam °/s setelah bias dikurangi. Saat diam, keluaran nol.

    Bias tiga sumbu adalah rata-rata gyro pada jendela diam yang baru selesai.
    Sampel sebelum jendela pertama memakai bias nol.
    """
    gyr = np.asarray(gyro_dps, dtype=np.float64)
    acc = np.asarray(accel_g, dtype=np.float64)
    t = np.asarray(time_s, dtype=np.float64)
    rate = np.linalg.norm(gyr, axis=1)
    amag = np.linalg.norm(acc, axis=1)
    still = (rate < _STILL_GYRO_DPS) & (amag > _STILL_ACC_MIN_G) & (amag < _STILL_ACC_MAX_G)
    bias = np.zeros(3, dtype=np.float64)
    seg_start = None
    gyr_use = np.zeros_like(gyr)
    for i, on in enumerate(still):
        if on and seg_start is None:
            seg_start = i
        if (not on) and seg_start is not None:
            if t[i - 1] - t[seg_start] >= _STILL_MIN_S:
                bias = gyr[seg_start:i].mean(axis=0)
            seg_start = None
        gyr_use[i] = 0.0 if on else gyr[i] - bias
    return gyr_use


def madgwick_rpy_deg(
    time_s: np.ndarray,
    accel_g: np.ndarray,
    gyro_dps: np.ndarray,
    correct_bias: bool = False,
) -> np.ndarray:
    """Madgwick 6 sumbu. Accel dalam g, gyro dalam °/s."""
    return attitude_rpy_deg(
        time_s, accel_g, gyro_dps, method="madgwick", axes=6, correct_bias=correct_bias
    )


def attitude_rpy_deg(
    time_s: np.ndarray,
    accel_g: np.ndarray,
    gyro_dps: np.ndarray,
    mag_uT: np.ndarray | None = None,
    method: str = "madgwick",
    axes: int = 6,
    correct_bias: bool = False,
) -> np.ndarray:
    """Sudut dalam derajat, kolom roll, pitch, yaw.

    Accel dalam g, gyro dalam °/s, magnetometer dalam µT.
    axes 6 memakai accel dan gyro. axes 9 menambahkan magnetometer.
    Yaw 6 sumbu relatif. Yaw 9 sumbu mengikuti arah medan magnet mentah.
    correct_bias mengurangi bias gyro dari jendela diam dan menahan yaw saat diam.
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

    gyro = np.asarray(gyro_dps, dtype=np.float64)
    if correct_bias:
        gyro = gyro_bias_hold(time_s, accel_g, gyro)
    acc_g = np.asarray(accel_g, dtype=np.float64) * _AXIS
    gyr_rads = np.deg2rad(gyro) * _AXIS
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

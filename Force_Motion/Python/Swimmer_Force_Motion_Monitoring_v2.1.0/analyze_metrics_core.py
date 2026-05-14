"""
Perhitungan metrik rekaman (waktu + spektrum) untuk **Analisa multifile** (v2.1.0).

``compute_recording_metrics`` memakai definisi FFT / Welch yang selaras dengan
implementasi spektrum di tab **Analisa** satu berkas (``analyze_single_file_tab``).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np
from scipy import signal


def estimate_sample_rate_hz(ts: list[float]) -> float:
    """Perkiraan fs dari median Δt antar sampel (robust untuk jitter kecil)."""
    if len(ts) < 2:
        return 1.0
    dts: list[float] = []
    for i in range(len(ts) - 1):
        dt = float(ts[i + 1]) - float(ts[i])
        if dt > 1e-9:
            dts.append(dt)
    if not dts:
        return 1.0
    dt_med = statistics.median(dts)
    return 1.0 / dt_med if dt_med > 1e-12 else 1.0


def spectrum_fft_bins(y: list[float], fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Frekuensi (Hz) dan magnitudo satu sisi (DC dihilangkan)."""
    x = np.asarray(y, dtype=np.float64)
    n = int(x.size)
    if n < 2 or fs_hz <= 0:
        return np.array([]), np.array([])
    x = x - np.mean(x)
    win = np.hanning(n)
    xw = x * win
    spec = np.abs(np.fft.rfft(xw))
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    wsum = float(np.sum(win))
    if wsum > 1e-12:
        spec = spec / wsum
    if spec.size > 1:
        spec[1:-1] *= 2.0
    return freqs[1:], spec[1:]


def spectrum_welch_bins(y: list[float], fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD (linear); skip f≈0."""
    x = np.asarray(y, dtype=np.float64)
    n = int(x.size)
    if n < 4 or fs_hz <= 0:
        return np.array([]), np.array([])
    x = x - np.mean(x)
    nperseg = min(max(8, n // 4), 1024, n)
    if nperseg > n:
        nperseg = n
    if nperseg < 4:
        return np.array([]), np.array([])
    nover = min(nperseg // 2, nperseg - 1)
    f, pxx = signal.welch(
        x,
        fs=fs_hz,
        window="hann",
        nperseg=nperseg,
        noverlap=nover,
        scaling="density",
        detrend=False,
    )
    if f.size > 1:
        return f[1:], pxx[1:]
    return np.array([]), np.array([])


def spectrum_peak_frequency_hz(y: list[float], fs_hz: float, *, use_welch: bool) -> float | None:
    if use_welch:
        fq, mag = spectrum_welch_bins(y, fs_hz)
    else:
        fq, mag = spectrum_fft_bins(y, fs_hz)
    if fq.size == 0:
        return None
    imax = int(np.argmax(mag))
    return float(fq[imax])


def _argmin_first(vals: list[float]) -> int:
    return min(range(len(vals)), key=lambda i: vals[i])


def _argmax_first(vals: list[float]) -> int:
    return max(range(len(vals)), key=lambda i: vals[i])


@dataclass(frozen=True)
class RecordingMetrics:
    timestamp_start_s: float
    force_max_kg: float
    force_max_t_s: float
    dom_freq_force_hz: float | None
    roll_max_deg: float
    roll_max_t_s: float
    roll_min_deg: float
    roll_min_t_s: float
    dom_freq_roll_hz: float | None
    pitch_max_deg: float
    pitch_max_t_s: float
    pitch_min_deg: float
    pitch_min_t_s: float
    dom_freq_pitch_hz: float | None
    spectrum_method_label: str


def compute_recording_metrics(
    ts_list: list[float],
    f_list: list[float],
    r_list: list[float],
    p_list: list[float],
    *,
    use_welch: bool,
) -> RecordingMetrics:
    """Hitung metrik untuk satu rekaman (sama definisi dengan tab Analisa satu berkas)."""
    n = len(ts_list)
    if n == 0:
        raise ValueError("Deret kosong")

    i_fmax = _argmax_first(f_list)
    i_rmin = _argmin_first(r_list)
    i_rmax = _argmax_first(r_list)
    i_pmin = _argmin_first(p_list)
    i_pmax = _argmax_first(p_list)

    t_start = float(min(ts_list))
    fs = estimate_sample_rate_hz(ts_list)
    method_label = "Welch PSD" if use_welch else "FFT"

    return RecordingMetrics(
        timestamp_start_s=t_start,
        force_max_kg=float(f_list[i_fmax]),
        force_max_t_s=float(ts_list[i_fmax]),
        dom_freq_force_hz=spectrum_peak_frequency_hz(f_list, fs, use_welch=use_welch),
        roll_max_deg=float(r_list[i_rmax]),
        roll_max_t_s=float(ts_list[i_rmax]),
        roll_min_deg=float(r_list[i_rmin]),
        roll_min_t_s=float(ts_list[i_rmin]),
        dom_freq_roll_hz=spectrum_peak_frequency_hz(r_list, fs, use_welch=use_welch),
        pitch_max_deg=float(p_list[i_pmax]),
        pitch_max_t_s=float(ts_list[i_pmax]),
        pitch_min_deg=float(p_list[i_pmin]),
        pitch_min_t_s=float(ts_list[i_pmin]),
        dom_freq_pitch_hz=spectrum_peak_frequency_hz(p_list, fs, use_welch=use_welch),
        spectrum_method_label=method_label,
    )

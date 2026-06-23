"""
Perhitungan metrik rekaman (waktu + spektrum) untuk **Analisa multifile** (v2.2.0).

``compute_recording_metrics`` memakai definisi FFT / Welch yang selaras dengan
implementasi spektrum di tab **Analisa** satu berkas (``analyze_single_file_tab``).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np
from scipy import signal


GAP_LOSS_TOLERANCE_FACTOR = 1.5


def consecutive_deltas_s(ts: list[float]) -> list[float]:
    """Selisih TimeStamp(s) antar baris berurutan (hanya Δt > 0)."""
    dts: list[float] = []
    for i in range(len(ts) - 1):
        dt = float(ts[i + 1]) - float(ts[i])
        if dt > 1e-9:
            dts.append(dt)
    return dts


def median_dt_s(ts: list[float]) -> float | None:
    """Median Δt antar sampel; None jika tidak cukup data."""
    dts = consecutive_deltas_s(ts)
    if not dts:
        return None
    return float(statistics.median(dts))


def estimate_sample_rate_hz(ts: list[float]) -> float:
    """Perkiraan fs dari median Δt antar sampel (robust untuk jitter kecil)."""
    dt_med = median_dt_s(ts)
    if dt_med is None or dt_med <= 1e-12:
        return 1.0
    return 1.0 / dt_med


@dataclass(frozen=True)
class GapLossStats:
    """Estimasi sampel hilang dari gap timestamp CSV rekaman (bukan diagnosis LoRa)."""

    method_label: str
    method_key: str
    dt_nominal_s: float
    fs_hz: float
    samples_actual: int
    samples_lost: int
    loss_pct: float
    samples_expected: int | None = None
    gap_count: int | None = None


def compute_gap_loss(
    ts: list[float],
    *,
    method: str = "B",
    tolerance_factor: float = GAP_LOSS_TOLERANCE_FACTOR,
) -> GapLossStats | None:
    """
    Estimasi sampel hilang pada rekaman CSV.

    - **Metode A** (``method="A"``): per pasangan baris; jika Δt > toleransi × Δt_nominal,
      ``n_lost = round(Δt/Δt_nom) − 1`` dijumlahkan.
    - **Metode B** (``method="B"``): global; ``n_expected = round(durasi/Δt_nom)+1``,
      ``n_lost = max(0, n_expected − n_actual)``.

    ``Δt_nominal`` = median selisih timestamp antar baris berurutan.
    """
    if len(ts) < 2:
        return None
    dt_nom = median_dt_s(ts)
    if dt_nom is None or dt_nom <= 1e-12:
        return None

    fs_hz = 1.0 / dt_nom
    n_actual = len(ts)
    key = method.upper()
    if key not in ("A", "B"):
        key = "B"

    if key == "A":
        threshold = dt_nom * tolerance_factor
        total_lost = 0
        gap_count = 0
        for dt in consecutive_deltas_s(ts):
            if dt > threshold:
                total_lost += max(0, round(dt / dt_nom) - 1)
                gap_count += 1
        n_expected = n_actual + total_lost
        loss_pct = 100.0 * total_lost / n_expected if n_expected > 0 else 0.0
        return GapLossStats(
            method_label="Metode A — per gap",
            method_key="A",
            dt_nominal_s=dt_nom,
            fs_hz=fs_hz,
            samples_actual=n_actual,
            samples_lost=total_lost,
            loss_pct=loss_pct,
            gap_count=gap_count,
        )

    duration = float(ts[-1]) - float(ts[0])
    n_expected = int(round(duration / dt_nom)) + 1
    total_lost = max(0, n_expected - n_actual)
    loss_pct = 100.0 * total_lost / n_expected if n_expected > 0 else 0.0
    return GapLossStats(
        method_label="Metode B — global",
        method_key="B",
        dt_nominal_s=dt_nom,
        fs_hz=fs_hz,
        samples_actual=n_actual,
        samples_lost=total_lost,
        loss_pct=loss_pct,
        samples_expected=n_expected,
    )


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

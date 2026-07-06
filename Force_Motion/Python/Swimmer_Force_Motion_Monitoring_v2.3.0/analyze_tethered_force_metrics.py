"""
Metrik gaya tethered — peakF, meanF, minF, ImpF, TpeakF, DUR, RFD, dF, FI (global vs Andrade).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np
from scipy import signal

FORCE_STATS_METHOD_GLOBAL = "A"
FORCE_STATS_METHOD_ANDRADE = "B"

FORCE_STATS_METHOD_LABELS = {
    FORCE_STATS_METHOD_GLOBAL: "Global (Amaro / Carrasco-Poyatos)",
    FORCE_STATS_METHOD_ANDRADE: "Per siklus (Andrade)",
}

ANDRADE_FILTER_ORDER = 4
ANDRADE_FILTER_CUTOFF_DEFAULT_HZ = 7.0
_RFD_MIN_T_PEAK_S = 1e-9
FI_MIN_DURATION_S = 15.0
FI_WINDOW_S = 10.0
_DF_MIN_MEAN_KG = 1e-9


@dataclass(frozen=True)
class ForceTetheredStats:
    peak_f_kg: float
    mean_f_kg: float
    min_f_kg: float
    impulse_f_kg_s: float
    peak_t_s: float | None
    min_t_s: float | None
    t_peak_f_s: float | None
    dur_s: float | None
    rfd_kg_s: float | None
    df_pct: float | None
    fatigue_index_pct: float | None
    method_key: str
    method_label: str
    stroke_count: int | None = None
    used_fallback_global: bool = False
    andrade_filter_cutoff_hz: float | None = None


def _argmin_first(vals: list[float]) -> int:
    return min(range(len(vals)), key=lambda i: vals[i])


def _argmax_first(vals: list[float]) -> int:
    return max(range(len(vals)), key=lambda i: vals[i])


def _trapezoid_impulse_kg_s(ts: np.ndarray, f: np.ndarray) -> float:
    if len(ts) < 2 or len(f) < 2:
        return 0.0
    return float(np.trapezoid(f, ts))


def _intracyclic_df_pct(seg_f: np.ndarray) -> float | None:
    """Variasi gaya intrasiklus (Morouço et al., 2018; 2024 Pers. 5), sampling seragam."""
    if len(seg_f) < 2:
        return None
    f_mean = float(np.mean(seg_f))
    if abs(f_mean) < _DF_MIN_MEAN_KG:
        return None
    n = len(seg_f)
    rms_dev = float(np.sqrt(np.sum((seg_f - f_mean) ** 2) / n))
    return (rms_dev / f_mean) * 100.0


def compute_fatigue_index_pct(
    ts_list: list[float],
    f_list: list[float],
) -> float | None:
    """
    FI = (F_akhir / F_awal − 1) × 100 [%].
    F_awal / F_akhir = meanF pada jendela awal/akhir region (Morouço et al., 2012; 2024).
    """
    if len(ts_list) < 2 or len(f_list) < 2:
        return None
    ts_arr = np.asarray(ts_list, dtype=float)
    f_arr = np.asarray(f_list, dtype=float)
    duration_s = float(ts_arr[-1] - ts_arr[0])
    if duration_s < FI_MIN_DURATION_S:
        return None
    win_s = min(FI_WINDOW_S, duration_s / 3.0)
    t0 = float(ts_arr[0])
    t_end = float(ts_arr[-1])
    mask_start = ts_arr <= t0 + win_s
    mask_end = ts_arr >= t_end - win_s
    if not np.any(mask_start) or not np.any(mask_end):
        return None
    f_start = float(np.mean(f_arr[mask_start]))
    f_finish = float(np.mean(f_arr[mask_end]))
    if abs(f_start) < _DF_MIN_MEAN_KG:
        return None
    return (f_finish / f_start - 1.0) * 100.0


def butterworth_lowpass_force(
    f_arr: np.ndarray,
    fs_hz: float,
    cutoff_hz: float,
    *,
    order: int = ANDRADE_FILTER_ORDER,
) -> np.ndarray:
    """Low-pass Butterworth (filtfilt), selaras Andrade et al. (2018)."""
    if len(f_arr) < order * 3 + 1:
        return np.asarray(f_arr, dtype=float).copy()
    nyq = fs_hz / 2.0
    if cutoff_hz <= 0.0 or cutoff_hz >= nyq:
        return np.asarray(f_arr, dtype=float).copy()
    sos = signal.butter(order, cutoff_hz, btype="low", fs=fs_hz, output="sos")
    return signal.sosfiltfilt(sos, np.asarray(f_arr, dtype=float))


def compute_force_stats_global(ts_list: list[float], f_list: list[float]) -> ForceTetheredStats:
    ts_arr = np.asarray(ts_list, dtype=float)
    f_arr = np.asarray(f_list, dtype=float)
    i_max = _argmax_first(f_list)
    i_min = _argmin_first(f_list)
    return ForceTetheredStats(
        peak_f_kg=float(f_list[i_max]),
        mean_f_kg=float(statistics.mean(f_list)),
        min_f_kg=float(f_list[i_min]),
        impulse_f_kg_s=_trapezoid_impulse_kg_s(ts_arr, f_arr),
        peak_t_s=float(ts_list[i_max]),
        min_t_s=float(ts_list[i_min]),
        t_peak_f_s=None,
        dur_s=None,
        rfd_kg_s=None,
        df_pct=None,
        fatigue_index_pct=compute_fatigue_index_pct(ts_list, f_list),
        method_key=FORCE_STATS_METHOD_GLOBAL,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_GLOBAL],
        stroke_count=None,
        used_fallback_global=False,
        andrade_filter_cutoff_hz=None,
    )


def _detect_valley_indices(
    f_arr: np.ndarray,
    fs_hz: float,
    *,
    stroke_hz_hint: float | None,
) -> np.ndarray:
    n = len(f_arr)
    if n < 5:
        return np.array([], dtype=int)
    if stroke_hz_hint is not None and stroke_hz_hint > 0.05:
        min_dist = max(3, int(0.35 * fs_hz / stroke_hz_hint))
    else:
        min_dist = max(3, int(0.20 * fs_hz))
    span = float(np.ptp(f_arr))
    if span <= 1e-9:
        return np.array([], dtype=int)
    prominence = max(1e-6, 0.08 * span)
    valleys, _ = signal.find_peaks(-f_arr, distance=min_dist, prominence=prominence)
    return valleys


def _stats_from_stroke_segments(
    ts_arr: np.ndarray,
    f_arr: np.ndarray,
    valleys: np.ndarray,
    *,
    andrade_filter_cutoff_hz: float,
) -> ForceTetheredStats | None:
    peak_vals: list[float] = []
    mean_vals: list[float] = []
    min_vals: list[float] = []
    impulse_vals: list[float] = []
    t_peak_vals: list[float] = []
    dur_vals: list[float] = []
    rfd_vals: list[float] = []
    df_vals: list[float] = []
    for i in range(len(valleys) - 1):
        lo = int(valleys[i])
        hi = int(valleys[i + 1])
        if hi <= lo:
            continue
        seg_ts = ts_arr[lo : hi + 1]
        seg_f = f_arr[lo : hi + 1]
        if len(seg_f) < 2:
            continue
        peak_idx = int(np.argmax(seg_f))
        min_f = float(seg_f[0])
        peak_f = float(seg_f[peak_idx])
        t_peak_f = float(seg_ts[peak_idx] - seg_ts[0])
        dur = float(seg_ts[-1] - seg_ts[0])
        min_vals.append(min_f)
        peak_vals.append(peak_f)
        mean_vals.append(float(np.mean(seg_f)))
        impulse_vals.append(_trapezoid_impulse_kg_s(seg_ts, seg_f))
        t_peak_vals.append(t_peak_f)
        dur_vals.append(dur)
        if t_peak_f > _RFD_MIN_T_PEAK_S:
            rfd_vals.append((peak_f - min_f) / t_peak_f)
        df_i = _intracyclic_df_pct(seg_f)
        if df_i is not None:
            df_vals.append(df_i)

    if not peak_vals:
        return None

    return ForceTetheredStats(
        peak_f_kg=float(statistics.mean(peak_vals)),
        mean_f_kg=float(statistics.mean(mean_vals)),
        min_f_kg=float(statistics.mean(min_vals)),
        impulse_f_kg_s=float(statistics.mean(impulse_vals)),
        peak_t_s=None,
        min_t_s=None,
        t_peak_f_s=float(statistics.mean(t_peak_vals)),
        dur_s=float(statistics.mean(dur_vals)),
        rfd_kg_s=float(statistics.mean(rfd_vals)) if rfd_vals else None,
        df_pct=float(statistics.mean(df_vals)) if df_vals else None,
        fatigue_index_pct=None,
        method_key=FORCE_STATS_METHOD_ANDRADE,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_ANDRADE],
        stroke_count=len(peak_vals),
        used_fallback_global=False,
        andrade_filter_cutoff_hz=andrade_filter_cutoff_hz,
    )


def compute_force_stats_andrade(
    ts_list: list[float],
    f_list: list[float],
    fs_hz: float,
    *,
    stroke_hz_hint: float | None = None,
    filter_cutoff_hz: float = ANDRADE_FILTER_CUTOFF_DEFAULT_HZ,
) -> ForceTetheredStats:
    ts_arr = np.asarray(ts_list, dtype=float)
    f_arr = butterworth_lowpass_force(
        np.asarray(f_list, dtype=float),
        fs_hz,
        filter_cutoff_hz,
        order=ANDRADE_FILTER_ORDER,
    )
    valleys = _detect_valley_indices(f_arr, fs_hz, stroke_hz_hint=stroke_hz_hint)
    if len(valleys) < 2:
        return _fallback_andrade_global(ts_list, f_list)

    stats = _stats_from_stroke_segments(
        ts_arr,
        f_arr,
        valleys,
        andrade_filter_cutoff_hz=filter_cutoff_hz,
    )
    if stats is None:
        return _fallback_andrade_global(ts_list, f_list)
    fi = compute_fatigue_index_pct(ts_list, f_list)
    return ForceTetheredStats(
        peak_f_kg=stats.peak_f_kg,
        mean_f_kg=stats.mean_f_kg,
        min_f_kg=stats.min_f_kg,
        impulse_f_kg_s=stats.impulse_f_kg_s,
        peak_t_s=stats.peak_t_s,
        min_t_s=stats.min_t_s,
        t_peak_f_s=stats.t_peak_f_s,
        dur_s=stats.dur_s,
        rfd_kg_s=stats.rfd_kg_s,
        df_pct=stats.df_pct,
        fatigue_index_pct=fi,
        method_key=stats.method_key,
        method_label=stats.method_label,
        stroke_count=stats.stroke_count,
        used_fallback_global=stats.used_fallback_global,
        andrade_filter_cutoff_hz=stats.andrade_filter_cutoff_hz,
    )


def _fallback_andrade_global(
    ts_list: list[float], f_list: list[float]
) -> ForceTetheredStats:
    fallback = compute_force_stats_global(ts_list, f_list)
    return ForceTetheredStats(
        peak_f_kg=fallback.peak_f_kg,
        mean_f_kg=fallback.mean_f_kg,
        min_f_kg=fallback.min_f_kg,
        impulse_f_kg_s=fallback.impulse_f_kg_s,
        peak_t_s=None,
        min_t_s=None,
        t_peak_f_s=None,
        dur_s=None,
        rfd_kg_s=None,
        df_pct=None,
        fatigue_index_pct=compute_fatigue_index_pct(ts_list, f_list),
        method_key=FORCE_STATS_METHOD_ANDRADE,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_ANDRADE],
        stroke_count=0,
        used_fallback_global=True,
        andrade_filter_cutoff_hz=None,
    )


def compute_force_tethered_stats(
    ts_list: list[float],
    f_list: list[float],
    fs_hz: float,
    *,
    method: str = FORCE_STATS_METHOD_GLOBAL,
    stroke_hz_hint: float | None = None,
    andrade_filter_cutoff_hz: float = ANDRADE_FILTER_CUTOFF_DEFAULT_HZ,
) -> ForceTetheredStats:
    if method == FORCE_STATS_METHOD_ANDRADE:
        return compute_force_stats_andrade(
            ts_list,
            f_list,
            fs_hz,
            stroke_hz_hint=stroke_hz_hint,
            filter_cutoff_hz=andrade_filter_cutoff_hz,
        )
    return compute_force_stats_global(ts_list, f_list)

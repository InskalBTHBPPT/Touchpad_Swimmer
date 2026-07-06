"""
Metrik gaya tethered — peakF, meanF, minF, ImpF (global vs per siklus Andrade).
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


@dataclass(frozen=True)
class ForceTetheredStats:
    peak_f_kg: float
    mean_f_kg: float
    min_f_kg: float
    impulse_f_kg_s: float
    peak_t_s: float | None
    min_t_s: float | None
    method_key: str
    method_label: str
    stroke_count: int | None = None
    used_fallback_global: bool = False


def _argmin_first(vals: list[float]) -> int:
    return min(range(len(vals)), key=lambda i: vals[i])


def _argmax_first(vals: list[float]) -> int:
    return max(range(len(vals)), key=lambda i: vals[i])


def _trapezoid_impulse_kg_s(ts: np.ndarray, f: np.ndarray) -> float:
    if len(ts) < 2 or len(f) < 2:
        return 0.0
    return float(np.trapezoid(f, ts))


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
        method_key=FORCE_STATS_METHOD_GLOBAL,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_GLOBAL],
        stroke_count=None,
        used_fallback_global=False,
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
) -> ForceTetheredStats | None:
    peak_vals: list[float] = []
    mean_vals: list[float] = []
    min_vals: list[float] = []
    impulse_vals: list[float] = []
    for i in range(len(valleys) - 1):
        lo = int(valleys[i])
        hi = int(valleys[i + 1])
        if hi <= lo:
            continue
        seg_ts = ts_arr[lo : hi + 1]
        seg_f = f_arr[lo : hi + 1]
        if len(seg_f) < 2:
            continue
        min_vals.append(float(seg_f[0]))
        peak_vals.append(float(np.max(seg_f)))
        mean_vals.append(float(np.mean(seg_f)))
        impulse_vals.append(_trapezoid_impulse_kg_s(seg_ts, seg_f))

    if not peak_vals:
        return None

    return ForceTetheredStats(
        peak_f_kg=float(statistics.mean(peak_vals)),
        mean_f_kg=float(statistics.mean(mean_vals)),
        min_f_kg=float(statistics.mean(min_vals)),
        impulse_f_kg_s=float(statistics.mean(impulse_vals)),
        peak_t_s=None,
        min_t_s=None,
        method_key=FORCE_STATS_METHOD_ANDRADE,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_ANDRADE],
        stroke_count=len(peak_vals),
        used_fallback_global=False,
    )


def compute_force_stats_andrade(
    ts_list: list[float],
    f_list: list[float],
    fs_hz: float,
    *,
    stroke_hz_hint: float | None = None,
) -> ForceTetheredStats:
    ts_arr = np.asarray(ts_list, dtype=float)
    f_arr = np.asarray(f_list, dtype=float)
    valleys = _detect_valley_indices(f_arr, fs_hz, stroke_hz_hint=stroke_hz_hint)
    if len(valleys) < 2:
        return _fallback_andrade_global(ts_list, f_list)

    stats = _stats_from_stroke_segments(ts_arr, f_arr, valleys)
    if stats is None:
        return _fallback_andrade_global(ts_list, f_list)
    return stats


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
        method_key=FORCE_STATS_METHOD_ANDRADE,
        method_label=FORCE_STATS_METHOD_LABELS[FORCE_STATS_METHOD_ANDRADE],
        stroke_count=0,
        used_fallback_global=True,
    )


def compute_force_tethered_stats(
    ts_list: list[float],
    f_list: list[float],
    fs_hz: float,
    *,
    method: str = FORCE_STATS_METHOD_GLOBAL,
    stroke_hz_hint: float | None = None,
) -> ForceTetheredStats:
    if method == FORCE_STATS_METHOD_ANDRADE:
        return compute_force_stats_andrade(
            ts_list, f_list, fs_hz, stroke_hz_hint=stroke_hz_hint
        )
    return compute_force_stats_global(ts_list, f_list)

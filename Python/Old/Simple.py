import datetime as dt
import sys
from typing import Literal

import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration
from nidaqmx.errors import DaqFunctionNotSupportedError

# USB-6008: total AI ~10 kS/s terbagi antar saluran (cek datasheet untuk limit pasti).
RATE_HZ = 500.0
BUFFER_SIZE = 100_000
SAMPLES_PER_LOOP = int(RATE_HZ // 10)  # 1/10 rate → 50 sampel per iterasi

# Urutan = kolom print: timestamp, ai0, ai1 (timing task sama untuk semua saluran).
# DEVICE_CHANNELS = ("Dev2/ai0", "Dev2/ai1")
DEVICE_CHANNELS = ("Dev1/ai0", "Dev1/ai1")
AI_TERMINAL_CONFIG = TerminalConfiguration.DIFF
# None = loop tak terbatas (hentikan dengan Ctrl+C).
NUM_LOOPS = None

# "A" = timestamp manual: dt = 1/RATE_HZ, t0 = waktu PC saat task start (nominal).
# "B" = task.read_waveform(): t0 & dt dari AnalogWaveform.timing (mirip LabVIEW).
#       Jika driver NI-DAQmx terlalu lama (tanpa DAQmxInternalReadAnalogWaveformEx),
#       mode B otomatis fallback seperti A + TIME_PRINT_MODE_A (peringatan sekali).
READ_MODE: Literal["A", "B"] = "A"

# Hanya dipakai saat READ_MODE == "A", atau saat mode "B" fallback (driver tanpa read_waveform).
# "iso"          -> 2026-05-09T12:43:50.243578+07:00
# "relative_sec" -> 0, 0.002, 0.004, ... (detik nominal sejak task start)
TIME_PRINT_MODE_A: Literal["iso", "relative_sec"] = "relative_sec"


def _format_ts(
    time_print_mode: Literal["iso", "relative_sec"],
    sample_offset: int,
    i: int,
    t0_nominal: dt.datetime,
    dt_sample: dt.timedelta,
) -> str:
    if time_print_mode == "iso":
        ts = t0_nominal + dt_sample * (sample_offset + i)
        return ts.isoformat()
    if time_print_mode == "relative_sec":
        rel_s = (sample_offset + i) / RATE_HZ
        return f"{rel_s:g}"
    raise ValueError(
        f"TIME_PRINT_MODE_A tidak dikenal: {time_print_mode!r} "
        "(pakai 'iso' atau 'relative_sec')."
    )


def _print_dual_chunk(
    ai0: list[float],
    ai1: list[float],
    sample_offset: int,
    t0_nominal: dt.datetime,
    dt_sample: dt.timedelta,
    time_print_mode: Literal["iso", "relative_sec"],
) -> None:
    if len(ai0) != len(ai1):
        raise ValueError(
            f"Panjang saluran tidak sama: ai0={len(ai0)}, ai1={len(ai1)}"
        )
    for i in range(len(ai0)):
        ts = _format_ts(time_print_mode, sample_offset, i, t0_nominal, dt_sample)
        print(ts, float(ai0[i]), float(ai1[i]))


def _as_float_list(samples) -> list[float]:
    if hasattr(samples, "tolist"):
        return [float(x) for x in samples.tolist()]
    return [float(x) for x in samples]


with nidaqmx.Task() as task:
    for ch in DEVICE_CHANNELS:
        task.ai_channels.add_ai_voltage_chan(
            ch, terminal_config=AI_TERMINAL_CONFIG
        )
    task.timing.cfg_samp_clk_timing(
        rate=RATE_HZ,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=BUFFER_SIZE,
    )
    task.start()
    t0_nominal = dt.datetime.now().astimezone()
    sample_offset = 0
    dt_sample = dt.timedelta(seconds=1.0 / RATE_HZ)

    use_waveform_for_b = READ_MODE == "B"
    waveform_fallback_warned = False

    try:
        n = 0
        while NUM_LOOPS is None or n < NUM_LOOPS:
            if READ_MODE == "A":
                raw = task.read(number_of_samples_per_channel=SAMPLES_PER_LOOP)
                # GROUP_BY_CHANNEL: [[ai0...], [ai1...]]
                ai0_samples = raw[0]
                ai1_samples = raw[1]
                _print_dual_chunk(
                    ai0_samples,
                    ai1_samples,
                    sample_offset,
                    t0_nominal,
                    dt_sample,
                    TIME_PRINT_MODE_A,
                )
                sample_offset += len(ai0_samples)
            elif READ_MODE == "B":
                if use_waveform_for_b:
                    try:
                        wfms = task.read_waveform(
                            number_of_samples_per_channel=SAMPLES_PER_LOOP,
                        )
                    except DaqFunctionNotSupportedError:
                        if not waveform_fallback_warned:
                            print(
                                "Peringatan: read_waveform tidak didukung oleh "
                                "NI-DAQmx ini (butuh upgrade driver). "
                                "Fallback ke read() + TIME_PRINT_MODE_A. "
                                "Unduh driver terbaru: https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html#590033",
                                file=sys.stderr,
                            )
                            waveform_fallback_warned = True
                        use_waveform_for_b = False
                    else:
                        w0, w1 = wfms[0], wfms[1]
                        y0 = _as_float_list(w0.scaled_data)
                        y1 = _as_float_list(w1.scaled_data)
                        t0_w = w0.timing.start_time
                        dt_w = w0.timing.sample_interval
                        num = len(y0)
                        if len(y1) != num:
                            raise ValueError(
                                f"Waveform ai0/a1 beda panjang: {num} vs {len(y1)}"
                            )
                        for i in range(num):
                            if TIME_PRINT_MODE_A == "iso":
                                if t0_w is not None:
                                    ts_dt = t0_w + dt_w * i
                                else:
                                    ts_dt = (
                                        t0_nominal + dt_sample * (
                                            sample_offset + i))
                                ts_str = ts_dt.isoformat()
                            elif TIME_PRINT_MODE_A == "relative_sec":
                                ts_str = f"{(sample_offset + i) / RATE_HZ:g}"
                            else:
                                raise ValueError(
                                    f"TIME_PRINT_MODE_A tidak dikenal: "
                                    f"{TIME_PRINT_MODE_A!r}"
                                )
                            print(ts_str, y0[i], y1[i])
                        sample_offset += num
                        n += 1
                        continue

                if not use_waveform_for_b:
                    raw = task.read(
                        number_of_samples_per_channel=SAMPLES_PER_LOOP)
                    ai0_samples = raw[0]
                    ai1_samples = raw[1]
                    _print_dual_chunk(
                        ai0_samples,
                        ai1_samples,
                        sample_offset,
                        t0_nominal,
                        dt_sample,
                        TIME_PRINT_MODE_A,
                    )
                    sample_offset += len(ai0_samples)
            else:
                raise ValueError(
                    f"READ_MODE tidak dikenal: {READ_MODE!r} (pakai 'A' atau 'B')."
                )
            n += 1
    except KeyboardInterrupt:
        print("\nBerhenti (Ctrl+C).")
    finally:
        task.stop()

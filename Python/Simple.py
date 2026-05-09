import datetime as dt
import sys
from typing import Literal

import nidaqmx
from nidaqmx.constants import AcquisitionType
from nidaqmx.errors import DaqFunctionNotSupportedError

# USB-6008: total AI ~10 kS/s terbagi antar saluran (cek datasheet untuk limit pasti).
RATE_HZ = 500.0
BUFFER_SIZE = 100_000
SAMPLES_PER_LOOP = int(RATE_HZ // 10)  # 1/10 rate → 50 sampel per iterasi

DEVICE_CHANNEL = "Dev2/ai0"
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


def _print_samples_iso(timestamps: list[dt.datetime], values) -> None:
    for ts, value in zip(timestamps, values):
        print(ts.isoformat(), float(value))


def _print_chunk_like_mode_a(
    data,
    sample_offset: int,
    t0_nominal: dt.datetime,
    dt_sample: dt.timedelta,
    time_print_mode: Literal["iso", "relative_sec"],
) -> None:
    if time_print_mode == "iso":
        times = [
            t0_nominal + dt_sample * (sample_offset + i) for i in range(len(data))
        ]
        _print_samples_iso(times, data)
    elif time_print_mode == "relative_sec":
        for i, value in enumerate(data):
            rel_s = (sample_offset + i) / RATE_HZ
            print(f"{rel_s:g}", float(value))
    else:
        raise ValueError(
            f"TIME_PRINT_MODE_A tidak dikenal: {time_print_mode!r} "
            "(pakai 'iso' atau 'relative_sec')."
        )


with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(DEVICE_CHANNEL)
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
                data = task.read(number_of_samples_per_channel=SAMPLES_PER_LOOP)
                _print_chunk_like_mode_a(
                    data, sample_offset, t0_nominal, dt_sample, TIME_PRINT_MODE_A
                )
                sample_offset += len(data)
            elif READ_MODE == "B":
                if use_waveform_for_b:
                    try:
                        wfm = task.read_waveform(
                            number_of_samples_per_channel=SAMPLES_PER_LOOP,
                        )
                    except DaqFunctionNotSupportedError:
                        if not waveform_fallback_warned:
                            print(
                                "Peringatan: read_waveform tidak didukung oleh "
                                "NI-DAQmx ini (butuh upgrade driver). "
                                "Fallback ke read() + TIME_PRINT_MODE_A. "
                                "Unduh driver terbaru: https://www.ni.com/en/support/downloads/drivers.html",
                                file=sys.stderr,
                            )
                            waveform_fallback_warned = True
                        use_waveform_for_b = False
                        wfm = None
                    else:
                        y = wfm.scaled_data
                        t0_w = wfm.timing.start_time
                        dt_w = wfm.timing.sample_interval
                        if t0_w is None:
                            t0_w = t0_nominal + dt_sample * sample_offset
                        times = [t0_w + dt_w * i for i in range(len(y))]
                        _print_samples_iso(times, y)
                        sample_offset += len(y)
                        n += 1
                        continue

                if not use_waveform_for_b:
                    data = task.read(number_of_samples_per_channel=SAMPLES_PER_LOOP)
                    _print_chunk_like_mode_a(
                        data,
                        sample_offset,
                        t0_nominal,
                        dt_sample,
                        TIME_PRINT_MODE_A,
                    )
                    sample_offset += len(data)
            else:
                raise ValueError(f"READ_MODE tidak dikenal: {READ_MODE!r} (pakai 'A' atau 'B').")
            n += 1
    except KeyboardInterrupt:
        print("\nBerhenti (Ctrl+C).")
    finally:
        task.stop()

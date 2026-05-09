import datetime as dt
from typing import Literal

import nidaqmx
from nidaqmx.constants import AcquisitionType

# USB-6008: total AI ~10 kS/s terbagi antar saluran (cek datasheet untuk limit pasti).
RATE_HZ = 500.0
BUFFER_SIZE = 100_000
SAMPLES_PER_LOOP = int(RATE_HZ // 10)  # 1/10 rate → 50 sampel per iterasi

DEVICE_CHANNEL = "Dev2/ai0"
# None = loop tak terbatas (hentikan dengan Ctrl+C).
NUM_LOOPS = None

# "A" = timestamp manual: dt = 1/RATE_HZ, t0 = waktu PC saat task start (nominal).
# "B" = task.read_waveform(): t0 & dt dari AnalogWaveform.timing (mirip LabVIEW).
READ_MODE: Literal["A", "B"] = "A"


def _print_samples_with_time(timestamps: list[dt.datetime], values) -> None:
    for ts, value in zip(timestamps, values):
        print(ts.isoformat(), float(value))


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

    try:
        n = 0
        while NUM_LOOPS is None or n < NUM_LOOPS:
            if READ_MODE == "A":
                data = task.read(number_of_samples_per_channel=SAMPLES_PER_LOOP)
                times = [
                    t0_nominal + dt_sample * (sample_offset + i) for i in range(len(data))
                ]
                _print_samples_with_time(times, data)
                sample_offset += len(data)
            elif READ_MODE == "B":
                wfm = task.read_waveform(
                    number_of_samples_per_channel=SAMPLES_PER_LOOP,
                )
                y = wfm.scaled_data
                t0_w = wfm.timing.start_time
                dt_w = wfm.timing.sample_interval
                if t0_w is None:
                    t0_w = t0_nominal + dt_sample * sample_offset
                times = [t0_w + dt_w * i for i in range(len(y))]
                _print_samples_with_time(times, y)
                sample_offset += len(y)
            else:
                raise ValueError(f"READ_MODE tidak dikenal: {READ_MODE!r} (pakai 'A' atau 'B').")
            n += 1
    except KeyboardInterrupt:
        print("\nBerhenti (Ctrl+C).")
    finally:
        task.stop()

import nidaqmx
from nidaqmx.constants import AcquisitionType

# USB-6008: total AI ~10 kS/s terbagi antar saluran (cek datasheet untuk limit pasti).
RATE_HZ = 500.0
BUFFER_SIZE = 100_000
SAMPLES_PER_LOOP = int(RATE_HZ // 10)  # 1/10 rate → 50 sampel per iterasi

DEVICE_CHANNEL = "Dev2/ai0"
# None = loop tak terbatas (hentikan dengan Ctrl+C).
NUM_LOOPS = 10

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(DEVICE_CHANNEL)
    task.timing.cfg_samp_clk_timing(
        rate=RATE_HZ,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=BUFFER_SIZE,
    )
    task.start()
    try:
        n = 0
        while NUM_LOOPS is None or n < NUM_LOOPS:
            data = task.read(number_of_samples_per_channel=SAMPLES_PER_LOOP)
            n += 1
            print(n, len(data), data)
    except KeyboardInterrupt:
        print("\nBerhenti (Ctrl+C).")

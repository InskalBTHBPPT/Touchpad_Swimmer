import nidaqmx
from nidaqmx.constants import AcquisitionType

# Parameter rate (Hz) hanya berlaku setelah Anda mengatur timing sample clock.
# USB-6008: total AI ~10 kS/s terbagi antar saluran (cek datasheet untuk limit pasti).
RATE_HZ = 500.0
SAMPLES = 50

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev2/ai0")
    task.timing.cfg_samp_clk_timing(
        rate=RATE_HZ,
        sample_mode=AcquisitionType.CONTINUOUS,
        samps_per_chan=SAMPLES,
    )
    data = task.read(number_of_samples_per_channel=SAMPLES)
    print(data)

import numpy as np

d = 0.575  # m
C = 299_792_458.0  # m/s
tau = d / C  # s

fs = np.arange(80)
f_hz = 2402e6 + 1e6 * np.array(fs)

phi_delta = f_hz * tau
phi_fixed = phi_delta * 32768
phi_fractional = np.round(phi_fixed % 32768).astype(int)

# Generate a PCT correction array
c_array = "BLE_PHY_CS_PCT_CORRECTION_PER_CHANNEL: ((int16_t[80]){\n    "
for i, x in enumerate(phi_fractional):
    c_array += f"{str(-x)},"
    if i % 10 == 9:
        c_array += "\n    "
    else:
        c_array += " "

c_array += "\n})"

print(c_array)

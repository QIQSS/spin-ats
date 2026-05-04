# Compensation du montage
max_compensation_amp = 0.005
attenuation_db = 32
gain = 10**(attenuation_db/20)

# Pulses
gates = ["P1", "P2"]
points = { # p1, p2, time (ns)
    "zero_dc": [0, 0, 0],
    "init": [0.004, -0.004, 50_000],
    "load": [-0.002, 0.002, 16],
    "load_deep": [-0.005, 0.005, 16],
    "readout": [*(-0.00075, 0.00075), 20_000],
}


freq1, freq2 = 200e6, 300e6
amp1, amp2 = 10e-3, 10e-3
iq_phase1, iq_phase2 = 0, 0
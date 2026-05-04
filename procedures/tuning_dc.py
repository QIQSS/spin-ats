# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     notebook_metadata_filter: jupytext,-kernelspec
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
# ---

# %% [markdown]
# # librairies

# %%
# pyhegel header
from pyHegel.scipy_fortran_fix import fix_problem_new
fix_problem_new()
from pyHegel.commands import *
from pyHegel import instruments
_init_pyHegel_globals()

import datetime, os, time, sys
import matplotlib.pyplot as plt
import numpy as np
import json

from libs.dc_controller.dc_controller import load_voltages, dc_controller_in_thread

from libs.helpers import make_save_dict, make_load_dict, make_set_multi

path_manip = "D:/QBB16_spin_multimode"
save_dict = make_save_dict(f"{path_manip}/parameters/tensions_dc/")
load_dict = make_load_dict(f"{path_manip}/parameters/tensions_dc/")

def path():
    date = datetime.datetime.now().strftime("%Y%m%d")
    path = f"{path_manip}/data/{date}/"
    if not os.path.exists(path): os.mkdir(path)
    return path


# %% [markdown]
# # instruments

# %%
def try_load(instruments, add_to_global=True):
    results = {}
    g = globals()
    for name, constructor in instruments.items():
        try:
            inst = g[name]
            print(f"{name}: already loaded")
        except Exception as e:
            print(f"{name}: loading", end="")
            inst = constructor()
            sys.stdout.flush()
            print(f", ok")
            if add_to_global: g[name] = inst  # add to globals
            continue
        results[name] = inst
    return results

instruments_to_load = {
    "dmm": lambda: instruments.agilent_multi_34410A("USB0::0x2A8D::0x0101::MY57515472::0::INSTR"),
    "bi7": lambda: instruments.iTest_be214x("TCPIP::192.168.150.112::5025::SOCKET", slot=7),
    "bi9": lambda: instruments.iTest_be214x("TCPIP::192.168.150.112::5025::SOCKET", slot=9),
    "rh3": lambda: instruments.iTest_be2102("TCPIP::192.168.150.112::5025::SOCKET", slot=3),
    "rh5": lambda: instruments.iTest_be2102("TCPIP::192.168.150.112::5025::SOCKET", slot=5),
    "zi":  lambda: instruments.zurich_UHF("dev2949"),
    "bf":  lambda: instruments.bf_controller(),
}

loaded_instruments = try_load(instruments_to_load)

# %%
rf_demod0 = (zi.readval, dict(vals=['r', 'deg'], ch=0))
rf_demod1 = (zi.readval, dict(vals=['r', 'deg'], ch=1))
rf_demod2 = (zi.readval, dict(vals=['r', 'deg'], ch=2))
rf_demod3 = (zi.readval, dict(vals=['r', 'deg'], ch=3))
rf_demod4 = (zi.readval, dict(vals=['r', 'deg'], ch=4))
rf_demod5 = (zi.readval, dict(vals=['r', 'deg'], ch=5))
rf_demod6 = (zi.readval, dict(vals=['r', 'deg'], ch=6))
rf_demod7 = (zi.readval, dict(vals=['r', 'deg'], ch=7))

set((zi.demod_tc, dict(ch=1)), 2.5e-3)
set(zi.async_wait, 10e-3)

# %%
dmm_scale = instruments.ScalingDevice(dmm.readval, scale_factor=1e8, only_val=True, invert_trans=True)
dmm.nplc.set(1)

# %% [markdown]
# # Test de fuite à chaud 

# %%
bi7.current_channel.set(1)
bi7.slope.set(0.2)
bi7.level.set(0)
bi7.output_en.set(True)

# %%
print(dmm.readval.get())
print(dmm.readval.get(), bi7.meas_out_current.get())
bi7.ramp.set(0.1)
print(dmm.readval.get())
print(dmm.readval.get(), bi7.meas_out_current.get())
print(dmm.readval.get())
bi7.ramp.set(0)
print(dmm.readval.get(), bi7.meas_out_current.get())
print(dmm.readval.get())


# %% [markdown]
# # grilles devs

# %%
gate_devs = { # bilt only
    "S": instruments.NamedParamDevice(rh3, dict()),
    "LB": instruments.NamedParamDevice(bi7, dict(ch=2)),
    "ST": instruments.NamedParamDevice(bi7, dict(ch=1)),
    "RB": instruments.NamedParamDevice(bi7, dict(ch=3)),
    "P1": instruments.NamedParamDevice(bi9, dict(ch=1)),
    "B1": instruments.NamedParamDevice(bi9, dict(ch=2)),
    "P2": instruments.NamedParamDevice(bi9, dict(ch=3)),
    "B2": instruments.NamedParamDevice(bi9, dict(ch=4)),
    "R": instruments.NamedParamDevice(bi7, dict(ch=4)),
    "C": instruments.NamedParamDevice(rh5, dict()),
}
globals().update(gate_devs)

set_multi = make_set_multi(gate_devs)

def get_multi_bilt(
    attrs = ["output_en", "level", "slope", "range", "meas_out_current", "meas_out_volt"],
    gate_devs = gate_devs,
    v = 0
):
    lines = [["name"] + attrs]
    for name, dev in gate_devs.items():
        line = [name]
        for attr in attrs:
            value = "-"
            try:
                value = get(getattr(dev, attr))
                value = f"{value:g}"
            except Exception as e:
                if v > 0: print(f"Error for {name}: {dev}, {e}")
            line.append(value)
        lines.append(line)
    widths = [max(len(line[i]) for line in lines) for i in range(len(lines[0]))]
    for line in lines:
        print("".join(f"{val:^{widths[i]+2}}" for i, val in enumerate(line)))


# %%
get_multi_bilt()

# %% [markdown]
# # All zero

# %%
all_zero = load_dict("all_zero")
set_multi(all_zero)

# %% [markdown]
# # Ouvrir les bilts

# %%
if input("GROUNDER LA BREAKOUT ! "*10) != "oui": raise Exception("ground pls")
for name, dev in gate_devs.items():
    set(dev.level, 0)
    set(dev.output_en, False)
    set(dev.range, 12)
    set(dev.slope, 0.2)
    set(dev.output_en, True)

# %%
get_multi_bilt()

# %% [markdown]
# # Test du SET

# %%
voltages = load_dict("all_zero")
voltages.update({"S":1e-3, "ST":2, "RB": 2})
set_multi(voltages)

merge = ["LB"]
dev = instruments.logical.CopyDevice([(gate_devs[name]._instrument, gate_devs[name]._arg_dict) for name in merge])
sweep(dev, 2.0, 0.0, 61, out=[dmm_scale],
    filename=path()+f"%T_{''.join(merge)}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # RBLB

# %%
voltages = load_dict("all_zero")
voltages.update({"S":1e-3, "ST": 2.1, "C": 0})
set_multi(voltages)
name_x, name_y = "RB", "LB"
sweep_multi([(gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), (gate_devs[name_y]._instrument, gate_devs[name_y]._arg_dict)], 
    [.45, .45], 
    [.75, .75], 
    [21, 81],
    out=[dmm_scale],
    #out=[rf_demod0],
    updown="alternate",
    filename=path()+f"%T_{name_x}_{name_y}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # Trace ST

# %%
voltages = load_dict("all_zero")
voltages.update({"S": 1e-3, "ST":2.1, "RB": .65, "LB": .55})
set_multi(voltages)
name_x = "ST"
sweep((gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), 
    1.5, 1.8, 201, out=[dmm_scale],
    filename=path()+f"%T_{name_x}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # Diamants

# %%
voltages = load_dict("proche_double_dot")
set_multi(voltages)

# %%
name_x, name_y = "ST", "S"
sweep_multi([(gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), (gate_devs[name_y]._instrument, gate_devs[name_y]._arg_dict)], 
    [1.5, -5e-3], 
    [2.5, 5e-3], 
    [101, 51],
    out=[dmm_scale],
    updown="alternate",
    filename=path()+f"%T_{name_x}_{name_y}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # Test grilles dots

# %%
voltages = load_dict("test_grilles_dots")
set_multi(voltages)
name_x = "P1"
sweep((gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), 
    0, 2, 101, out=[dmm_scale],
    filename=path()+f"%T_{name_x}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # Simple dot

# %%
voltages = load_dict("proche_simple_dot")
set_multi(voltages)
name_x, name_y = "B2", "P2"
sweep_multi([(gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), (gate_devs[name_y]._instrument, gate_devs[name_y]._arg_dict)], 
    [.5, 0.8], 
    [-.5, 2], 
    [51, 101],
    out=[dmm_scale],
    updown="alternate",
    filename=path()+f"%T_{name_x}_{name_y}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # Double dot

# %%
voltages = load_dict("proche_double_dot")
set_multi(voltages)

# %%
name_x, name_y = "P1", "P2"
sweep_multi([(gate_devs[name_x]._instrument, gate_devs[name_x]._arg_dict), (gate_devs[name_y]._instrument, gate_devs[name_y]._arg_dict)], 
    [0.8, 0.8], 
    [2, 2], 
    [301, 301],
    out=[dmm_scale],
    updown="alternate",
    filename=path()+f"%T_{name_x}_{name_y}.txt", extra_conf=[str(voltages)],
)

# %% [markdown]
# # DC controller

# %%
# !! TODO: pas testé
thr = dc_controller_in_thread(load_dict("proche_double_dot"), set_multi, ["P1", "B1", "P2", "B2", "ST"])

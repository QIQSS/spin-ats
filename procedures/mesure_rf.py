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
# # Libs and instruments

# %%
# pyhegel header
from pyHegel.scipy_fortran_fix import fix_problem_new
fix_problem_new()
from pyHegel.commands import *
_init_pyHegel_globals()

import matplotlib.pyplot as plt
import numpy as np
import h5py

from libs.helpers import (
    make_load_dict, make_save_dict,
    sendSeqToAWG, ats_common_setup,
    ats_plot
)

from libs.pulses.Builder import Pulse, Segment, compensateAndEqualizeTime
from libs.pulses.Shapes import Ramp, Sine
from libs.videomode.videomode import VideoModeWindow, Sweep, interlace_array, sweep_file
# TODO: import sweep file from utils.files instead

from libs.utils.file_saving import (
    make_path_fn,
    expand_filename,
    get_cell_content,
    sweep_file,
    get_file_variables,
    get_file_code,
)
from libs.utils.spin_fit_analysis import (
    fit_slices,
    DistributionSTFitResult,
    find_iq_rotation
)

from libs.utils.plots import mk_extent

path_manip = "D:/QBB16_spin_multimode"
path = make_path_fn(path_manip+"/data")



# %%
awg = instruments.tektronix.tektronix_AWG('tcpip::AWG5200-XXXX.lan')
#zi = instruments.zurich_UHF("dev2949")
ats = instruments.ATSBoard(systemId=1, cardId=1)

# %% [markdown]
# # Videomode

# %%
import parameters.params as params_file
from parameters.params import *
# %matplotlib inline

readout_time = 30e-6
short_axis = Sweep.from_nbpts(5e-3, -5e-3, 81, "P2", 1, interlace=0)
long_axis = Sweep.from_nbpts(-5e-3, 5e-3, 101, "P1", 1, interlace=1)
##
pulse_short, pulse_long = Pulse(name="short"), Pulse(name="long")
pulse_long.add(duration=short_axis.nbpts * readout_time, offset=long_axis.points[0], mark=True)
pulse_short.add(duration = short_axis.nbpts * readout_time, waveform = Ramp(short_axis.start, short_axis.stop), mark=True)
for pts in long_axis.points[1:]:
    pulse_short.add(
        duration = short_axis.nbpts * readout_time,
        waveform = Ramp(short_axis.start, short_axis.stop),
    )
    pulse_long.add(
        duration = short_axis.nbpts * readout_time,
        offset = pts,
    )
#pulse_long.plot(pulse_short, sample_rate=1e6)
sr = 10e6
awg.sample_rate.set(sr)
sendSeqToAWG(awg, pulse_short, 1, pulse_sr=sr, gain=gain)
sendSeqToAWG(awg, pulse_long, 2, pulse_sr=sr, gain=gain)
awg.run(True)

# %% [markdown]
# ## test acq

# %%
short_axis.nbpts*long_axis.nbpts*readout_time*ats.sample_rate.get(), len(res)

# %%
ats.sample_rate.set(1e6)
ats.nbwindows.set(1)
ats.acquisition_length_sec.set(short_axis.nbpts*long_axis.nbpts*readout_time)
ats_common_setup(ats)

def acq(channel: str):
    res = ats.readval.get()
    res = np.array(res[channel]).flatten()
    return res
res = acq("A")
plt.plot(res[:-3])

# %%
ats.sample_rate.set(1e6)
ats.nbwindows.set(1)
ats.acquisition_length_sec.set(short_axis.nbpts*long_axis.nbpts*readout_time)
ats_common_setup(ats)

def acq(channel: str):
    res = ats.readval.get()

    res = np.array(res[channel]).flatten()
    res = res.reshape(long_axis.nbpts, -1)

    if short_axis.is_interlaced: res = interlace_array(res.T).T
    if long_axis.is_interlaced: res = interlace_array(res)
    return res
plt.imshow(acq("A"), aspect="auto", origin="lower")

# %% [markdown]
# ## run

# %%
# %gui qt

ats.sample_rate.set(sr)
ats.nbwindows.set(1)
ats.acquisition_length_sec.set(short_axis.nbpts*long_axis.nbpts*readout_time)
ats_common_setup(ats)

vm = VideoModeWindow.from_ats(ats, awg,
   save_path = path(),
   channel = "A",
   short_axis = short_axis,
   long_axis = long_axis,
   play = 1
)
vm2 = VideoModeWindow.from_ats(ats, awg,
   save_path = path(),
   channel = "B",
   short_axis = short_axis,
   long_axis = long_axis,
   play = 1
)


# %% [markdown]
# # Readout, position

# %%
import parameters.params as params_file
from parameters.params import *
# %matplotlib qt
p = points

# Parameters
n_detuning = 51

p1_list = np.linspace(-1.1e-3, 0e-3, n_detuning)
p2_list = -p1_list
############################

det_offsets = [p1_list, p2_list]
pulses = [Pulse(name=name) for name in gates]
[pulse.add(duration=100e-6) for pulse in pulses]

for level in zip(p1_list, p2_list):

    for i, pulse in enumerate(pulses):

        pulse.add(duration=1e-6)

        pulse.add(offset=p["init"][i], duration=p["init"][2]*1e-9)
        
        pulse.add(waveform=Ramp(pulse.segments[-1].offset, p["load"][i]), duration=10e-6)
        pulse.add(offset=p["load"][i], duration=p["load"][2]*1e-9)

        pulse.add(
            offset=level[i],
            duration=p["readout"][2]*1e-9, mark=True)

    compensateAndEqualizeTime(*pulses, max_compensation_amp)
#pulses[0].plot(*pulses[1:], wide='wider', sample_rate=1e6)

sr = 100e6
awg.sample_rate.set(sr)
sendSeqToAWG(awg, pulses[0], channel=1, gain=gain, pulse_sr=sr)
sendSeqToAWG(awg, pulses[1], channel=2, gain=gain, pulse_sr=sr)
sendSeqToAWG(awg, pulses[1], channel=3, gain=gain, pulse_sr=sr)
awg.run(False)

pulse_setup = get_cell_content()

# %%
# Demodulators
from parameters.params import *
ti = 1e-6
set((zi.demod_tc, dict(ch=0)), ti/5)
set((zi.demod_order, dict(ch=0)), 4)
set((zi.demod_osc_src, dict(ch=0)), 4)
set((zi.demod_en, dict(ch=0)), True)
set((zi.demod_phase, dict(ch=0)), iq_phase1)

set((zi.demod_tc, dict(ch=1)), ti/5)
set((zi.demod_order, dict(ch=1)), 4)
set((zi.demod_osc_src, dict(ch=1)), 5)
set((zi.demod_en, dict(ch=1)), True)
set((zi.demod_phase, dict(ch=1)), iq_phase2)
# Oscillators
set((zi.osc_freq, dict(ch=4)), freq1)
set((zi.sigouts_ampl_en, dict(ch=0, demod=4)), True)
set((zi.sigouts_ampl_Vp, dict(ch=0, demod=4)), amp1)

set((zi.osc_freq, dict(ch=5)), freq2)
set((zi.sigouts_ampl_en, dict(ch=0, demod=5)), True)
set((zi.sigouts_ampl_Vp, dict(ch=0, demod=5)), amp2)
# Aux out
set((zi.auxouts_output_sel, dict(ch=0)), "demodX")
set((zi.auxouts_demod_sel, dict(ch=0)), 0)
set((zi.auxouts_output_sel, dict(ch=1)), "demodY")
set((zi.auxouts_demod_sel, dict(ch=1)), 0)
# Signal output
set((zi.sigouts_en, dict(ch=0)), True)
set((zi.sigouts_50ohm_en, dict(ch=0)), False)

zurich_setup = get_cell_content()

# %%
import parameters.params as params_file
from parameters.params import *
# %matplotlib inline

n_avg = 70
ats_nb_window = (int(np.sqrt(n_avg*n_detuning))+1) * int(np.sqrt(n_avg*n_detuning))

ats.sample_rate.set(sr)
ats.nbwindows.set(n_avg*n_detuning)
ats.acquisition_length_sec.set(points["readout"][2]*1e-9)
ats.buffer_count.set(4)
ats.input_range.set(800)
ats_common_setup(ats)

awg.run(False)
ats.run_and_wait()
awg.run(True)
res = ats.readval_all.get()
awg.run(False)



# %%
data_new = np.array([np.array(res["A"]).flatten(), np.array(res["B"]).flatten()])
# %matplotlib qt
plt.figure()
plt.plot(data_new[0], label="A")
plt.plot(data_new[1], label="B")
plt.legend()

# %%
# Format ats result
data = np.array([np.array(res["A"]).flatten(), np.array(res["B"]).flatten()])
# data = data.reshape(2, -1, ats.samples_per_record.get()).mean(axis=-1)
data = data.reshape(2, -1, ats.samples_per_record.get())[:, :, -1]
n_acq = data.shape[1]
n_expected = n_avg * n_detuning
if n_acq > n_expected:
    data = data[:, :n_expected]
if n_acq < n_expected:
    data = data[:, :(n_acq // n_detuning)*n_detuning]
    data = data.reshape(2, -1, n_detuning)

# %%
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8,5))
ax1.imshow(data[0], aspect="auto", interpolation="none", origin="lower", extent=mk_extent(p1_list, n_avg))
ax2.imshow(data[1], aspect="auto", interpolation="none", origin="lower", extent=mk_extent(p1_list, n_avg))
[ax.set(xlabel="detuning level", ylabel="avg") for ax in (ax1, ax2)]
ax1.set_title("A"); ax2.set_title("B")

# %%
# SAVE
filename = expand_filename(path()+"%T_readout_point.hdf5")
print(filename)

with sweep_file(
    filename,
    axes_dict = dict(
        count = data[0].shape[0],
        detuning_axis = len(p1_list),
    ),
    outs_dict = dict(
        I = ["count", "detuning_axis"],
        Q = ["count", "detuning_axis"],
    ),
    metadata = dict(
        cell = get_cell_content(),
        zurich_setup = zurich_setup,
        pulse_setup = pulse_setup,
        params = get_file_code(params_file),
        p1_list = p1_list,
        p2_list = p2_list,
    )
) as f:
    f["data"]["I"][:] = data[0]
    f["data"]["Q"][:] = data[1]

# %% [markdown]
# ## analyse

# %%
# %matplotlib inline
# Chargement des données
with h5py.File(filename, 'r') as file:
    data_i, data_q = file["data/I"][:], file["data/Q"][:]
    p1_list, p2_list = file["meta"].attrs["p1_list"], file["meta"].attrs["p2_list"]
    n_count = file["data/count"].shape[0]
    n_detuning = file["data/detuning_axis"].shape[0]

# Calcul des histogrammes
hist, bins_i, bins_q = np.histogram2d(data_i.flatten(), data_q.flatten(), bins=100)
hist_i, hist_q = hist.sum(axis=1), hist.sum(axis=0)
bins_ic, bins_qc = (bins_i[1:] + bins_i[:-1]) / 2, (bins_q[1:] + bins_q[:-1]) / 2
theta = find_iq_rotation(data_i, data_q, iq_phase1, log_norm=False, verbosity=2)


# %%
# %matplotlib inline
detuning_idx = 30
hist_vs_detuning = np.apply_along_axis(lambda arr: np.histogram(arr, bins_i)[0],0, data_i)

fig, ax = plt.subplots(figsize=(8, 4), layout="tight")
im = ax.imshow(hist_vs_detuning, extent=mk_extent(n_detuning, bins_i), interpolation="none", aspect="auto", origin="lower")
ax.text(0, bins_i[0], "Odd", c="r", size=16)
ax.text(n_detuning, bins_i[0], "Even", c="r", ha="right", size=16)
ax.set(xlabel="Detuning index", ylabel="Histogram I")
ax.grid(alpha=0.5, ls="--", which="both", axis="x")
cb = fig.colorbar(im, ax=ax, label="Count")
ax.twiny().set(xlabel="P1 (V)", xlim=ax.get_xlim(), xticks=np.linspace(0, n_detuning - 1, 6, dtype=int), xticklabels=[f"{p1_list[i]:.4f}" for i in tick_positions])
ax.minorticks_on()
fig.suptitle(filename)
if detuning_idx is not None:
    vl = ax.axvline(detuning_idx, c="red", ls=":")
    print(f"Couple de détuning: (P1, P2) = ({round(p1_list[detuning_idx], 5)}, {round(p2_list[detuning_idx], 5)})")


# %% [markdown]
# # Readout, temps d'intégration

# %%
import parameters.params as params_file
from parameters.params import *
# %matplotlib inline

# Parameters
readout_total_time = 200e-6

############################
p = points
pulses = [Pulse(name=name) for name in gates]
for i, pulse in enumerate(pulses):
    pulse.add(duration=0e-3)

    pulse.add(offset=p["init"][i], duration=p["init"][2]*1e-9)
    
    pulse.add(waveform=Ramp(pulse.segments[-1].offset, p["load"][i]), duration=10e-6)
    pulse.add(offset=p["load"][i], duration=p["load"][2]*1e-9)

    pulse.add(offset=p["readout"][i], duration=readout_total_time, 
    waveform=Sine(1e5, .001, 0),
    mark=True)

compensateAndEqualizeTime(*pulses, max_compensation_amp)
pulses[0].plot(*pulses[1:], wide='wider', relative_time=True, sample_rate=1e6)

sr = 100e6
awg.sample_rate.set(sr)
sendSeqToAWG(awg, pulses[0], channel=1, gain=gain, pulse_sr=sr)
sendSeqToAWG(awg, pulses[1], channel=2, gain=gain, pulse_sr=sr)
sendSeqToAWG(awg, pulses[1], channel=3, gain=gain, pulse_sr=sr)

pulse_setup = get_cell_content()

# %%
# Demodulators
from parameters.params import *
ti = 1e-6

set((zi.demod_tc, dict(ch=0)), ti/5)
set((zi.demod_order, dict(ch=0)), 4)
set((zi.demod_osc_src, dict(ch=0)), 4)
set((zi.demod_en, dict(ch=0)), True)
set((zi.demod_phase, dict(ch=0)), phase1)

set((zi.demod_tc, dict(ch=1)), ti/5)
set((zi.demod_order, dict(ch=1)), 4)
set((zi.demod_osc_src, dict(ch=1)), 5)
set((zi.demod_en, dict(ch=1)), True)
set((zi.demod_phase, dict(ch=1)), phase2)
# Oscillators
set((zi.osc_freq, dict(ch=4)), freq1)
set((zi.sigouts_ampl_en, dict(ch=0, demod=4)), True)
set((zi.sigouts_ampl_Vp, dict(ch=0, demod=4)), amp1)

set((zi.osc_freq, dict(ch=5)), freq2)
set((zi.sigouts_ampl_en, dict(ch=0, demod=5)), True)
set((zi.sigouts_ampl_Vp, dict(ch=0, demod=5)), amp2)
# Aux out
set((zi.auxouts_output_sel, dict(ch=0)), "demodX")
set((zi.auxouts_demod_sel, dict(ch=0)), 0)
set((zi.auxouts_output_sel, dict(ch=1)), "demodY")
set((zi.auxouts_demod_sel, dict(ch=1)), 0)
# Signal output
set((zi.sigouts_en, dict(ch=0)), True)
set((zi.sigouts_50ohm_en, dict(ch=0)), False)

zurich_setup = get_cell_content()

# %%
import parameters.params as params_file
from parameters.params import *
# %matplotlib inline

n_avg = 1_000

ats.sample_rate.set(1e6)
ats.acquisition_length_sec.set(readout_total_time)
ats.nbwindows.set(n_avg)
ats.buffer_count.set(4)
ats_common_setup(ats)

awg.run(False)
ats.run_and_wait()
awg.run(True)
data = ats.readval_all.get()
awg.run(False)

# %%
# SAVE
filename = expand_filename(path()+"%T_readout_time.hdf5")

n_avg = ats.nbwindows.get()
pts_per_trace = ats.samples_per_record.get()

with sweep_file(
    filename,
    axes_dict = dict(
        count = n_avg,
        time_us = data["t"] * 1e6,
    ),
    outs_dict = dict(
        I = ["count", "time_us"],
        Q = ["count", "time_us"],
    ),
    metadata = dict(
        cell = get_cell_content(),
        zurich_setup = zurich_setup,
        pulse_setup = pulse_setup,
        params = get_file_code(params_file)
    )
) as f:
    f["data"]["I"][:] = np.array(data["A"]).reshape((n_avg, -1))
    f["data"]["Q"][:] = np.array(data["B"]).reshape((n_avg, -1))

# %% [markdown]
# ## analyse

# %%
moving_integration_width_us = 50

sl = slice(5, -2)
n_bins = 300

# Chargement des données
with h5py.File(filename, 'r') as file:
    data_i = file["data/I"][:, sl]
    time_list = file["data/time_us"][sl]

# Suppression des traces avec des blips
hist_tot, bins_tot = np.histogram(data_i.flatten(), bins=n_bins)
idx = np.argmax(hist_tot)
ridx = min(np.argmax(hist_tot[idx:] == 0) + idx + 10, len(bins_tot)-2)
lidx = max(idx - np.argmax(hist_tot[:idx][::-1] == 0) - 10, 0)

if hist_tot[ridx]: ridx = len(hist_tot)
if hist_tot[lidx]: lidx = 0

bins = bins_tot[lidx:ridx]

min_val = bins_tot[lidx]
max_val = bins_tot[ridx]
wrong_idx = ((min_val > data_i) | (data_i > max_val)).any(axis=1)
data_i = data_i[~wrong_idx]

print(f"Conservation de {data_i.shape[0]} / {len(wrong_idx)} traces.")

# Construction des données avec intégration cumulée et fenêtrée
dt = time_list[1] - time_list[0]
window_width = int(moving_integration_width_us // dt)

data_cum = data_i.cumsum(axis=1) / (np.arange(len(time_list)) + 1)

window = np.ones(window_width) / window_width
time_list_mov = np.convolve(time_list, window, mode="valid")
data_mov = np.apply_along_axis(lambda arr: np.convolve(arr, window, mode="valid"), 1, data_i)


# Calcul des histogrammes
hist_mov, bins = np.histogram(data_mov, bins=n_bins)
hist_cum, _ = np.histogram(data_cum, bins=bins)

bins_center = (bins[1:] + bins[:-1]) / 2

# Calcul des histogrammes en fonction du temps de readout
hist_cum_vs_time = np.apply_along_axis(
    lambda arr: np.histogram(arr, bins)[0], 0, data_cum)

hist_mov_vs_time = np.apply_along_axis(
    lambda arr: np.histogram(arr, bins)[0], 0, data_mov)

# %%
# %matplotlib inline

plt.figure(figsize=(5, 4))
plt.imshow(hist_cum_vs_time.T, extent=[*bins[[0, -1]], *time_list[[0, -1]]], interpolation="none", aspect="auto", origin="lower")
# plt.imshow(np.log10(hist_I_vs_time.T), extent=[*bins_i_cum[[0, -1]], *time_list[[0, -1]]], interpolation="none", aspect="auto", origin="lower")
plt.xlabel("Histogram I")
plt.ylabel("Integration time ($\mu$s)")
# plt.xlim(-0.0026, -0.0024)
cb = plt.colorbar(label="Count")
plt.tight_layout()


plt.figure(figsize=(5, 4))
plt.imshow(hist_mov_vs_time.T, extent=[*bins[[0, -1]], *time_list_mov[[0, -1]]], interpolation="none", aspect="auto", origin="lower")
plt.xlabel("Histogram I")
plt.ylabel("Time of the measurement ($\mu$s)")
# plt.xlim(-0.00605, -0.00575)
cb = plt.colorbar(label="Count")
plt.tight_layout()


# %%
# %matplotlib inline
default_time = 50e-6  # Temps d'intégration sur lequel se baser pour trouver les paramètres initiaux de fit
default_time_idx = int(default_time // (dt * 1e-6))  # Index correspondant à ce temps d'intégration
tranche = hist_cum_vs_time[:, default_time_idx]  # Tranche d'histogramme à ce temps d'intégration

default_res = DistributionSTFitResult.from_bins_hist(bins_center, tranche, compute_visibility=1, p0=None, verbosity=5)
p0 = default_res.popt

all_fits = [
    DistributionSTFitResult.from_bins_hist(bins_center, tranche, compute_visibility=True, p0=p0) for tranche in hist_cum_vs_time.T
]  # Fit des données pour tous les temps d'intégration

# Trouver le temps d'intégration avec la visibilité maximale
optimal_tm_index = max(
    range(len(all_fits)), 
    key=lambda i: all_fits[i].visibility if all_fits[i].visibility is not None else 0
)

optimal_tm = time_list[optimal_tm_index]
optimal_fit = all_fits[optimal_tm_index]

# # Notes: Les lignes suivantes tentent de remplacer les lignes commentées ci-dessus. Elles n'ont pas été testées!!!
# fit_results = fit_slices(hist_cum_vs_time, n_slices=1, resolution=1, bins=bins, arg_names=["visibility", "threshold"])
# optimal_tm_index = np.argmax(fit_results[0])
# optimal_tm = time_list[optimal_tm_index]
# opt_vis, opt_thr = fit_results[optimal_tm_index]

# Rapport des paramètres optimaux
print()
print("# # # # # # #")
print("Paramètres optimaux")
print(f"Temps d'intégration: {optimal_tm} us")
print(f"Visibilité: {optimal_fit.visibility*100:.1f}%")
print(f"Threshold: {optimal_fit.threshold} (u.a.)")

# Afficher les données
plt.figure(figsize=(6, 4))
vis = np.array([fit.visibility if fit.visibility is not None else np.nan for fit in all_fits])
plt.plot(time_list, vis, label="Visibility")
plt.scatter(time_list[optimal_tm_index], optimal_fit.visibility, marker="*", c="red", label=f"Optimal visibility: {optimal_fit.visibility*100:.4f}%")
plt.axvline(time_list[optimal_tm_index], c="grey", zorder=-1, linestyle='--')
plt.text(time_list[optimal_tm_index], np.nanmin(vis), f"${time_list[optimal_tm_index]}\mu s$", horizontalalignment="right")
plt.xlabel("Integration time (us)")
plt.ylabel("Visibility (%)")
plt.legend()
plt.tight_layout()


import json
import sys
import datetime
import os
from typing import Literal

from matplotlib import pyplot as plt

from pyHegel import commands as c

    
def make_save_dict(base_path) -> callable:
    def save_dict(dict_, filename, v=0):
        with open(f"{base_path}/{filename}.json", "w") as f:
            json.dump(dict_, fp=f, indent=2)
            if v>0: print(f.name, "saved.")
    return save_dict

def make_load_dict(base_path) -> callable:
    def load_dict(filename, v=0):
        if not filename.endswith(".json"): filename += ".json"
        with open(f"{base_path}/{filename}", 'r') as f:
            dict_ = json.load(f)
            if v>0: print(f.name, "loaded.")
            return dict_
    return load_dict

def make_set_multi(gates_dict: dict[str,"ph_device"]):
    """ créer une fonction qui prend en argument:
    {"P1":1, "B1":0.1} et execute `set` sur les device correspondants dans `gates_dict`
    """
    def set_multi(
            gate_to_voltage: dict[str,float], 
            gate_devs: dict[str,"ph_device"] = gates_dict,
            verbosity = 0,
            return_dict = True
        ):
        if verbosity == 1:
            print("Ramping voltages...")
            
        for gate, voltage in gate_to_voltage.items():
            dev = gate_devs[gate]
            if voltage is not None:
                if verbosity > 2:
                    print(f"Ramping {gate} to {voltage}")
                c.set(dev, voltage)

        if verbosity == 1:
            print(" Done!")
        if return_dict: return gate_to_voltage
    return set_multi
    
def sendSeqToAWG(awg, sequence,
                 channel=1,
                 gain=None,
                 pulse_sr=10e3, 
                 wv_name='waveform',
                 play_mode: Literal["CONTInuous", "TRIGgered"] = "CONTinuous",
                 open_channel=True,
                 round_nbpts_to_mod64=None,
    ):
    """ Stop the awg then send the sequence (object from Pulse library) to the awg.
    gain can be None and will be set to awg.gain if it exists or this value if not: 1/(0.02512)*0.4
    If run_after: it play the wave after sending it.
    nbpts_mod64: 'last' | 'zeros' | num, pad wave to be a multiple of 64.
    """
    wv_name += '_' + str(channel)
    wave = sequence.getWaveNormalized(pulse_sr)
    wave_max_val = max(abs(sequence.getWave(pulse_sr)))
    marks = sequence.getMarks(pulse_sr, val_low=1, val_high=-1)
    
    if round_nbpts_to_mod64:
        padding_val = {'zeros':0, 'last':wave[-1]}.get(round_nbpts_to_mod64, round_nbpts_to_mod64)
        
        nb_padding_points = 64 - (len(wave) % 64)
        wave = np.concatenate((wave, np.ones(nb_padding_points)*padding_val))
        marks = np.concatenate((marks, np.ones(nb_padding_points)*marks[-1]))
    
    if gain is None:
        print(f"Gain not given, taking 1")
        gain = 1
    
    ## On awg
    if awg.sample_rate.get() < pulse_sr:
        print(f"Warning: awg SR below pulse SR")

    awg.run(False)
    amp = 2*wave_max_val*gain
    if amp < 0.025:
        print(f"{amp=} too low")
    awg.waveform_create(wave, wv_name, sample_rate=pulse_sr, amplitude=amp, force=True)
    awg.waveform_marker_data.set(marks, wfname=wv_name)
    awg.list_waveforms.get() # update the list to avoid error after
    awg.channel_waveform.set(wv_name, ch=channel)
    
    if amp > 0.750:
        print(f"Warning: volt amplitude with gain above 750mV: {amp}V")
    awg.volt_ampl.set(amp, ch=channel)

        
    awg.current_channel.set(channel)
    awg.trigger_mode.set(play_mode)
    awg.current_wfname.set(wv_name)
    awg.output_en.set(open_channel)


def ats_common_setup(ats):
    # channels
    ats.impedance.set(50)
    ats.active_channels.set(['A','B'])
    
    # tiggers
    ats.trigger_channel_1.set("ext")
    ats.trigger_to_use.set("1")
    ats.trigger_level_1.set(500)
    ats.trigger_slope_1.set('ascend')
    ats.trigger_delay.set(0)
    
    ats.conf = lambda: {'sr':ats.sample_rate.get(), 'pts':ats.samples_per_record.get(), 't':ats.acquisition_length_sec.get()}
    ats.ConfigureBoard()

def ats_reformat_data(data):
    """ 
    - data: (4, N)
        [[win], [time], [a], [b]]
    Returns:
        array: 
    """
    pass


def ats_plot(data):
    if len(data) == 4:
        _, time, A, B = data
    else:
        time, A, B = data
    fig, ax = plt.subplots()
    ax.plot(time.flatten(), A.flatten(), label="A")
    ax.plot(time.flatten(), B.flatten(), label="B")
    ax.grid(alpha=.2, ls="--")
    ax.set(xlabel="time (s)", ylabel="signal (V?)")
    ax.legend()
    return fig, ax
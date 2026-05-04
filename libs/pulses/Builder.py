from .Shapes import *
from .ShapeCompensation import *
from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np

class Segment(object):
    """ A segment is a part of a pulse.
    It is by default a constant 0 for a duration of 0.1s.
    Attributes waveform and envelope are objects that have a getWave(sample_rate, duration) and getArea() method.
    Mark is a tuple (start, stop) that defines the part of the segment that is marked.
    """
    _id = 0
    name = 'segment'
    duration = 0.1
    offset = 0.
    mark = (0., 0.)
    waveform = None
    envelope = None
    sweep_dict = {}

    def __init__(self, duration=0, offset=0, waveform=None, envelope=None,
                mark=(0, 0), sweep_dict={}, name=None):
        self._id = Segment._id
        Segment._id += 1
        if name is None:
            self.name = 'segment_' + str(self._id)
        self.duration = duration
        self.offset = offset
        self.mark = mark
        if mark is True: self.mark = (0,1)
        if mark is False: self.mark = (0,0)
        self.waveform = waveform
        self.envelope = envelope
        self.sweep_dict = {key:val for key, val in sweep_dict.items()}

    def getWave(self, sample_rate, to_ramp_value=0.):
        """ Build and return the waveform of the segment defined as waveform * envelope + offset.
        """
        if self.duration == 0: return np.array([])
        if self.envelope is not None:
            envelope_wave = self.envelope.getWave(sample_rate, self.duration)
        else:
            envelope_wave = np.ones(int(self.duration*sample_rate))

        if self.waveform is not None:
            waveform_wave = self.waveform.getWave(sample_rate, self.duration)
        else:
            waveform_wave = np.zeros(int(self.duration*sample_rate))

        offset_wave = self.offset * np.ones(int(self.duration*sample_rate))

        return waveform_wave * envelope_wave + offset_wave
    
    def getArea(self):
        """ Returns the area of the segment.
        """
        duration = self.duration
        if self.envelope is None and self.waveform is None:
            return self.offset * duration
        if self.envelope is None:
            return self.waveform.getArea(duration) + self.offset * duration
        if self.waveform is None:
            return self.envelope.getArea(duration) + self.offset * duration
        return self.waveform.getArea(duration) * self.envelope.getArea(duration) + self.offset * duration
    
    def getMarks(self, sample_rate, val_low=0, val_high=1):
        marks = val_low * np.ones(int(self.duration*sample_rate))
        if self.mark[0] == self.mark[1]:
            return marks
        id_high_start = int(self.duration*sample_rate*self.mark[0])
        id_high_end = int(self.duration*sample_rate*self.mark[1])
        marks[id_high_start:id_high_end] = val_high
        return marks
    
    def __str__(self):
        # same as above but wrtie only if attribute is not None
        string = "Segment("
        if self.duration != 0:
            string += "duration=" + str(self.duration) + ", "
        if self.offset != 0:
            string += "offset=" + str(self.offset) + ", "
        if self.mark != (0., 0.):
            string += "mark=" + str(self.mark) + ", "
        if self.waveform is not None:
            string += "waveform=" + str(self.waveform) + ", "
        if self.envelope is not None:
            string += "envelope=" + str(self.envelope) + ", "
        if self.sweep_dict != {}:
            string += "sweep_dict=" + str(self.sweep_dict) + ", "
        string = string[:-2] + ")"
        return string


class Pulse(object):
    """ A pulse is a concatenation of Segments
    """

    def __init__(self, *segments, name='Pulse', inverse_mark=False, shape_comp=False):
        self.name = name
        self.segments = []
        self.duration = 0.
        self.addSegment(*segments)
        # a sequence is a repetition of pulses.
        self.nb_rep = 1 # for a sequence: the number of repetitions
        self.sub_pulse_seg_count = 0 # for a sequence: the number of segments in the original pulse
        self.compensate = 0. # for a sequence: the dc compensation value
        self.inverse_mark = inverse_mark # True to invert high marks and low marks
        self.shape_comp = shape_comp # if True, use the transfert function from ShapeCompensation when getWave
    
    def __str__(self):
        ret = "Pulse("
        for seg in self.segments:
            ret += str(seg) + ', '
        ret = ret[:-2] + ')'
        return ret
    
    def __getitem__(self, i):
        return self.segments[i]

    def add(self, *args, **kwargs):
        """
        **kwargs are given to Segment. Then it's added to the pulse.
        """
        seg = Segment(*args, **kwargs)
        self.addSegment(seg)
    
    def addSegment(self, *segments):
        """ give an instance of Segment, then it's added to the pulse """
        for segment in segments:
            self.segments.append(segment)
            self.duration += segment.duration
    
    def removeSegment(self, i_segment):
        """ remove a segment by its index """
        self.duration -= self.segments[i_segment].duration
        self.segments.pop(i_segment)
    
    def getWave(self, sample_rate, force_no_shape_comp=False):
        wave = np.array([])
        for segment in self.segments:
            wave = np.concatenate((wave, segment.getWave(sample_rate)))
        if self.shape_comp and not force_no_shape_comp:
            wave = computeVint(self.getTimestep(sample_rate, wave), wave)
        return wave

    def getWaveNormalized(self, sample_rate):
        wave = self.getWave(sample_rate)
        wave_min, wave_max = min(wave), max(wave)
        div = max(abs(wave_min), abs(wave_max))
        if div != 0.:
            wave /= div
        return wave
    
    def getMarks(self, sample_rate, val_low=-1, val_high=1):
        marks = np.array([])
        if self.inverse_mark: val_low, val_high = val_high, val_low
        for segment in self.segments:
            marks = np.concatenate((marks, segment.getMarks(sample_rate, val_low, val_high)))
        return marks
    
    def getMarkDuration(self, sample_rate):
        """ return the total duration of high marks """
        marks = self.getMarks(sample_rate, val_high=1)
        nbpts_high = len(np.where(marks==1)[0])
        return nbpts_high / sample_rate

    def getArea(self):
        return sum([seg.getArea() for seg in self.segments])
    
    def getTimestep(self, sample_rate, wave=None):
        """ return a list of time for each point of the wave.
        """
        return np.linspace(0., self.duration, len(self.getWave(sample_rate) if wave is None else wave))
    
    def getIndexes(self, sample_rate):
        """ Returns the indexes of the segments in the wave.
        """
        ret = []
        start = 0
        for seg in self.segments:
            end = start + len(seg.getWave(sample_rate))
            ret.append([start, end-1])
            start = end
        return ret
    
    def getSubPulse(self, i_sub_pulse):
        """ Returns a Pulse composed of the i_sub_pulse-th segment.
        """
        sub_pulse = Pulse()
        sub_pulse.segments = []
        segments = self.segments[i_sub_pulse*self.sub_pulse_seg_count:(i_sub_pulse+1)*self.sub_pulse_seg_count]
        sub_pulse.addSegment(*segments)
        return sub_pulse
    
    def addStep(self, duration, amplitude, mark=(0,0)):
        self.addSegment(Segment(duration=duration, offset=amplitude, mark=mark))
        
    def addRamp(self, duration, amplitude_start, amplitude_stop, offset=0, mark=(0,0)):
        """ less verbose way of adding a ramp.
        """
        self.addSegment(Segment(duration=duration, waveform=Ramp(amplitude_start, amplitude_stop), offset=offset, mark=mark))
    
    def addCompensationZeroMean(self, value, mark=(0,0), threshold=1e-20) -> Segment:
        area = self.getArea()
        if area < threshold:
            area = 0
        comp_time = abs(area/value)
        value = value if area < 0 else -value
        segment = Segment(duration=comp_time, offset=value, mark=mark)
        self.addSegment(segment)
        return segment
    
    def _genSequenceSweep(self, segments, nb_rep):
        """ Generate a dictionary of sweep values for each segment.
        """
        sweep_vals = {}
        for seg_i, seg in enumerate(segments):
            seg_sweep = {}
            for key, val in seg.sweep_dict.items():
                if key == 'mark':
                    # no mark sweep for now
                    pass
                elif key == 'waveform' or key == 'envelope':
                    for param_key, param_val in val.items():
                        seg_sweep[key] = {param_key : np.linspace(param_val[0], param_val[1], nb_rep)}
                else:
                    seg_sweep[key] = np.linspace(val[0], val[1], nb_rep)
            sweep_vals[seg_i] = seg_sweep
        return sweep_vals
    
    def _setSequenceSweep(self, segments, iteration, sweep_vals):
        for i_seg, sweep_val in sweep_vals.items():
            seg = segments[i_seg]
            for key, val in sweep_val.items():
                if key == 'mark':
                    seg.mark = (val['start'][iteration], val['stop'][iteration])
                elif key == 'waveform':
                    for param_key, param_val in val.items():
                        seg.waveform.parameters[param_key] = param_val[iteration]
                elif key == 'envelope':
                    for param_key, param_val in val.items():
                        seg.envelope.parameters[param_key] = param_val[iteration]
                elif key == 'duration':
                    seg.duration = val[iteration]
                elif key == 'offset':
                    seg.offset = val[iteration]

    def genSequence(self, nb_rep=1, compensate=0.):
        """ Generate another Pulse composed of a long sequence of segments
        """
        sequence = Pulse()
        sequence.segments = []
        sequence.compensate = compensate
        sequence.nb_rep = nb_rep
        sequence.sub_pulse_seg_count = len(self.segments)
        if compensate != 0.: sequence.sub_pulse_seg_count += 1
        sweep_vals = self._genSequenceSweep(self.segments, nb_rep)
        original_segments = deepcopy(self.segments)
        for rep in range(nb_rep):
            new_segments = deepcopy(original_segments)
            self._setSequenceSweep(new_segments, rep, sweep_vals)
            if compensate != 0.:
                comp_segment = self.addCompensationZeroMean(compensate, add=False)
                new_segments.append(comp_segment)
            sequence.addSegment(*new_segments)
        return sequence
        
    def genMarksOnly(self, name=''):
        """ return a copy of self with a constant 0 waveform """
        pulse = Pulse(name=name)
        for seg in self.segments:
            pulse.addSegment(Segment(duration=seg.duration, mark=seg.mark, offset=0))
        return pulse
    
    def plot(self, *other_pulses, sample_rate=10e5, **kwargs):
        if len(other_pulses) >0:
            pulses = [self] + list(other_pulses)
            plotXpulses(*pulses, sample_rate=sample_rate, **kwargs)
            return
        plotPulse(self, sample_rate, **kwargs)

    def compensateAndEqualizeTime(self, pulse2, value):
        compensateAndEqualizeTime(self, pulse2, value)
    def genPWLFile(self, sample_rate, filename):
        genPWLFile(self, sample_rate, filename)

def equalizeTime(pulse1, pulse2):
    len1, len2 = pulse1.duration, pulse2.duration
    diff = abs(len1-len2)
    if diff == 0: return
    if len1 < len2:
        pulse1.add(diff)
    elif len2 < len1:
        pulse2.add(diff)
    return
    
def compensateAndEqualizeTime(pulse1, pulse2, value):
    """ Add a dc compensation segment to each pulse and equalize their time with a 0 offset segment.
    """
    pulse1.addCompensationZeroMean(value)
    pulse2.addCompensationZeroMean(value)
    max_duration = max(pulse1.duration, pulse2.duration)
    if pulse1.duration < max_duration:
        p1_offset = Segment(duration=max_duration-pulse1.duration)
        pulse1.addSegment(p1_offset)
    elif pulse2.duration < max_duration:
        p2_offset = Segment(duration=max_duration-pulse2.duration)
        pulse2.addSegment(p2_offset)

def plotPulse(pulse, sample_rate=10e5, fig_axes=(None, None, None),
            highlight=[],
            superpose=False,
            no_shape_comp=True,
            plot_kwargs={},
            return_fig_axes=False,
            wide=False,
            relative_time=False):
    """Make a plot for pulse and its marker
    highlight is a list of index to color specified segments.
    superpose is for swept generated pulse
    Its simpler to call it via pulse.plot()
    For multiple pulses, use pulse.plot(*other_pulses) which call plotXpulses
    relative_time: start time axis (t=0) when marker is high
    """
    if None in fig_axes:
        figsize = {True:(8,2), 'wide':(8,2), 'wider':(16,2)}.get(wide, None)
        fig, [ax1, ax2] = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]}, figsize=figsize)
    else:
        fig, ax1, ax2 = fig_axes
    fig.suptitle('Pulse')
    ax1.grid(True); ax2.grid(True)
    ax2.set_xlabel('time (s)')

    wave = pulse.getWave(sample_rate, force_no_shape_comp=no_shape_comp)
    marks = pulse.getMarks(sample_rate)
    timestep = pulse.getTimestep(sample_rate)
    
    if relative_time:
        first_high = np.where(marks==1)[0][0]
        timestep -= timestep[first_high]

    custom_color = plot_kwargs.pop('color', None)
    wav_color = 'tab:blue' if custom_color is None else custom_color
    mar_color = 'orange' if custom_color is None else custom_color

    if superpose and pulse.sub_pulse_seg_count != 0:
        nb_sub_pulse = len(pulse.segments)//pulse.sub_pulse_seg_count
        for i_sub_pulse in range(nb_sub_pulse):
            alpha = 0.4 + 0.4*i_sub_pulse/nb_sub_pulse
            plotPulse(pulse.getSubPulse(i_sub_pulse), sample_rate, fig_axes=(fig, ax1, ax2),
                        highlight=[],
                        superpose=False,
                        plot_kwargs=dict(list(plot_kwargs.items())+[('alpha',alpha)]))
    else:
        ax1.plot(timestep, wave, color=wav_color, **plot_kwargs)
        ax2.plot(timestep, marks, color=mar_color, **plot_kwargs)

    if len(highlight)>0:
        indexes = pulse.getIndexes(sample_rate)
        for i_seg in highlight:
            if i_seg >= len(indexes):
                continue
            # highlight the i_seg-th segment
            # with indexes = [[seg1_start, seg1_end], [seg2_start, seg2_end], ...
            start = indexes[i_seg][0]
            end = indexes[i_seg][1]
            ax1.axvspan(timestep[start], timestep[end], alpha=0.15, color=wav_color)
            ax2.axvspan(timestep[start], timestep[end], alpha=0.15, color=mar_color)
    
    if return_fig_axes:
        return fig, ax1, ax2

def plotXpulses(*args, sample_rate=10e5, **kwargs):
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, pulse in enumerate(args):
        name = pulse.name + '_i' if pulse.name == 'Pulse' else pulse.name
        if i == 0:
            fig, ax1, ax2 = plotPulse(args[i], sample_rate, return_fig_axes=True, plot_kwargs={'color':colors[i%len(colors)], 'label':name}, **kwargs)
            continue
        plotPulse(pulse, sample_rate, fig_axes=(fig, ax1, ax2), plot_kwargs={'color':colors[i%len(colors)], 'label':name}, **kwargs)
    loc = kwargs.get('loc', 'upper right')
    ax1.legend(loc='upper right')

    
def genPWLFile(pulse, sample_rate, filename):
    """Generate a PWL file from a pulse and a sample rate, merging consecutive duplicate values."""
    # Get the waveform data
    wave = pulse.getWave(sample_rate)
    timelist = pulse.getTimestep(sample_rate)
    timestep = np.diff(timelist)[0]

    v_prev = wave[0]
    all_pairs = [ [0, wave[0]] ]
    
    for v in wave[1:]:
        if v == all_pairs[-1][1]:
            all_pairs[-1][0] += timestep
        else:
            all_pairs.append([timestep, v])
    
    all_pairs = [(t, v) for t, v in zip(timelist, wave)]
    #return all_pairs
    with open(filename, 'w') as file:
        for time, value in all_pairs:
            file.write(f'{time:.15f}\t {value:.15f}\n')
    
    print(f'PWL file "{filename}" ok')
    
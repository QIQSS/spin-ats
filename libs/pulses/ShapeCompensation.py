from scipy.fft import ifft, fft, fftfreq
import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
import warnings

# Used for pre-compensation.

# """ global utils """
# TODO: fix warning RuntimeWarning: divide by zero encountered in divide z_c = lambda w, c: -1.j/(w*c)

z_r = lambda w, r: r*np.ones_like(w)
z_c = lambda w, c: -1.j/(w*c) 

z_seri = lambda *args: np.sum(np.array(args), axis=0)
z_para = lambda *args: 1/ np.sum(1 / np.array(args), axis=0)

# """


def h(w, r5=50, c1=220e-9, re=9e6, ce=1e-12, r1=50e3, r2=1e3, r3=1, c2=220e-9, c3=220e-9, plot=False):
    """ main circuit """
    
    zdc = lambda w, re, ce, r1, r2, r3, c2, c3: z_para( z_r(w, re), z_c(w, ce), z_seri(z_r(w, r1), z_para(z_c(w, c2), z_seri(z_r(w, r2), z_para(z_c(w, c3), z_r(w, r3))))))
    zrf = lambda w, r5, c1: r5-1.j/(w*c1)

    zdc_ = zdc(w, re, ce, r1, r2, r3, c2, c3) 
    zrf_ = zrf(w, r5, c1)

    
    ret = zdc_ / (zrf_ + zdc_)
    
    if plot:
        plt.figure()
        plt.plot(w, ret, label='h')
        plt.legend()
        plt.show()
    return ret


def computeVint(timelist, voutt, h=h, *args, remove_dc_component=True, plot=False,
                save=False, filename='pulse_compensated.txt'):
    """ compute v_in(t) for a given v_out(t) and a transfert function h 
    v_in(t) = v_out(t) / h
    """
    warnings.filterwarnings('ignore', category=RuntimeWarning)

    f = fftfreq(len(timelist), timelist[1]-timelist[0])
    vow = fft(voutt)
    h_ = np.nan_to_num(h(2*np.pi*f, *args), nan=1e-6)
    
    viw = vow / h_
    vit = ifft(viw)
    
    if remove_dc_component:
        vit -= vit[0]
    
    if plot:
        plt.figure()
        plt.plot(timelist, vit, label='V_int')
        plt.plot(timelist, voutt, label='V_out')
        plt.legend()
        plt.show()
    
    if save:
        df = pd.DataFrame(dict(t=timelist, v=vit))
        df.to_csv(filename, index=False, sep="\t", header=False)
        
        

    warnings.filterwarnings('default', category=RuntimeWarning)
        
    return vit.real

Notes de manip.

Dispo:
QBB16 7A si28

TODO:
- [x] Videomode pulse
- [x] clean up code: -> helper libs/videomode
- [x] Videomode save file
- [x] save cell
- [x] pulse mesure de readout
- [x] calcul et rotation plan IQ
- [ ] ats:
    - [x] faster readval if possible
        - [x] enlever les np.concatenate dans self.get_data()
    - [x] fix chB bizarre
    - [ ] sauvegarde en temps réel pendant la mesure

- [ ] awg output: DC High BW or AC direct, difference ??

- [x] awg investiguer long temps d'envoie des pulses
- [x] vm: fermeture sans bug
- [ ] vm: fermeture sans bloquer ats (seulement en quand 2 vm)
- [ ] ats: points en trop en fin d'acquisition
- [x] git



# Installation librairie ATS
```
ats = instruments.ATSBoard()
RuntimeError: Unable to load atsapi Module. Make sure Alazartech SDKis installed: No module named 'atsapi'
```

Notre carte: ATS9462
AWG5204:
425 GS/s
4DC range dc
SEQ

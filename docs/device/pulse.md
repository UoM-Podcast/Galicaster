Pulse Device module configuration
=================================

Admitted values:
----------------

name: Name assigned to the device.
device: Device type: pulse
flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
location: PulseAudio source name. Use default to select the same Input as the Sound Control
file: The file name where the track will be recorded.
vumeter: Activates data sending to the program's vumeter. (True|False) Only one device should be activated.
amplification: Gstreamer amplification value: < 1 decreases and > 1 increases volume. Values between 1 and 2 are commonly used.
player: Wheter the audio will be previewed (played).

* To list PulseAudio devices run:

pactl list | grep "Source" -A 5

* Use "Name:" as the location field.

Examples
--------

[track1]
name = AudioSource
device = pulse
flavor = presenter
location = default
file = sound.mp3
active = True
vumeter = True
amplification = 2.0

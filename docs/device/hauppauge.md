Hauppauge Device module configuration
=====================================

Admitted values
---------------

name: Name assigned to the device.
device: Device type: hauppauge
flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
location: Device's mount point of the MPEG output.
locprevideo: Device's mount point of the RAW output.
locpreaudio: Device's mount point of the PCM output.
file: The file name where the track will be recorded.
vumeter: Whether the audio input would be represented on the vumeter. (True|False)
player: Whether the audio input would be played on preview. (True|False)

Examples:
---------

[track1]
name = Hauppauge
device = hauppauge
flavor = presenter
location = /dev/haucamera
locpreavideo = /dev/hauprevideo
locpreaudio = /dev/haupreaudio
file = CAMERA.mpg
vumeter = True
player = True


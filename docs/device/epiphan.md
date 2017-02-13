Epiphan Device module configuration
===================================

Note
----

Since drivers 3.27.7.5, epiphan USB and PCIe devices can be used as regular V4L2 devices with only addition of a proper caps string matching input resolution and target framerare.

Compatibility
-------------

Epiphan USB and PCI framegrabbers


Admitted values:
---------------

name: Name assigned to the device.
device: Device type: epiphan
flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
location: Device's mount point in the system (e.g. /dev/epiphan).
file: The file name where the track will be recorded.
drivertype: Wheter the device use a v4l2 or a v4l interface, to guarantee backwards compatibility (v4l2|v4l)
- As for Ubuntu 10.10 or similar use v4l.
resolution: Output resolution. If the input resolutino doesn't match the output, the input will be scaled respecting the ratio - by introducing black borders.
ramerate: Output framarate. If the input framerate doesn't match the output, frames will be dropped or duplicated accordingly.

Examples
--------

[track1]
name = DVI2PCIe
device = epiphan
flavor = presentation
location = /dev/screen
file = SCREEN.avi
resolution = 1024,768
framerate = 10/1
drivertype = v4l2

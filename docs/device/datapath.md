Datapath Device module configuration
================================

Note
----
This module is similar to the V4L2 module, with differences on the default parameters. In addition, pausing this module is blocked since the driver don't guarantee a proper recording when pausing and unplugging the input. Future drivers may solve this issue, then datapath cards could be used with the v4l2 device module.

Compatibility
------------

Datapath RGBVision series


Admitted values:
----------------

name: Name assigned to the device.
device: Device type: datapath
flavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
location: Device's mount point in the system (e.g. /dev/video0).
file: The file name where the track will be recorded. (The path is automatically assembled)
videocrop: Margin in pixels to be cutted. Useful to set a 4:3 proportion on a HD webcam.videocrop-top, videocrop-bottom, videocrop-left, videocrop-right (optional).
caps:  GStreamer cappabilities of the device. Check the caps section for more information.

* Use GVUCView tool to know wich capabilities are compatible with your device
* For more information  http://pygstdocs.berlios.de/pygst-tutorial/capabilities.html

Caps
----

Datapath is a V4L2 compatible device. V4L2 devices accepts two types of signal inputs - RAW and MJPEG - and multiple resolution-framerate combinations. A simplified Gstreamer cappabilities string is formed by type, resolution and framerate among other parameters:

- Type: image/jpeg or video/x-raw-yuv
- Framerate: X/Y. Examples: 30/1, 25/1, 24/1, 10/1
- Resolution: width=A,height=B. A and B being length in pixels

Then, a complete caps string looks like:
video/x-raw-yuv framerate=30/1, width=1280, height=1024

Examples:
---------

--Datapath RGB Vision 1es

[track1]
name = Datapath
device = datapath
location = /dev/datapath
file = SCREEN.avi
flavor = presentation
caps = video/x-raw-yuv,framerate=30/1,width=1280,height=1024

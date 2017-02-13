RTP Device module configuration
====================

Compatibility
-------------

MPEG or H264 sources with MP3 or ACC audio

Admitted values:
----------------

name: Name assigned to the device.
device: Device type: rtp
lavor: Opencast "flavor" associated to the track. (presenter|presentation|other)
location: URL to the RTP source. (e.g. rtsp://127.0.0.1:554/mpeg4).
file: The file name where the track will be recorded.
cameratype: Wheter the device streams a MPEG4 or H264 stream. (mpeg4|h264)
audio: Wheter the audio is recorded or not. (True|False)
audiotype: Audio format to capture, by default mp3. (acc|mp3)
vumeter: Activates data sending to the program's vumeter. (True|False) Only one device should be activated.
player: Whether the audio input would be played on preview. (True|False)
muxer: Muxer to encapsulate the stream. FLV by default, other options include mpegtsmux, avimux, mp4mux.


Examples
--------

* MPEG4-MPEGTS without audio

[track1]
name = AXIS 212PTZ
device = rtp
location = rtsp://127.0.0.1:554/mpeg4/media.amp
file = CAMERA.mpeg.ts
flavor = presenter
cameratype = mpeg4
audio = False
muxer= mpegtsmux

* H264-FLV with audio

[track1]
name = AXIS Q7404
device = rtp
location = rtsp://127.0.0.1:554/axis-media/media.amp?videocodec=h264
file = CAMERA.flv
flavor = presenter
cameratype = h264
audio = True
audiotype = mp3

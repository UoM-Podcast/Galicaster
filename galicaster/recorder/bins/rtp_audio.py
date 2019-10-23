# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/recorder/bins/rtp
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.
#
# TODO:
#  - Change mux. Dont use flvmux
#  - In cameratype mpeg4 dont use decodebin2
#

from gi.repository import Gst

from os import path

from galicaster.recorder import base
from galicaster.recorder.utils import get_audiosink


pipe_config_audio = {'mp3':
                         {'depay': 'rtpmpadepay', 'parse': 'mpegaudioparse', 'dec': 'avdec_mp3'},
                     'aac':
                         {'depay': 'rtpmp4gdepay', 'parse': 'aacparse', 'dec': 'faad'}}


audiostr = (' rtspsrc name=gc-rtpaudio-src ! gc-rtpaudio-audio-depay ! gc-rtpaudio-audioparse ! queue ! gc-rtpaudio-audio-dec !'
           ' tee name=tee-aud ! queue ! valve drop=false name=gc-rtpaudio-audio-valve ! '
           ' queue ! audioconvert ! gc-rtpaudio-enc ! queue ! filesink name=gc-rtpaudio-sink async=false'
           ' tee-aud. ! queue ! '
           ' level name=gc-rtpaudio-level message=true interval=100000000 ! '
           ' volume name=gc-rtpaudio-volume ! gc-asink ')



class GCrtp_audio(Gst.Bin, base.Base):


    order = ["name", "flavor", "location", "file", "audiotype", "vumeter", "player"]
    gc_parameters = {
        "name": {
            "type": "text",
            "default": "Webcam",
            "description": "Name assigned to the device",
            },
        "flavor": {
            "type": "flavor",
            "default": "presenter",
            "description": "Opencast flavor associated to the track",
            },
        "location": {
            "type": "text",
            "default": "rtsp://127.0.0.1/mpeg4/media.amp",
            "description": "Location of the RTSP url to read",
            },
        "file": {
            "type": "text",
            "default": "CAMERA.avi",
            "description": "The file name where the track will be recorded.",
            },
        "vumeter": {
            "type": "boolean",
            "default": "True",
            "description": "Activate Level message",
            },
        "player": {
            "type": "boolean",
            "default": "True",
            "description": "Enable sound play",
            },
        "audiotype": {
            "type": "select",
            "default": "mp3",
            "options": [
                "mp3", "aac"
                ],
            "description": "RTP Audio encoding type",
            },
        "audioencoder": {
            "type": "text",
            "default": "lamemp3enc target=1 bitrate=192 cbr=true",
            "description": "Gstreamer audio encoder element used in the bin",
        },
        "audiosink" : {
            "type": "select",
            "default": "alsasink",
            "options": ["autoaudiosink", "alsasink", "pulsesink", "fakesink"],
            "description": "Audio sink",
        },
    }

    is_pausable = False
    has_audio   = True
    has_video   = False

    __gstdetails__ = (
        "Galicaster RTP Audio Bin",
        "Generic/Audio",
        "Bin to capture RTP/RTSP audio",
        "Teltek Video Research",
        )

    def __init__(self, options={}):
        base.Base.__init__(self, options)
        Gst.Bin.__init__(self)

        gcaudiosink = get_audiosink(audiosink=self.options['audiosink'], name='sink-'+self.options['name'])

        aux = (audiostr.replace("gc-rtpaudio-audio-depay", pipe_config_audio[self.options['audiotype']]['depay'])
                .replace('gc-asink', gcaudiosink)
                .replace("gc-rtpaudio-enc", self.options["audioencoder"])
                .replace("gc-rtpaudio-audioparse", pipe_config_audio[self.options['audiotype']]['parse'])
                .replace("gc-rtpaudio-audio-dec", pipe_config_audio[self.options['audiotype']]['dec']))



        bin = Gst.parse_launch("( {} )".format(aux))
        self.add(bin)

        self.set_option_in_pipeline('location', 'gc-rtpaudio-src', 'location')
        self.set_value_in_pipeline(path.join(self.options['path'], self.options['file']), 'gc-rtpaudio-sink', 'location')
        if "player" in self.options and self.options["player"] == False:
            self.mute = True
            element = self.get_by_name("gc-rtpaudio-volume")
            element.set_property("mute", True)
        else:
            self.mute = False

        if "vumeter" in self.options:
            level = self.get_by_name("gc-rtpaudio-level")
            if self.options["vumeter"] == False:
                level.set_property("message", False)

    def changeValve(self, value):
        valve1=self.get_by_name('gc-rtpaudio-audio-valve')
        valve1.set_property('drop', value)


    def getAudioSink(self):
        return self.get_by_name('sink-audio-'+self.options['name'])

    def getSource(self):
        return self.get_by_name('gc-rtpaudio-src')

    def mute_preview(self, value):
        if not self.mute:
            element = self.get_by_name("gc-rtpaudio-volume")
            element.set_property("mute", value)

    def send_event_to_src(self, event):
        src1 = self.get_by_name('gc-rtpaudio-src')
        src1.send_event(event)

    def disable_preview(self):
        element = self.get_by_name("gc-rtpaudio-volume")
        element.set_property("mute", True)


    def enable_preview(self):
        element = self.get_by_name("gc-rtpaudio-volume")
        element.set_property("mute", False)

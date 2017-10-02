# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/failovermic
#
# Copyright (c) 2012, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.

"""This plugin will record an audio gstreamer pipeline of the specified device. if the audio file in the media package
is quite then it is replaced with the recorded audio file"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)

import os
import shutil
from galicaster.core import context
from galicaster.mediapackage import mediapackage

repo = context.get_repository()

# FAIL_DIR = os.path.join(repo.get_rectemp_path(), 'gc_failover')
FAILOVER_FILE = os.path.join(repo.get_rectemp_path(), 'failover.mp3')
FAILOVER_MIMETYPE = 'audio/mp3'
default_max_amplitude = '-50'
default_device = 'default'
default_track = '1'
rms_list = []
temp_amp = None

device = None
MAX_AMPLITUDE = None
audio_track = None
ampsd = True


def init():
    try:
        global MAX_AMPLITUDE
        global audio_track
        global pipe, bus
        global dispatcher, logger, repo, conf, recorder

        dispatcher = context.get_dispatcher()
        logger = context.get_logger()
        conf = context.get_conf()
        recorder = context.get_recorder()

        MAX_AMPLITUDE = conf.get('failovermic', 'failover_threshold')
        audio_track = conf.get('failovermic', 'audio_track')
        logger.info("Max amplutide: {}".format(MAX_AMPLITUDE))

        dispatcher.connect('timer-short', check_pipeline_amp)

    except ValueError:
        pass

def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

def check_pipeline_amp(self):
    global temp_amp, logger

    if context.get_recorder().is_recording():
        return
    else:
        amps = mean(context.get_recorder().get_audio_level())
        print amps
        print ampsd
        if amps <= -699:
            print 'no audio'
            ampsd = False
        else:
            ampsd = True

        # rms_list.append(rms)
        # if os.path.exists(temp_amp):
        #     f = open(temp_amp, 'a')
        # else:
        #     f = open(temp_amp, 'w')
        # if len(rms_list) > 100:
        #     value = str(max(rms_list))
        #     logger.debug("Writing data {} to {}".format(value, temp_amp))
        #     f.write(value + '\n')
        #     f.close()
        #     del rms_list[:]

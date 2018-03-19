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

        dispatcher.connect('recorder-vumeter', check_pipeline_amp)
        dispatcher.connect('recorder-stopped', save_failover_audio)
        # dispatcher.connect('recorder-starting', setup_failover_dir)

    except ValueError:
        pass


def get_audio_pathname():
    global conf
    audio_tracks = conf.get_current_profile().get_audio_tracks()
    if audio_tracks:
        return audio_tracks

    return None


def remove_temp(tmpf):
    if os.path.exists(tmpf):
        os.remove(tmpf)


def find_track_by_filename(mp):
    # FIXME using arbitrary range to loop through track identifiers, better to implement a mediapackage
    # function to find the idenfier based on track file name
    for i in range(0, 10):
        track = mp.getTrack('track-{}'.format(str(i)))
        if track.uri.split('/')[-1] == "failover.mp3":
            return 'track-{}'.format(str(i))


def save_failover_audio(self, mp_id):
    global repo, logger, temp_amp
    mp = repo.get(mp_id)
    mpUri = mp.getURI()
    #compare rms from pipeline with set threshold
    with open(temp_amp) as f:
        amp_list = f.readlines()
    f.close()

    if not amp_list:
        logger.debug("There is no amplification values, so nothing to do")
    else:
        pipeline_amp = float(max(amp_list))
        if MAX_AMPLITUDE is None:
            threshold = default_max_amplitude
        else:
            threshold = MAX_AMPLITUDE
        if pipeline_amp <= float(threshold):

            # if delayed don't finish the audio replacement yet
            if mp.getOpStatus('ingest') == mediapackage.OP_NIGHTLY:
                pass
            else:
                replace_audio(mp)
        else:
            logger.info('Audio Level is OK ({}), keeping audio track'.format(pipeline_amp))
            track_id = find_track_by_filename(mp)
            mp.remove(track_id)
            repo.update(mp)
    remove_temp(temp_amp)


def replace_audio(mp):
    mpUri = mp.getURI()
    logger.info('Audio quiet - will be replaced')
    aud_tracks = get_audio_pathname()
    for i in aud_tracks:
        if i.file == "failover.mp3":
            FAILOVER_FILE = os.path.join(mpUri, os.path.basename(i.file))
    bins = recorder.recorder.bins
    for name, bin in bins.iteritems():
        if name == 'AudioSource':
            filename = "presenter.mp3"
    if filename:
        logger.debug("Audio track found, so replacing it...")
        dest = os.path.join(mpUri, os.path.basename(filename))
    else:
        logger.debug("No audio track found, so create a new one")
        dest = os.path.join(mpUri, os.path.basename(FAILOVER_FILE))
    logger.debug("Copying from {} to {}".format(FAILOVER_FILE, dest))
    try:
        shutil.copyfile(FAILOVER_FILE, dest)
        # os.remove(FAILOVER_FILE)
        track_id = find_track_by_filename(mp)
        mp.remove(track_id)
        repo.update(mp)
        logger.info('Replaced quite audio with failover recording, URI: %s', mpUri)
    except Exception as exc:
        logger.error("Error trying to save failover audio: {}".format(exc))


def do_async_check(mp, mpUri):
    # look for failover audio file
    temp_failaudio_loc = os.path.join(mpUri, os.path.basename(FAILOVER_FILE))
    if os.path.exists(temp_failaudio_loc):
        replace_audio(mp)


def check_pipeline_amp(self, valor, valor2, stereo):
    global temp_amp, logger

    # gstreamer pipeline amplitude temp file
    temp_amp = os.path.join(repo.get_rectemp_path(), 'plugin_failovermic.tmp')

    if context.get_recorder().is_recording():
        rms = valor
        rms_list.append(rms)
        if os.path.exists(temp_amp):
            f = open(temp_amp, 'a')
        else:
            f = open(temp_amp, 'w')
        if len(rms_list) > 100:
            value = str(max(rms_list))
            logger.debug("Writing data {} to {}".format(value, temp_amp))
            f.write(value + '\n')
            f.close()
            del rms_list[:]

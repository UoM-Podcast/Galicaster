import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)

import os
import shutil
from galicaster.core import context
from galicaster.mediapackage import mediapackage
from galicaster.plugins import handleerror

repo = context.get_repository()

ampsd = True


def init():
    try:
        global dispatcher, logger, repo, conf, recorder

        dispatcher = context.get_dispatcher()
        logger = context.get_logger()
        conf = context.get_conf()
        recorder = context.get_recorder()

        dispatcher.connect('timer-short', check_pipeline_amp)

    except ValueError:
        pass

def check_pipeline_amp(self):
    global temp_amp, logger
    global ampsd
    # if context.get_recorder().is_recording():
    #     return
    # else:
    amps = context.get_recorder().get_audio_level()
    # -699.99 dB seems to be absolute zero for levels
    if amps[0] <= -699 and amps[1] <= -699:

        if ampsd == False:
            handleerror.HandleError().do_error('mic has no audio. Level = {}, restarting galicaster'.format(amps), kill=False, reboot=True)
        else:
            logger.debug('muted audio detected: {}'.format(amps))
        ampsd = False
    else:
        logger.debug('audio levels OK: {}'.format(amps))
        ampsd = True

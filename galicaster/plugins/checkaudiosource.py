import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)

import os
import shutil
from galicaster.core import context
from galicaster.mediapackage import mediapackage
from galicaster.plugins import handleerror
from galicaster.plugins import gcnagios

repo = context.get_repository()

ampsd = True
amp_warn = True


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
    global amp_warn
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

    elif -65 >= amps[0] >= -100 and -65 >= amps[1] >= -100:

        if amp_warn == False:
            handleerror.HandleError().do_audio_warning('mic low audio levels. Level = {}'.format(amps), kill=False, reboot=False)
        else:
            logger.debug('low audio detected: {}'.format(amps))
            amp_warn = False
    else:
        logger.debug('audio levels OK: {}'.format(amps))
        if ampsd == False or amp_warn == False:
            gcnagios.GCNagios().nagios_default_state()
        amp_warn = True
        ampsd = True


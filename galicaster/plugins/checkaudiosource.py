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
from galicaster.plugins import gcmail

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

        global low_alert
        global check_recording
        low_alert = conf.get_int('checkaudiosource', 'low_alert', -50)
        check_recording = conf.get_boolean('checkaudiosource', 'check_recording', False)

        dispatcher.connect('timer-short', check_pipeline_amp)

    except ValueError:
        pass


def send_email():
    # send email to email address(s) listed in the mediapackage
    ca_name = conf.get('ingest', 'hostname')
    subject = "Audio Event Logging: {}".format(ca_name)
    email = 'podcast-tech@manchester.ac.uk'
    message = """
This is an automated email to log a galicaster event

No Audio detected in {}. CA restarting
""".format(ca_name)
    gcmail.GCEmail().send_mail(email, subject, message)


def check_pipeline_amp(self):
    global logger
    global ampsd
    global amp_warn
    # if context.get_recorder().is_recording():
    #     return
    # else:
    amps = context.get_recorder().get_audio_level()
    # -699.99 dB seems to be absolute zero for levels
    print amps
    if amps[0] <= -699 and amps[1] <= -699:

        if ampsd == False:
            handleerror.HandleError().do_error('mic has no audio. Level = {}, restarting galicaster'.format(amps), kill=False, reboot=True)
        else:
            logger.debug('muted audio detected: {}'.format(amps))
            send_email()
        ampsd = False
    # check for abnormally low audio levels when recording and create a nagios warning if so.
    elif amps[0] <= low_alert and amps[1] <= low_alert:
        if check_recording:
            if recorder.is_recording():
                if amp_warn == False:
                    handleerror.HandleError().do_audio_warning('Low audio during Recording. Level = {}'.format(amps),
                                                               kill=False, reboot=False)
                else:
                    logger.debug('Low audio during Recording: {}'.format(amps))
                    amp_warn = False
            else:
                logger.debug('Low audio but tolerated: {}'.format(amps))
                if ampsd == False or amp_warn == False:
                    gcnagios.GCNagios().nagios_default_state()
                amp_warn = True
                ampsd = True
        else:
            if amp_warn == False:
                handleerror.HandleError().do_audio_warning('Low audio levels. Level = {}'.format(amps), kill=False, reboot=False)
            else:
                logger.debug('low audio detected: {}'.format(amps))
                amp_warn = False
    else:
        logger.debug('audio levels OK: {}'.format(amps))
        if ampsd == False or amp_warn == False:
            gcnagios.GCNagios().nagios_default_state()
        amp_warn = True
        ampsd = True


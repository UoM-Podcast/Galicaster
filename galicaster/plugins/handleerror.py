__author__ = 'andrew wilson'
"""
Handle errors coming from galicaster to alert via nagios and perform actions like killing galicaster by script
"""

import os

from galicaster.core import context
from galicaster.plugins import gcnagios

logger = context.get_logger()
worker = context.get_worker()
conf = context.get_conf()


def init():
    try:
        dispatcher = context.get_dispatcher()
        handerr = HandleError()
        dispatcher.connect('recorder-error', handerr.receive_error)

    except ValueError:
        pass


class HandleError(object):

    def __init__(self, errormsg=None):
        try:
            self.match_start = conf.get('handleerror', 'match_start').split(';')
        except:
            self.match_start = None
        try:
            self.match_start_n = conf.get('handleerror', 'match_start_notifyonly').split(';')
        except:
            self.match_start_n = None
        try:
            self.match_end = conf.get('handleerror', 'match_end').split(';')
        except:
            self.match_end = None
        self.killscript = conf.get('handleerror', 'killscript')
        self.errormsg = errormsg

    def do_error(self, err, kill=None, reboot=None):
        logger.info('Notifying nagios of the galicaster error')
        if conf.get_boolean('plugins', 'gcnagios') is True:
            gcnagios.GCNagios().nagios_gst_error(None, err)
        if kill:
            logger.info("killing Galicaster")
            try:
                os.system('{} {} {}'.format(self.killscript, err, 'false'))
            except:
                logger.debug("killing Galicaster by script was not successful. Path: {}".format(self.killscript))
        if reboot:
            logger.info("Rebooting the Capture Agent")
            try:
                os.system('{}'.format('reboot'))
            except:
                logger.debug("Rebooting the capture agent was not successful.")

    def do_audio_warning(self, err, kill=None, reboot=None):
        logger.info('Notifying nagios of the galicaster warning')
        if conf.get_boolean('plugins', 'gcnagios') is True:
            gcnagios.GCNagios().nagios_audio_error(None, err, error_type='warn')

    def execute_error_task(self, matcher, msg, match_type, kill=None):
        if matcher:
            for err in matcher:
                if match_type == 'start':
                    if msg.startswith(err):
                        self.do_error(err, kill)
                else:
                    if match_type == 'end':
                        if msg.endswith(err):
                            self.do_error(err, kill)

    def receive_error(self, signal=None, error_message=None):
        if error_message:
            self.execute_error_task(self.match_start, error_message, 'start', True)
            self.execute_error_task(self.match_end, error_message, 'end', True)
            self.execute_error_task(self.match_start_n, error_message, 'start', False)

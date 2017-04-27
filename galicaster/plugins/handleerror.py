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
            self.match_end = conf.get('handleerror', 'match_end').split(';')
        except:
            self.match_end = None
        self.action = conf.get('handleerror', 'action')
        self.killscript = conf.get('handleerror', 'killscript')
        self.errormsg = errormsg

    def execute_error_task(self, matcher, msg):
        if matcher:
            for err in matcher:
                if msg.startswith(err):
                    logger.info(err)
                    if conf.get_boolean('plugins', 'gcnagios') is True:
                        gcnagios.GCNagios().nagios_gst_error(None, err)
                    if self.action == 'kill':
                        logger.info("killing Galicaster")
                        try:
                            os.system(self.killscript)
                        except:
                            logger.debug("killing Galicaster by script was not successful. Path: {}".format(self.killscript))

    def receive_error(self, signal=None, error_message=None):
        if error_message:
            self.execute_error_task(self.match_start, error_message)
            self.execute_error_task(self.match_end, error_message)

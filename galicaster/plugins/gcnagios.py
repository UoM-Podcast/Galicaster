__author__ = 'andrew wilson'

import os
from string import Template

from galicaster.core import context

logger = context.get_logger()
worker = context.get_worker()

GC_NAGIOS_PLUGINS_DIR = 'nagios/plugins/'
conf_folder = '/etc/galicaster/'

NAGIOS_OK = '0'
NAGIOS_WARNING = '1'
NAGIOS_CRITICAL = '2'
NAGIOS_UNKNOWN = '3'

nagios_status = {
    '0': 'OK',
    '1': 'WARNING',
    '2': 'CRITICAL',
    '3': 'UNKNOWN'
}

plugin_template = Template("""#!/usr/bin/python
import os, sys

print "$nag_error"
sys.exit($exit_code)
""")


def init():
    try:
        dispatcher = context.get_dispatcher()
        make_plugin_path()
        gcn = GCNagios()
        dispatcher.connect('init', gcn.nagios_default_state)

    except ValueError:
        pass


def make_plugin_path():
    # check to see if temp dir exists if not make one
    if not os.path.exists(conf_folder + GC_NAGIOS_PLUGINS_DIR):
        os.makedirs(conf_folder + GC_NAGIOS_PLUGINS_DIR)


class GCNagios(object):

    def __init__(self, nag_error=None,  exit_code=NAGIOS_OK):
        self.nag_error = nag_error
        self.plugin_path = conf_folder + GC_NAGIOS_PLUGINS_DIR
        self.plugin_template = plugin_template
        self.exit_code = exit_code

    def nagios_default_state(self, sender=None):
        if context.get_recorder().is_error():
            pass
        else:
            self.nag_error = nagios_status[NAGIOS_OK] + ' - gstreamer working'
            self.make_plugin('nagios_gst_error')
            self.make_plugin('nagios_audio_error')

    def nagios_gst_error(self, signal=None, error_message=None, error_type=None):
        # FIXME: get a list of error messages to iterate over or just any error
        if error_message: # and error_message.startswith('GStreamer encountered a general resource error'):
            if error_type == 'warn':
                logger.debug('GStreamer warning: ' + error_message)
                # FIXME: use config defined message
                self.nag_error = nagios_status[NAGIOS_WARNING] + ' - ' + error_message.replace('\n', '')
                self.exit_code = NAGIOS_WARNING
                self.make_plugin('nagios_gst_error')
            else:
                logger.debug('GStreamer error: ' + error_message)
                # FIXME: use config defined message
                self.nag_error = nagios_status[NAGIOS_CRITICAL] + ' - ' + error_message.replace('\n', '')
                self.exit_code = NAGIOS_CRITICAL
                self.make_plugin('nagios_gst_error')
        else:
            self.nag_error = 'OK - GStreamer working'
            self.make_plugin('nagios_gst_error')

    def nagios_audio_error(self, signal=None, error_message=None, error_type=None):
        # FIXME: get a list of error messages to iterate over or just any error
        if error_message:
            if error_type == 'warn':
                logger.debug('galicaster audio warning: ' + error_message)
                # FIXME: use config defined message
                self.nag_error = nagios_status[NAGIOS_WARNING] + ' - ' + error_message.replace('\n', '')
                self.exit_code = NAGIOS_WARNING
                self.make_plugin('nagios_audio_error')
            else:
                logger.debug('galicaster audio error: ' + error_message)
                # FIXME: use config defined message
                self.nag_error = nagios_status[NAGIOS_CRITICAL] + ' - ' + error_message.replace('\n', '')
                self.exit_code = NAGIOS_CRITICAL
                self.make_plugin('nagios_audio_error')
        else:
            self.nag_error = 'OK - galicaster audio'
            self.make_plugin('nagios_audio_error')

    def make_template(self):
        message = plugin_template.substitute(nag_error=self.nag_error, exit_code=self.exit_code)
        return message

    def make_plugin(self, plug_name):
        plugin_path_full = self.plugin_path + plug_name
        pluginfile = open(plugin_path_full, 'w')
        pluginfile.write(self.make_template())
        pluginfile.close()
        os.chmod(plugin_path_full, 0755)


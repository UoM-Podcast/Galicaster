__author__ = 'andrew wilson'

import datetime
import os
from string import Template

from galicaster.core import context
from galicaster.mediapackage import mediapackage

logger = context.get_logger()
worker = context.get_worker()
conf = context.get_conf()

def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('recorder-error', GCNagios.nagios_gst_error)

    except ValueError:
        pass

plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'contrib/nagios/plugins/'))
plugin_template = Template("""#!/usr/bin/python
import os, sys

print "$gst_error"
sys.exit($exit_code)
""")


class GCNagios(object):

    def __init__(self, gst_error=None, plugin_file=plugin_path, plugin_template=plugin_template, exit_code='0'):
        self.gst_error = gst_error
        self.plugin_path = plugin_path
        self.plugin_template = plugin_template
        self.exit_code = exit_code

    def nagios_gst_error(self, error_message):
        if error_message.startswith("GStreamer encountered a general resource error"):
            logger.info("GStreamer error: " + error_message)
            self.in_error = True
            self.gst_error = 'CRITICAL - ' + error_message + ' Reboot Required'
            self.exit_code = '2'
            self.make_plugin()
        else:
            self.gst_error = 'OK - gstreamer working'
            self.make_plugin()

    def make_template(self):
        message = plugin_template.substitute(gst_error=self.gst_error, exit_code=self.exit_code)
        return message

    def make_plugin(self):
        pluginfile = open(self.plugin_path + '/' + self.nagios_gst_error.__name__, 'w')
        pluginfile.write(self.make_template())
        pluginfile.close()


#print nagios_gsterror('GStreamer encountered a general resource error ham and cake')
GCNagios().nagios_gst_error('GStreamer encountered a general resource error ham')

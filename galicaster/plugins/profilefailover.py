__author__ = 'andrew wilson'

import datetime
import os
import usb1

from galicaster.core import context
from galicaster.mediapackage import mediapackage

logger = context.get_logger()
worker = context.get_worker()
conf = context.get_conf()

dev_id = '17a00101'
profile = 'test-loopback'
normal_profile = 'test-loopback-usb'

def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('galicaster-notify-timer-short', profile_failover)

    except ValueError:
        pass

def get_device():
    context = usb1.USBContext()
    for dev in context.getDeviceList(skip_on_error=True):
        if format(dev.getVendorID(), '04x') + format(dev.getProductID(), '04x') == dev_id:
            return True
    return False

def add_failover_pipeline():
    #! textoverlay text='Microphone Disconnected' font-desc="Arial 10" outline-color=0  halign=right valign=top ! decodebin !

def profile_failover(sender=None):
    #if (error_message.startswith("Internal GStreamer error: negotiation problem") or
       #(error_message.startswith("GStreamer encountered a general resource error. (pulsesrc.c") and
       #os.path.isfile("/var/www/no_mic") is False)):
    if context.get_state().is_recording is False:
        is_device = get_device()
        current_profile = conf.get_current_profile().name
        if current_profile != profile and (is_device is False):
            conf.change_current_profile(profile)
            conf.update()
            context.get_dispatcher().emit("reload-profile")
        if current_profile != normal_profile and (is_device is True):
            conf.change_current_profile(normal_profile)
            conf.update()
            context.get_dispatcher().emit("reload-profile")
             #logger.info("GStreamer error: " + error_message)
             #logger.info("killing Galicaster")
             #os.system("/usr/share/galicaster/contrib/scripts/kill_gc")

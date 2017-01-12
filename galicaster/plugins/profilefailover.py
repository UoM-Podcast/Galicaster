__author__ = 'andrew wilson'

import usb1

from galicaster.core import context


def init():
    try:
        conf = context.get_conf()
        dev_id = conf.get('profilefailover', 'usb-device') or '17a00101'
        profile = conf.get('profilefailover', 'failover-profile') or conf.get_current_profile().name
        normal_profile = conf.get('profilefailover', 'normal-profile') or conf.get('basic', 'profile') or 'Default'
        pf = DeviceRemovalProfileFailover(dev_id, profile, normal_profile, conf, context.get_logger())

        dispatcher = context.get_dispatcher()
        dispatcher.connect('galicaster-notify-timer-short', pf.profile_failover)

    except ValueError:
        pass


class DeviceRemovalProfileFailover():

    def __init__(self, dev_id, profile, normal_profile, conf, logger=None):
        self.dev_id = dev_id
        self.profile = profile
        self.normal_profile = normal_profile
        self.conf = conf
        self.logger = logger

    def get_device(self):
        udevcontext = usb1.USBContext()
        for dev in udevcontext.getDeviceList(skip_on_error=True):
            if format(dev.getVendorID(), '04x') + format(dev.getProductID(), '04x') == self.dev_id:
                return True
        return False

    def profile_failover(self, sender=None):
        if context.get_recorder().is_recording is False:
            is_device = self.get_device()
            current_profile = self.conf.get_current_profile().name
            if current_profile != self.profile and (is_device is False):
                self.logger.warning('USB device used with Galicaster has been disconnected, '
                                    'switching to profile {}'.format(self.profile))
                self.conf.change_current_profile(self.profile)
                self.conf.update()
                context.get_dispatcher().emit("reload-profile")
            if current_profile != self.normal_profile and (is_device is True):
                self.logger.info('USB device used with Galicaster has been CONNECTED, '
                                 'switching to profile {}'.format(self.normal_profile))
                self.conf.change_current_profile(self.normal_profile)
                self.conf.update()
                context.get_dispatcher().emit("reload-profile")

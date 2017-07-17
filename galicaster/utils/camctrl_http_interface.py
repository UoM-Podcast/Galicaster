import requests
from requests.auth import HTTPDigestAuth
import logging

logging.getLogger("requests").setLevel(logging.WARNING)

class AxisWeb(object):
    def __init__(self, cam_hostname, cam_username, cam_password):
        self.cam_hostname = cam_hostname
        self.cam_username = cam_username
        self.cam_password = cam_password
        self.led_state = "off"
        # On init, make sure LED is off
        self.tallyled(False)

    def sendcommand(self, fullurl, data):
        headers = {'X-Requested-Auth': 'Digest'}
        try:

            r = requests.post(fullurl, headers=headers, auth=HTTPDigestAuth(self.cam_username, self.cam_password),
                              data=data)
        except Exception as e:
            print 'ERROR when accessing axis http interface: ' + e
        return r

    def tallyled(self, switch=False):
        if switch:
            self.led_state = "on"
        else:
            self.led_state = "off"
        url = 'http://' + self.cam_hostname + '/sm/sm.srv'
        postfield = {"root_TallyLED_Usage": self.led_state, "return_page": "/admin/config.shtml?menu=&submenu=&group=TallyLED", "action": "modify"}
        snd_cmd = self.sendcommand(url, postfield)
        return snd_cmd.status_code

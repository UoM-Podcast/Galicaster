import requests
from requests.auth import HTTPDigestAuth
import logging
import datetime

logging.getLogger("requests").setLevel(logging.WARNING)

class AxisWeb(object):
    def __init__(self, cam_hostname, cam_username, cam_password):
        self.cam_hostname = cam_hostname
        self.cam_username = cam_username
        self.cam_password = cam_password
        self.led_state = "off"
        # On init, make sure LED is off
        self.tallyled(False)
        # Make sure the time is set
        self.vapix_settime()

    def sendcommand(self, fullurl, data):
        headers = {'X-Requested-Auth': 'Digest'}
        try:

            r = requests.post(fullurl, headers=headers, auth=HTTPDigestAuth(self.cam_username, self.cam_password),
                              data=data)
        except Exception as e:
            print 'ERROR when accessing axis http interface: ' + e
        return r

    def send_vapix_command(self, fullurl):
        headers = {'X-Requested-Auth': 'Digest'}
        try:

            r = requests.get(fullurl, headers=headers, auth=HTTPDigestAuth(self.cam_username, self.cam_password))
        except Exception as e:
            print 'ERROR when accessing axis http interface: ' + e
        return r

    def tallyled(self, switch=False):
        # this uses the 'plain text config, section of the axis web config, technically this isnt supported api
        if switch:
            self.led_state = "on"
        else:
            self.led_state = "off"
        url = 'http://' + self.cam_hostname + '/sm/sm.srv'
        postfield = {"root_TallyLED_Usage": self.led_state, "return_page": "/admin/config.shtml?menu=&submenu=&group=TallyLED", "action": "modify"}
        snd_cmd = self.sendcommand(url, postfield)
        return snd_cmd.status_code

    def settime(self, version="PC"):
        # this uses the 'plain text config, section of the axis web config, technically this isnt supported api
        url = 'http://' + self.cam_hostname + '/sm/sm.srv'
        postfield = {"root_Time_SyncSource": version,
                     "return_page": "/admin/config.shtml?menu=&submenu=&group=Time", "action": "modify"}
        snd_cmd = self.sendcommand(url, postfield)
        return snd_cmd.status_code

    def vapix_gettime(self):
        url = 'http://' + self.cam_hostname + '/axis-cgi/date.cgi?action=get'
        snd_vpx_cmd = self.send_vapix_command(url)
        return snd_vpx_cmd.status_code

    def vapix_settime(self):
        now = datetime.datetime.now()
        yr = now.year
        mth = now.month
        dy = now.day
        hr = now.hour
        mn = now.minute
        sc = now.second
        time_action = '/axis-cgi/date.cgi?action=set&' \
                      'year={}&month={}&day={}&hour={}&minute={}&second={}'.format(yr, mth, dy, hr, mn, sc)
        url = 'http://' + self.cam_hostname + time_action
        snd_vpx_cmd = self.send_vapix_command(url)
        return snd_vpx_cmd.status_code

"""
check that aver camera is in tracking mode and set it if not
"""

import requests
from requests.auth import HTTPBasicAuth

from galicaster.core import context

conf = context.get_conf()
dispatcher = context.get_dispatcher()
logger = context.get_logger()

DEFAULT_CAM_IP = '192.168.0.90'
DEFAULT_CAM_USER = 'root'
DEFAULT_CAM_PASS = ''

API_TRACKING_PARAM = 'trk_tracking_on,3'
API_TRACKING_GET = '/cgi-bin?Get={}&_=1'.format(API_TRACKING_PARAM)
API_TRACKING_ON = '/cgi-bin?Set={},3,1&_=1'.format(API_TRACKING_PARAM)

cam_ip = ''
cam_user = ''
cam_pass = ''

def init():
    global cam_ip, cam_user, cam_pass
    cam_ip = conf.get('camctrl', 'ip') or DEFAULT_CAM_IP
    logger.debug('cam ip set to {}'.format(cam_ip))
    cam_user = conf.get('camctrl', 'web_username') or DEFAULT_CAM_USER
    logger.debug('cam ip set to {}'.format(cam_user))
    cam_pass = conf.get('camctrl', 'web_password') or DEFAULT_CAM_PASS
    logger.debug('cam password set')

    dispatcher.connect('timer-short', do_timers_short)

def do_timers_short(sender):
    auth = HTTPBasicAuth(cam_user, cam_pass)
    try:
        r = requests.get('http://' + cam_ip + API_TRACKING_GET, auth=auth)
        status = r.text.split('=')
        if status[0] == API_TRACKING_PARAM and status[1].rstrip() == '1':
            return
    except:
        logger.warn('could not get tracking status from {}'.format(cam_ip))

    logger.debug('sending request to turn tracking on')
    try:
        r = requests.get('http://' + cam_ip + API_TRACKING_ON, auth=auth)
    except:
        logger.warn('turn on tracking request failed for {}'.format(cam_ip))

# -*- coding:utf-8 -*-
# Copyright (c) 2016 University of Manchester
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import threading
from bottle import route, run, response, abort, request, install
from gi.repository import GObject

from galicaster.core import context
import galicaster.utils.pyvapix as vapix

last_cam_ip = None

def error_handler(func):
    def wrapper(*args,**kwargs):
        try:
            return func(*args,**kwargs)
        except Exception as e:
            logger = context.get_logger()
            error_txt = str(e)
            logger.error("Error in function '{}': {}".format(func.func_name, error_txt))

            abort(503, error_txt)
    return wrapper


def init():
    conf = context.get_conf()
    host = conf.get('peakaboovapixbridge', 'host')
    port = conf.get_int('peakaboovapixbridge', 'port')

    install(error_handler)

    restp = threading.Thread(target=run,kwargs={'host': host, 'port': port, 'quiet': True})
    restp.setDaemon(True)
    restp.start()


@route('/')
def index():
    response.content_type = 'application/json'
    text = {"description" : "Peakaboo VAPIX bridge with REST endpoints galicaster plugin\n\n"}
    endpoints = {
            "/move/:action": "move camera",
        }
    endpoints.update(text)
    return json.dumps(endpoints)


@route('/move/:action')
def move(action):
    response.content_type = 'application/json'
    ptz_prefix = 'peakaboo-ptz-'
    ptz_suffix = '_Camera_1'
    cam_ip = '192.168.0.90'
    ptz_sp_plus = '50'
    ptz_sp_minus = '-50'
    conf = context.get_conf()
    cam_auth_user = conf.get('ddp', 'cam_auth_user')
    cam_auth_pass = conf.get('ddp', 'cam_auth_pass')

    recorder = context.get_recorder()
    try:
        bins = recorder.recorder.bins
    except AttributeError as e:
        print e

    # determine which camera the command is for
    for name, bin in bins.iteritems():
        if bin.options['type'] == 'video/camera':
            if action != 'false':
                if action.split('_')[2] == name.split('_')[1]:
                    # print name
                    cam_ip = str(bin.options['location'].split('@')[1].split(':')[0]).strip()
                    # print cam_ip
                    global last_cam_ip
                    last_cam_ip = cam_ip
                    ptz_suffix = '_' + name

    send_ptz_setmove = vapix.Vapix(ip=cam_ip, username=cam_auth_user, password=cam_auth_pass)
    if action == ptz_prefix + 'left-up-button' + ptz_suffix:
        # print 'move left up!'
        send_ptz_setmove.move('upleft')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'up-button' + ptz_suffix:
        # print 'move up!'
        send_ptz_setmove.move('up')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'right-up-button' + ptz_suffix:
        # print 'move right up!'
        send_ptz_setmove.move('upright')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'left-button' + ptz_suffix:
        # print 'move left!'
        send_ptz_setmove.move('left')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'right-button' + ptz_suffix:
        # print 'move right!'
        send_ptz_setmove.move('right')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'left-down-button' + ptz_suffix:
        # print 'move left down!'
        send_ptz_setmove.move('downleft')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'down-button' + ptz_suffix:
        # print 'move down!'
        send_ptz_setmove.move('down')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'right-down-button' + ptz_suffix:
        # print 'move right down!'
        send_ptz_setmove.move('downright')
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'zoom-in-button' + ptz_suffix:
        # print 'zoom in'
        send_ptz_setmove.continuouszoommove(ptz_sp_plus)
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'zoom-out-button' + ptz_suffix:
        # print 'zoom out'
        send_ptz_setmove.continuouszoommove(ptz_sp_minus)
        ptzmovement = True
        ptzhome = False
    if action == ptz_prefix + 'home-button' + ptz_suffix:
        # print 'move home position!'
        send_ptz_setmove.move('home')
        ptzmovement = True
        ptzhome = True
    if action == 'false':
        # print 'stop moving!'
        print last_cam_ip
        vapix.Vapix(ip=last_cam_ip, username=cam_auth_user, password=cam_auth_pass).move('stop')
        vapix.Vapix(ip=last_cam_ip, username=cam_auth_user, password=cam_auth_pass).continuouszoommove('0')
        ptzmovement = False
    
    return json.dumps({"move": "done"})

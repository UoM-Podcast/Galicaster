# DDP galicaster plugin
#
# Copyright (c) 2016 University of Sussex
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

# import calendar
import cStringIO
import requests
from requests.auth import HTTPDigestAuth
import socket
from threading import Event, Thread
import time
import uuid
import gi
import subprocess
import re
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf
from random import randint
from random import uniform
from random import choice

from MeteorClient import MeteorClient
import pyscreenshot as ImageGrab
from PIL import Image
from io import BytesIO
from galicaster.core import context
import galicaster.utils.camctrl_onvif_interface as camera
import galicaster.utils.pyvapix as vapix

conf = context.get_conf()
dispatcher = context.get_dispatcher()
logger = context.get_logger()


def init():
    ddp = DDP()
    ddp.start()


class DDP(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.meteor = conf.get('ddp', 'meteor')

        self.client = MeteorClient(self.meteor, debug=False)
        self.client.on('added', self.on_added)
        self.client.on('changed', self.on_changed)
        self.client.on('subscribed', self.on_subscribed)
        self.client.on('connected', self.on_connected)
        self.client.on('removed', self.on_removed)
        self.client.on('closed', self.on_closed)
        self.client.on('logged_in', self.on_logged_in)

        self.displayName = conf.get('ddp', 'room_name')
        self.vu_min = -50
        self.vu_range = 50
        self.vu_data = 0
        self.last_vu = None
        self.ip = conf.get('ingest', 'address')
        self.id = conf.get('ingest', 'hostname')
        self._user = conf.get('ddp', 'user')
        self._password = conf.get('ddp', 'password')
        self._http_host = conf.get('ddp', 'http_host')
        self.high_quality = conf.get_boolean('ddp', 'hq_snapshot')
        self.support_group = conf.get('ddp', 'support_group')
        self.paused = False
        self.recording = False
        self.currentMediaPackage = None
        self.currentProfile = None
        self.has_disconnected = False
        self.screen = Gdk.Screen.get_default()
        self._screen_width = self.screen.get_width()
        self._screen_height = self.screen.get_height()
        self.cam_ip = conf.get('ddp', 'cam_ip')
        self.cam_rtmp_hostname = conf.get('ddp', 'rtmp_host')
        self.cam_snapshot = 'http://{}/jpg/image.jpg?resolution=1280x720'
        self.cam_auth_user = conf.get('ddp', 'cam_auth_user')
        self.cam_auth_pass = conf.get('ddp', 'cam_auth_pass')
        self.cam_available = conf.get('ddp', 'cam_available')
        self.token = None
        self.extra_params_list = None
        self.connected = False
        self.inputs_sources = None
        self.ptzmovement = False
        self.ptzhome = False
        self.bins = {}
        self.stream = False
        self.last_cam_ip = None
        self.ptz_sp_plus = '50'
        self.ptz_sp_minus = '-50'

        dispatcher.connect('init', self.on_init)
        dispatcher.connect('recorder-vumeter', self.vumeter)
        dispatcher.connect('timer-long', self.update_vu)
        dispatcher.connect('timer-short', self.heartbeat)
        dispatcher.connect('recorder-ready', self.add_inputs)
        dispatcher.connect('recorder-started', self.on_start_recording)
        dispatcher.connect('recorder-stopped', self.on_stop_recording)
        dispatcher.connect('recorder-status', self.on_rec_status_update)

    def get_ip_address(self):
        return socket.gethostbyname(socket.gethostname())

    def run(self):
        self.connect()

    def connect(self):
        logger.debug(self.connected)
        if not self.connected:
            logger.info('Trying to connect to meteor')
            try:
                self.client.connect()
                self.connected = True
            except Exception as e:
                logger.debug(e)
                logger.warn('DDP connection failed')

    def update(self, collection, query, update):
        if self.client.connected and self.subscribedTo('GalicasterControl'):
            try:
                self.client.update(
                    collection,
                    query,
                    update,
                    callback=self.update_callback)
            except Exception:
                logger.warn(
                    "Error updating document "
                    "{collection: %s, query: %s, update: %s}" %
                    (collection, query, update))

    def insert(self, collection, document):
        if self.client.connected and self.subscribedTo('GalicasterControl'):
            try:
                self.client.insert(
                    collection,
                    document,
                    callback=self.insert_callback)
            except Exception:
                logger.warn(
                    "Error inserting document {collection: %s, document: %s}" %
                    (collection, document))

    def heartbeat(self, element):
        if self.client.connected:
            self.update_images(randint(0, 9))
            self.update_rec_status()
        else:
            self.connect()

    def update_rec_status(self):
        self.update(
            'rooms', {
                '_id': self.id
            }, {
                '$set': {
                    'recording': self.recording
                }
            })

    def on_start_recording(self, sender, id):
        self.recording = True
        self.currentMediaPackage = self.media_package_metadata(id)
        self.currentProfile = conf.get_current_profile().name
        self.update(
            'rooms', {
                '_id': self.id
            }, {
                '$set': {
                    'currentMediaPackage': self.currentMediaPackage,
                    'currentProfile': self.currentProfile,
                    'recording': self.recording
                }
            })

    def on_stop_recording(self, mpid, sender=None):
        self.recording = False
        self.currentMediaPackage = None
        self.currentProfile = None
        self.update(
            'rooms', {
                '_id': self.id
            }, {
                '$unset': {
                    'currentMediaPackage': '',
                    'currentProfile': ''
                }, '$set': {
                    'recording': self.recording
                }
            })
        # self.update_images(1.5)

    def on_init(self, data):
        self.update_images(randint(0, 9))
        self.start_livestream(randint(3, 12))

    def start_livestream(self, delay=0):
        worker = Thread(target=self._start_livestream, args=(delay,))
        worker.start()

    def _start_livestream(self, delay):
        time.sleep(delay)
        if self.stream == False:
            for name, bin in self.bins.iteritems():
                if bin.options['type'] == 'video/camera':
                    location = bin.options['location']
                    # check if stream is already running
                    try:
                        response = requests.get("http://{}/dash/{}/index.mpd".format(self.cam_rtmp_hostname, self.displayName + '_' + name))
                    except Exception as e:
                        return
                    if response.status_code == requests.codes.ok:
                        return
                    stream_cmd = "ffmpeg -re -f lavfi -i anullsrc -thread_queue_size 512 -rtsp_transport tcp -i " \
                                 "{} -tune " \
                                 "zerolatency -c:v libx264 -pix_fmt yuv420p -profile:v baseline -preset ultrafast -tune zerolatency " \
                                 "-vsync cfr -x264-params 'nal-hrd=cbr' -b:v 1500k -minrate 1500k -maxrate 1500k -bufsize 3000k -g 60 -s " \
                                 "1280x720 -c:a aac -map 1:v:0 -map 1:a:0 -f " \
                                 "flv rtmp://{}/dash/{}".format(location, self.cam_rtmp_hostname, self.displayName + '_' + name)
                    subprocess.Popen(stream_cmd, shell=True)
                self.stream = True

    def update_images(self, delay=0.0):
        worker = Thread(target=self._update_images, args=(delay,))
        worker.start()

    def process_images(self, image_data):
        image_format = 'JPEG'
        if not self.high_quality:
            image_data.thumbnail((640, 360), Image.ANTIALIAS)
        else:
            image_format = 'PNG'
        if image_data.mode != "RGB":
            im2 = image_data.convert("RGB")
        output1 = cStringIO.StringIO()
        image_data.save(output1, format=image_format) # to reduce jpeg size use param: optimize=True
        return output1

    def _update_images(self, delay):
        time.sleep(delay)
        files = {}
        # take a screenshot with pyscreenshot
        im1 = ImageGrab.grab(bbox=(0, 0, self._screen_width, self._screen_height), backend='imagemagick')

        # get the camera snapshots and send them
        for name, bin in self.bins.iteritems():
            if bin.options['type'] == 'video/camera':
                location = bin.options['location']
                snapshot_ip = re.search(r'\@(.*)\:', location).group(1)
                try:
                    response = requests.get(self.cam_snapshot.format(snapshot_ip), auth=HTTPDigestAuth(self.cam_auth_user, self.cam_auth_pass))
                    cam_snap_img = Image.open(BytesIO(response.content))
                    files[name] = ('{}.jpg'.format(name), self.process_images(cam_snap_img).getvalue(), 'image/jpeg')


                except IOError as e:
                    logger.warn(e)
                    return

        files['galicaster'] = ('galicaster.jpg', self.process_images(im1).getvalue(), 'image/jpeg')

        try:
            # add verify=False for testing self signed certs
            r = requests.post(
                "%s/image/%s" %
                (self._http_host, self.id), files=files, auth=(
                    self._user, self._password)) # to ignore ssl verification, use param: verify=False
        except Exception:
            logger.warn('Unable to post images')

    def vumeter(self, element, data, data_chan2, vu_bool):
        if data == "Inf":
            data = 0
        else:
            if data < -self.vu_range:
                data = -self.vu_range
            elif data > 0:
                data = 0
        self.vu_data = int(((data + self.vu_range) / float(self.vu_range)) * 100)

    def update_vu(self, element):
        if self.vu_data != self.last_vu:
                update = {'vumeter': self.vu_data}
                self.update('rooms', {'_id': self.id}, {'$set': update})
                self.last_vu = self.vu_data

    def on_rec_status_update(self, element, data):
        if data == 'paused':
            is_paused = True
        else:
            is_paused = False
        if is_paused:
            # self.update_images(.75)
            pass
        if self.paused == is_paused:
            self.update(
                'rooms', {
                    '_id': self.id}, {
                    '$set': {
                        'paused': is_paused}})
            self.paused = is_paused
        if data == 'recording':
            # self.update_images(.75)
            pass

    def media_package_metadata(self, id):
        mp = context.get('recorder').current_mediapackage
        line = mp.metadata_episode
        duration = mp.getDuration()
        line["duration"] = long(duration / 1000) if duration else None
        # FIXME Does series_title need sanitising as well as duration?
        created = mp.getDate()
        # line["created"] = calendar.timegm(created.utctimetuple())
        for key, value in mp.metadata_series.iteritems():
            line["series_" + key] = value
        for key, value in line.iteritems():
            if value in [None, []]:
                line[key] = ''
        # return line
        return line

    def subscription_callback(self, error):
        if error:
            logger.warn("Subscription callback returned error: %s" % error)

    def insert_callback(self, error, data):
        if error:
            logger.warn("Insert callback returned error: %s" % error)

    def update_callback(self, error, data):
        if error:
            logger.warn("Update callback returned error: %s" % error)

    def on_subscribed(self, subscription):
        if(subscription == 'GalicasterControl'):
            me = self.client.find_one('rooms')
            # Data to push when inserting or updating
            data = {
                'displayName': self.displayName,
                'ip': self.ip,
                'paused': self.paused,
                'recording': self.recording,
                'heartbeat': int(time.time()),
                'camAvailable': self.cam_available,
                'supportGroup': self.support_group
            }
            # Parse extra Meteor Mongodb collection elements and append
            if self.extra_params_list:
                for params in self.extra_params_list:
                    param = params.split(':')
                    data[param[0]] = param[1]

            if self.currentMediaPackage:
                data['currentMediaPackage'] = self.currentMediaPackage
            if self.currentProfile:
                data['currentProfile'] = self.currentProfile

            if me:
                # Items to unset
                unset = {}
                if not self.currentMediaPackage:
                    unset['currentMediaPackage'] = ''
                if not self.currentProfile:
                    unset['currentProfile'] = ''

                # Update to push
                update = {
                    '$set': data
                }

                if unset:
                    update['$unset'] = unset
                self.update('rooms', {'_id': self.id}, update)
            else:
                data['_id'] = self.id
                self.insert('rooms', data)

    def add_inputs(self, signal=None):
        self.update(
            'rooms', {
                '_id': self.id}, {
                '$set': {
                    'inputs': self.inputs()}})

    def inputs(self):
        recorder = context.get_recorder()
        try:
            self.bins = recorder.recorder.bins
        except AttributeError as e:
            print e

        self.inputs_sources = {}
        capture_devices = []
        camera_devices = {}
        for name, bin in self.bins.iteritems():
            # only send video devices
            if not bin.options['type'] == 'audio/microphone':
                if bin.options['type'] == 'video/presentation':
                    capture_devices.append(name)
                if bin.options['type'] == 'video/camera':
                    cam_ip = bin.options['location'].split('@')[1].split(':')[0]
                    camera_devices[name] = cam_ip
        self.inputs_sources['presentations'] = capture_devices
        self.inputs_sources['cameras'] = camera_devices
        return self.inputs_sources

    def on_added(self, collection, id, fields):
        pass

    def on_changed(self, collection, id, fields, cleared):
        me = self.client.find_one('rooms')
        if self.paused != me['paused']:
            self.set_paused(me['paused'])

        if context.get('recorder').is_recording() != me['recording']:
            self.set_recording(me)
        # ptz camera commands
        ptz_prefix = 'peakaboo-ptz-'
        ptz_suffix = '_Camera_1'
        cam_ip = self.last_cam_ip
        if not self.ptzmovement:
            # determine which camera the command is for
            # FIXME sends 'False when not moving so stop is unknown right now
            if me['ptzmove']:
                for name, bin in self.bins.iteritems():
                    if bin.options['type'] == 'video/camera':
                        if me['ptzmove'].split('_')[2] == name.split('_')[1]:
                            # print name
                            cam_ip = str(bin.options['location'].split('@')[1].split(':')[0]).strip()
                            # print cam_ip
                            self.last_cam_ip = cam_ip
                            ptz_suffix = '_' + name


            if me['ptzmove'] == ptz_prefix + 'left-up-button' + ptz_suffix:
                print 'move left up!'
                self.send_ptz_setmove(cam_ip, 'upleft')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'up-button' + ptz_suffix:
                print 'move up!'
                self.send_ptz_setmove(cam_ip, 'up')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'right-up-button' + ptz_suffix:
                print 'move right up!'
                self.send_ptz_setmove(cam_ip, 'upright')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'left-button' + ptz_suffix:
                print 'move left!'
                self.send_ptz_setmove(cam_ip, 'left')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'right-button' + ptz_suffix:
                print 'move right!'
                self.send_ptz_setmove(cam_ip, 'right')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'left-down-button' + ptz_suffix:
                print 'move left down!'
                self.send_ptz_setmove(cam_ip, 'downleft')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'down-button' + ptz_suffix:
                print 'move down!'
                self.send_ptz_setmove(cam_ip, 'down')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'right-down-button' + ptz_suffix:
                print 'move right down!'
                self.send_ptz_setmove(cam_ip, 'downright')
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'zoom-in-button' + ptz_suffix:
                print 'zoom in'
                self.send_ptzzoom(cam_ip, self.ptz_sp_plus)
                self.ptzmovement = True
                self.ptzhome = False
            if me['ptzmove'] == ptz_prefix + 'zoom-out-button' + ptz_suffix:
                print 'zoom out'
                self.send_ptzzoom(cam_ip, self.ptz_sp_minus)
                self.ptzmovement = True
                self.ptzhome = False
        # if not self.ptzhome:
            if me['ptzmove'] == ptz_prefix + 'home-button' + ptz_suffix:
                print 'move home position!'
                self.send_ptz_setmove(cam_ip, 'home')
                self.ptzmovement = True
                self.ptzhome = True
        if self.ptzmovement:
            if me['ptzmove'] == False:
                print 'stop moving!'
                self.send_ptz_setmove(cam_ip, 'stop')
                self.send_ptzzoom(cam_ip, '0')
                self.ptzmovement = False

    def send_ptz(self, ipaddress, cmd1, cmd2):
        # send ptz commands to the specified camera
        vapix.Vapix(ip=ipaddress, username=self.cam_auth_user, password=self.cam_auth_pass).continuouspantiltmove(cmd1,cmd2)

    def send_ptz_setmove(self, ipaddress, cmd1):
        # send absolute ptz commands to the specified camera
        vapix.Vapix(ip=ipaddress, username=self.cam_auth_user, password=self.cam_auth_pass).move(cmd1)

    def send_ptzzoom(self, ipaddress, cmd1):
        # send ptz zoom commands to the specified camera
        vapix.Vapix(ip=ipaddress, username=self.cam_auth_user, password=self.cam_auth_pass).continuouszoommove(cmd1)

    def on_removed(self, collection, id):
        self.on_subscribed(None)

    def set_paused(self, new_status):
        if not self.paused:
            self.paused = new_status
            logger.debug('paused')
            context.get('recorder').pause()
        else:
            self.paused = False
            logger.debug('resumed')
            context.get('recorder').resume()


    def set_recording(self, me):
        self.recording = me['recording']
        if self.recording:
            # FIXME: Metadata isn't passed to recorder
            meta = me.get('currentMediaPackage', {}) or {}
            profile = me.get('currentProfile', 'nocam')
            series = (meta.get('series_title', ''), meta.get('isPartOf', ''))
            user = {'user_name': meta.get('creator', ''),
                    'user_id': meta.get('rightsHolder', '')}
            title = meta.get('title', 'Unknown')
            self.recording = True
            # make recorder start
            context.get('recorder').record()
        else:
            self.recording = False
            # make recorder stop
            context.get('recorder').stop()

    def on_connected(self):
        logger.info('Connected to Meteor')
        token = conf.get('ddp', 'token')
        self.client.login(self._user, self._password, token=token)

    def on_logged_in(self, data):
        conf.set('ddp', 'token', data['token'])
        conf.update()
        try:
            self.client.subscribe(
                'GalicasterControl',
                params=[
                    self.id],
                callback=self.subscription_callback)
        except Exception as e:
            logger.debug(e)
            logger.warn('DDP subscription failed')

    def on_closed(self, code, reason):
        self.has_disconnected = True
        logger.error('Disconnected from Meteor: err %d - %s' % (code, reason))

    def subscribedTo(self, publication):
        return self.client.subscriptions.get(publication) != None

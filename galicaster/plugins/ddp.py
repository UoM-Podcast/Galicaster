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

import calendar
import alsaaudio
import cStringIO
import os
import requests
import socket
import subprocess
from threading import Event, Thread
import time
import uuid

from gi.repository import Gtk, Gdk, GObject, Pango, GdkPixbuf
from MeteorClient import MeteorClient
import pyscreenshot as ImageGrab
from PIL import Image

from galicaster.core import context


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
        self.do_vu = 0
        self.last_vu = None
        self.ip = conf.get('ingest', 'address')
        self.id = conf.get('ingest', 'hostname')
        self._user = conf.get('ddp', 'user')
        self._password = conf.get('ddp', 'password')
        self._http_host = conf.get('ddp', 'http_host')
        self._audiostream_port = conf.get('audiostream', 'port') or 31337
        if conf.get_boolean('ddp', 'existing_stream'):
            self._stream_host = conf.get_boolean('ddp', 'existing_stream')
        else:
            self._stream_host = self.ip
        self.store_audio = conf.get_boolean('ddp', 'store_audio')
        self.screenshot_file = conf.get('ddp', 'existing_screenshot')
        self.high_quality = conf.get_boolean('ddp', 'hq_snapshot')
        self.paused = False
        self.recording = False
        self.currentMediaPackage = None
        self.currentProfile = None
        self.has_disconnected = False
        screen = Gdk.Screen.get_default()
        self._screen_width = screen.get_width()
        self._screen_height = screen.get_height()
        self.cardindex = None

        cam_available = conf.get(
            'ddp',
            'cam_available') or 0
        if cam_available in ('True', 'true', True, '1', 1):
            self.cam_available = 1
        elif cam_available in ('False', 'false', False, '0', 0):
            self.cam_available = 0
        else:
            self.cam_available = int(cam_available)

        dispatcher.connect('init', self.on_init)
        dispatcher.connect('recorder-vumeter', self.vumeter)
        dispatcher.connect('timer-short', self.heartbeat)
        dispatcher.connect('recorder-started', self.on_start_recording)
        dispatcher.connect('recorder-stopped', self.on_stop_recording)
        dispatcher.connect('recorder-status', self.on_rec_status_update)

    def run(self):
        self.connect()

    def connect(self):
        if not self.has_disconnected:
            try:
                self.client.connect()
            except Exception:
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
            self.update_images()
        else:
            self.connect()

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
        self.update_images(1.5)

    def on_init(self, data):
        self.update_images(1.5)

    def update_images(self, delay=0):
        worker = Thread(target=self._update_images, args=(delay,))
        worker.start()

    def _update_images(self, delay):
        time.sleep(delay)
        files = {}

        if not self.screenshot_file:
            # take a screenshot with pyscreenshot
            im = ImageGrab.grab(bbox=(0, 0, self._screen_width, self._screen_height), backend='imagemagick')
        else:
            try:
                # used if screenshot already exists
                im = Image.open(self.screenshot_file)
            except IOError as e:
                logger.warn("Unable to open screenshot file {0}".format(self.screenshot_file))
                return
        output = cStringIO.StringIO()
        image_format = 'JPEG'
        if not self.high_quality:
            im.thumbnail((640, 360), Image.ANTIALIAS)
        else:
            image_format = 'PNG'

        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(output, format=image_format) # to reduce jpeg size use param: optimize=True
        files['galicaster'] = ('galicaster.jpg', output.getvalue(),
                               'image/jpeg')
        try:
            # add verify=False for testing self signed certs
            requests.post(
                "%s/image/%s" %
                (self._http_host, self.id), files=files, auth=(
                    self._user, self._password)) # to ignore ssl verification, use param: verify=False
        except Exception:
            logger.warn('Unable to post images')

    # def mixer_changed(self, source=None, condition=None, reopen=True):
    #     if self.audiofaders:
    #         if reopen:
    #             for audiofader in self.audiofaders:
    #                 if self.cardindex:
    #                     audiofader['control'] = alsaaudio.Mixer(
    #                         control=audiofader['name'], cardindex=audiofader['cardindex'])
    #                 else:
    #                     audiofader['control'] = alsaaudio.Mixer(
    #                         control=audiofader['name'])
    #         try:
    #             self.update_audio()
    #         except Exception as e:
    #             pass
    #         return True

    def vumeter(self, element, data, data_chan2, vu_bool):
        if self.do_vu == 0:
            if data == "Inf":
                data = 0
            else:
                if data < -self.vu_range:
                    data = -self.vu_range
                elif data > 0:
                    data = 0
            data = int(((data + self.vu_range) / float(self.vu_range)) * 100)
            if data != self.last_vu:
                update = {'vumeter': data}
                self.update('rooms', {'_id': self.id}, {'$set': update})
                self.last_vu = data
        self.do_vu = (self.do_vu + 1) % 20

    def on_rec_status_update(self, element, data):
        if data == 'paused':
            is_paused = True
        else:
            is_paused = False
        if is_paused:
            self.update_images(.75)
        if self.paused == is_paused:
            self.update(
                'rooms', {
                    '_id': self.id}, {
                    '$set': {
                        'paused': is_paused}})
            self.paused = is_paused
        if data == 'recording':
            self.update_images(.75)

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
            stream_key = uuid.uuid4().get_hex()

            # Data to push when inserting or updating
            data = {
                'displayName': self.displayName,
                'ip': self.ip,
                'paused': self.paused,
                'recording': self.recording,
                'heartbeat': int(time.time()),
                'camAvailable': self.cam_available,
                'inputs': self.inputs(),
                'stream': {
                    'host': self._stream_host,
                    'port': self._audiostream_port,
                    'key': stream_key
                }
            }
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
                # audio = self.read_audio_settings()
                data['_id'] = self.id
                # if audio:
                #     data['audio'] = audio
                self.insert('rooms', data)

    def inputs(self):
        inputs = {
            'presentations': ['Presentation']
        }
        inputs['cameras'] = []
        labels = conf.get('ddp', 'cam_labels')
        cam_labels = []
        if labels:
            cam_labels = [l.strip() for l in labels.split(',')]
        for i in range(0, self.cam_available):
            label = cam_labels[i] if i < len(
                cam_labels) else "Camera %d" % (i + 1)
            inputs['cameras'].append(label)
        return inputs

    # def set_audio(self, fields):
    #     if self.audiofaders:
    #         faders = fields.get('audio')
    #         if faders:
    #             for fader in faders:
    #                 mixer = None
    #                 level = fader.get('level')
    #                 for audiofader in self.audiofaders:
    #                     if audiofader['name'] == fader['name']:
    #                         mixer = audiofader['control']
    #                         break
    #                 if mixer:
    #                     l, r = mixer.getvolume(fader['type'])
    #                     if level >= 0 and l != level:
    #                         mixer.setvolume(level, 0, fader['type'])
    #                         mixer.setvolume(level, 1, fader['type'])
    #             if self.store_audio:
    #                 # Relies on no password sudo access for current user to alsactl
    #                 subprocess.call(['sudo', 'alsactl', 'store'])

    def on_added(self, collection, id, fields):
        # try:
        #     self.set_audio(fields)
        #     self.update_audio()
        # except Exception as e:
        #     logger.debug(e)
        #     logger.debug('audiofader issue: cannot adjust audio')
        #     pass
        pass

    def on_changed(self, collection, id, fields, cleared):
        # try:
        #     self.set_audio(fields)
        # except Exception as e:
        #     #print e
        #     pass
        me = self.client.find_one('rooms')
        if self.paused != me['paused']:
            self.set_paused(me['paused'])

        if context.get('recorder').is_recording() != me['recording']:
            self.set_recording(me)

    def on_removed(self, collection, id):
        self.on_subscribed(None)

    def set_paused(self, new_status):
        if not self.paused:
            self.paused = new_status
            context.get('recorder').pause()
        else:
            self.paused = False
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
            context.get('recorder').record()
        else:
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
        except Exception:
            logger.warn('DDP subscription failed')

    def on_closed(self, code, reason):
        self.has_disconnected = True
        logger.error('Disconnected from Meteor: err %d - %s' % (code, reason))

    # def update_audio(self):
    #     if self.audiofaders:
    #         me = self.client.find_one('rooms')
    #         audio = self.read_audio_settings()
    #         update = False
    #         if me:
    #             mAudio = me.get('audio')
    #             mAudioNames = [x['name'] for x in mAudio]
    #             if audio:
    #                 audioNames = [x['name'] for x in audio]
    #                 if set(mAudioNames) != set(audioNames):
    #                     update = True
    #                 if not update:
    #                     for key, fader in enumerate(audio):
    #                         if mAudio[key].get('level') != fader.get('level'):
    #                             update = True
    #                 if update:
    #                     self.update(
    #                         'rooms', {
    #                             '_id': self.id}, {
    #                             '$set': {
    #                                 'audio': audio}})

    # def read_audio_settings(self):
    #     if self.audiofaders:
    #         audio_settings = []
    #         for audiofader in self.audiofaders:
    #             if audiofader['display']:
    #                 try:
    #                     audio_settings.append(
    #                         self.control_values(audiofader)
    #                     )
    #                 except Exception as e:
    #                     logger.debug(e)
    #                     return
    #             # ensure fixed values
    #             mixer = audiofader['control']
    #             if audiofader['setrec']:
    #                 mixer.setrec(1)
    #             if audiofader['mute']:
    #                 mixer.setmute(1)
    #             if audiofader['unmute']:
    #                 mixer.setmute(0)
    #             if audiofader['setlevel'] >= 0:
    #                 mixer.setvolume(audiofader['setlevel'], 0, audiofader['type'])
    #                 if 'Joined Playback Volume' not in mixer.volumecap():
    #                     mixer.setvolume(audiofader['setlevel'], 1, audiofader['type'])
    #         return audio_settings
    #
    # def control_values(self, audiofader):
    #     controls = {}
    #     left, right = audiofader['control'].getvolume(audiofader['type'])
    #     controls['min'] = audiofader['min']
    #     controls['max'] = audiofader['max']
    #     controls['level'] = left
    #     controls['type'] = audiofader['type']
    #     controls['name'] = audiofader['name']
    #     controls['display'] = audiofader['display']
    #     return controls

    def subscribedTo(self, publication):
        return self.client.subscriptions.get(publication) != None
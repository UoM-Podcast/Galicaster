import calendar
#import alsaaudio
import cStringIO
import os
import requests
import socket
import subprocess
from threading import Event, Thread
import time
import uuid
import gtk

import gobject
from MeteorClient import MeteorClient
import pyscreenshot as ImageGrab
from PIL import Image

from galicaster.core import context
from galicaster.classui import recorderui
from galicaster.recorder import recorder

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

        self.client = MeteorClient(self.meteor,  debug=False)
        self.client.on('added', self.on_added)
        self.client.on('changed', self.on_changed)
        self.client.on('subscribed', self.on_subscribed)
        self.client.on('connected', self.on_connected)
        self.client.on('removed', self.on_removed)
        self.client.on('closed', self.on_closed)
        self.client.on('logged_in', self.on_logged_in)

        self.displayName = conf.get('sussexlogin', 'room_name')
        self.vu_min = -70
        self.vu_range = 40
        self.vu_data = 0
        self.last_vu = None
        self.ip = socket.gethostbyname(socket.gethostname())
        self.id = conf.get('ingest', 'hostname')
        self._user = conf.get('ddp', 'user')
        self._password = conf.get('ddp', 'password')
        self._http_host = conf.get('ddp', 'http_host')
        self._audiostream_port = conf.get('audiostream', 'port') or 31337
        self.netreg_id = conf.get('ddp', 'netreg_id')
        self.store_audio = conf.get_boolean('ddp', 'store_audio')
        self.screenshot = conf.get_boolean('ddp', 'take_screenshot')
        self.screenshot_file = conf.get('ddp', 'existing_screenshot')
        self.paused = False
        self.recording = False
        self.currentMediaPackage = None
        self.currentProfile = None
        self.has_disconnected = False
        self._screen_width = gtk.gdk.screen_width()
        self._screen_height = gtk.gdk.screen_height()

        cam_available = conf.get(
            'sussexlogin',
            'cam_available') #or cam_available
        if cam_available in ('True', 'true', True, '1', 1):
            self.cam_available = 1
        elif cam_available in ('False', 'false', False, '0', 0):
            self.cam_available = 0
        else:
            self.cam_available = int(cam_available)

        # self.audiofaders = []
        # faders = conf.get('ddp', 'audiofaders').split()
        # try:
        #     for fader in faders:
        #         audiofader = {}
        #         fader = 'audiofader-' + fader
        #         audiofader['name'] = conf.get(fader, 'name')
        #         audiofader['display'] = conf.get(fader, 'display')
        #         audiofader['min'] = conf.get_int(fader, 'min')
        #         audiofader['max'] = conf.get_int(fader, 'max')
        #         audiofader['type'] = conf.get(fader, 'type')
        #         audiofader['setrec'] = conf.get_boolean(fader, 'setrec')
        #         audiofader['mute'] = conf.get_boolean(fader, 'mute')
        #         audiofader['unmute'] = conf.get_boolean(fader, 'unmute')
        #         audiofader['setlevel'] = conf.get_int(fader, 'setlevel')
        #         audiofader['control'] = alsaaudio.Mixer(control=audiofader['name'])
        #         self.audiofaders.append(audiofader)
        # except Exception as e:
        #     print e
        # fd, eventmask = self.audiofaders[0]['control'].polldescriptors()[0]
        # self.watchid = gobject.io_add_watch(fd, eventmask, self.mixer_changed)

        dispatcher.connect('galicaster-init', self.on_init)
        dispatcher.connect('update-rec-vumeter', self.vumeter)
        dispatcher.connect('galicaster-notify-timer-short', self.heartbeat)
        dispatcher.connect('galicaster-notify-timer-short', self.update_vu)
        dispatcher.connect('start-before', self.on_start_recording)
        dispatcher.connect('starting-record', self.on_start_manual_recording)
        dispatcher.connect('restart-preview', self.on_stop_recording)
        dispatcher.connect('update-rec-status', self.on_rec_status_update)

    def run(self):
        self.connect()

    def connect(self):
        # FIXME make this a config choice or remove
        #if not self.has_disconnected:
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


    def on_start_manual_recording(self, sender, recorderui=None):
        self.recording = True
        #self.currentMediaPackage = self.media_package_metadata(id)
        self.currentProfile = context.get_state().profile.name
        self.update(
            'rooms', {
                '_id': self.id
            }, {
                '$set': {
                    'currentMediaPackage': None,
                    'currentProfile': self.currentProfile,
                    'recording': self.recording
                }
            })

    def on_start_recording(self, sender, id):
        self.recording = True
        self.currentMediaPackage = self.media_package_metadata(id)
        self.currentProfile = context.get_state().profile.name
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

    def on_stop_recording(self, sender=None):
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

        audio_devices = ['audiotest', 'autoaudio', 'pulse']
        no_support_devices = ['blackmagic']
        for track in context.get_state().profile.tracks:
            if track.device not in audio_devices:
                if track.device in no_support_devices:
                    logger.debug("{0} bin jpg multifilesink unsupported".format(track.device))
                else:
                    track_file = os.path.join('/tmp', track.file + '.jpg')
                    try:
                        if(os.path.getctime(track_file) > time.time() - 4000):
                            files[track.flavor] = (track.flavor + '.jpg',
                                                   open(track_file, 'rb'),
                                                   'image/jpeg')
                    except IOError:
                        logger.warn("Unable to check date of or open file {0}".format(track_file))
        if self.screenshot:
            # take a screenshot with pyscreenshot
            im = ImageGrab.grab(bbox=(10, 10, self._screen_width, self._screen_height), backend='imagemagick')
        else:
            try:
                # used if screenshot already exists
                im = Image.open(self.screenshot_file)
            except IOError as e:
                logger.warn("Unable to open screenshot file {0}".format(self.screenshot_file))
                return
        im.thumbnail((640, 360))
        output = cStringIO.StringIO()
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.save(output, format="JPEG")
        files['galicaster'] = ('galicaster.jpg', output.getvalue(),
                               'image/jpeg')
        try:
            # add verify=False for testing self signed certs
            requests.post("{0}/image/{1}".format(self._http_host, self.id), files=files, auth=(self._user, self._password), verify=False)
        except Exception as e:
            print e
            logger.warn('Unable to post images')

    # def mixer_changed(self, source=None, condition=None, reopen=True):
    #     if reopen:
    #         for audiofader in self.audiofaders:
    #             audiofader['control'] = alsaaudio.Mixer(
    #                 control=audiofader['name'])
    #     self.update_audio()
    #     return True

    def vumeter(self, element, data):
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
        is_paused = data == 'Paused'
        if is_paused:
            self.update_images(.75)
        if self.paused != is_paused:
            self.update(
                'rooms', {
                    '_id': self.id}, {
                    '$set': {
                        'paused': is_paused}})
            self.paused = is_paused
        if data == '  Recording  ':
            #subprocess.call(['killall', 'maliit-server'])
            self.update_images(.75)

    def media_package_metadata(self, id):
        mp = context.get_repository().get(id)
        line = mp.metadata_episode.copy()
        duration = mp.getDuration()
        line["duration"] = long(duration / 1000) if duration else None
        # Does series_title need sanitising as well as duration?
        created = mp.getDate()
        line["created"] = calendar.timegm(created.utctimetuple())
        for key, value in mp.metadata_series.iteritems():
            line["series_" + key] = value
        for key, value in line.iteritems():
            if value in [None, []]:
                line[key] = ''
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
                'netregId': self.netreg_id,
                'inputs': self.inputs(),
                'stream': {
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
                #audio = self.read_audio_settings()
                data['_id'] = self.id
                #data['audio'] = audio
                self.insert('rooms', data)

    def inputs(self):
        inputs = {
            'presentations': ['Presentation']
        }
        inputs['cameras'] = []
        labels = conf.get('sussexlogin', 'matrix_cam_labels')
        cam_labels = []
        if labels:
            cam_labels = [l.strip() for l in labels.split(',')]
        for i in range(0, self.cam_available):
            label = cam_labels[i] if i < len(
                cam_labels) else "Camera %d" % (i + 1)
            inputs['cameras'].append(label)
        return inputs

    # def set_audio(self, fields):
    #     faders = fields.get('audio')
    #     if faders:
    #         for fader in faders:
    #             mixer = None
    #             level = fader.get('level')
    #             for audiofader in self.audiofaders:
    #                 if audiofader['name'] == fader['name']:
    #                     mixer = audiofader['control']
    #                     break
    #             if mixer:
    #                 l, r = mixer.getvolume(fader['type'])
    #                 if level >= 0 and l != level:
    #                     mixer.setvolume(level, 0, fader['type'])
    #                     mixer.setvolume(level, 1, fader['type'])
    #         if self.store_audio:
    #             # Relies on no password sudo access for current user to alsactl
    #             subprocess.call(['sudo', 'alsactl', 'store'])

    def on_added(self, collection, id, fields):
        pass
        #self.set_audio(fields)
        #self.update_audio()

    def on_changed(self, collection, id, fields, cleared):
        #self.set_audio(fields)
        me = self.client.find_one('rooms')
        if self.paused != me['paused']:
            self.set_paused(me['paused'])
        if context.get_state().is_recording != me['recording']:
            self.set_recording(me)

    def on_removed(self, collection, id):
        self.on_subscribed(None)

    def set_paused(self, new_status):
        self.paused = new_status
        dispatcher.emit("toggle-pause-rec")

    def set_recording(self, me):
        self.recording = me['recording']
        if self.recording:
            meta = me.get('currentMediaPackage', {}) or {}
            print meta
            # profile = me.get('currentProfile', 'nocam')
            # series = (meta.get('series_title', ''), meta.get('isPartOf', ''))
            # user = {'user_name': meta.get('creator', ''),
            #         'user_id': meta.get('rightsHolder', '')}
            title = meta.get('title', 'Unknown')
            print title
            # dispatcher.emit('sussexlogin-record',
            #                 (user, title, series, profile))
            dispatcher.emit("manual-record")
        else:
            dispatcher.emit("stop-record", '')

    def on_connected(self):
        logger.info('Connected to Meteor')
        token = conf.get('ddp', 'token')
        self.client.login(self._user, self._password)

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
    #     me = self.client.find_one('rooms')
    #     audio = self.read_audio_settings()
    #     update = False
    #     if me:
    #         mAudio = me.get('audio')
    #         mAudioNames = [x['name'] for x in mAudio]
    #         audioNames = [x['name'] for x in audio]
    #         if set(mAudioNames) != set(audioNames):
    #             update = True
    #         if not update:
    #             for key, fader in enumerate(audio):
    #                 if mAudio[key].get('level') != fader.get('level'):
    #                     update = True
    #         if update:
    #             self.update(
    #                 'rooms', {
    #                     '_id': self.id}, {
    #                     '$set': {
    #                         'audio': audio}})
    #
    # def read_audio_settings(self):
    #     audio_settings = []
    #     for audiofader in self.audiofaders:
    #         if audiofader['display']:
    #             audio_settings.append(
    #                 self.control_values(audiofader)
    #             )
    #         # ensure fixed values
    #         mixer = audiofader['control']
    #         if audiofader['setrec']:
    #             mixer.setrec(1)
    #         if audiofader['mute']:
    #             mixer.setmute(1)
    #         if audiofader['unmute']:
    #             mixer.setmute(0)
    #         if audiofader['setlevel'] >= 0:
    #             mixer.setvolume(audiofader['setlevel'], 0, audiofader['type'])
    #             if 'Joined Playback Volume' not in mixer.volumecap():
    #                 mixer.setvolume(audiofader['setlevel'], 1, audiofader['type'])
    #     return audio_settings
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

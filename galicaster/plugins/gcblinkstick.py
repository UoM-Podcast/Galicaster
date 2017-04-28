import datetime
from gi.repository import GLib
import usb

from blinkstick import blinkstick

from galicaster.core import context
from galicaster.recorder.service import (INIT_STATUS, PREVIEW_STATUS,
                                         RECORDING_STATUS, PAUSED_STATUS,
                                         ERROR_STATUS, Status)
from galicaster.classui.recorderui import TIME_UPCOMING

conf = context.get_conf()
dispatcher = context.get_dispatcher()
logger = context.get_logger()
repo = context.get_repository()
recorder = context.get_recorder()

DEFAULT_REC_COLOR = '#ff0000'
DEFAULT_PAUSE_COLOR = '#ff0000'
DEFAULT_PAUSE_DELAY = 1000
DEFAULT_UPCOMING_COLOR = '#ffff00'

LED_COUNT = 8

# add a fake status to indicate upcoming recording
UPCOMING_STATUS = Status('upcoming', 'Upcoming')


def init():
    rec_color = conf.get('blinkstick', 'rec_color') or DEFAULT_REC_COLOR
    logger.debug('rec_color set to {}'.format(rec_color))
    pause_color = conf.get('blinkstick', 'pause_color') or DEFAULT_PAUSE_COLOR
    logger.debug('pause_color set to {}'.format(pause_color))
    pause_delay = conf.get_int('blinkstick',
                               'pause_delay') or DEFAULT_PAUSE_DELAY
    logger.debug('pause_delay set to {}'.format(pause_delay))
    upcoming_color = conf.get('blinkstick',
                              'upcoming_color') or DEFAULT_UPCOMING_COLOR
    logger.debug('upcoming_color set to {}'.format(upcoming_color))

    BlinkstickPlugin(rec_color=rec_color,
                     pause_color=pause_color,
                     pause_delay=pause_delay,
                     upcoming_color=upcoming_color,
                     upcoming_time=TIME_UPCOMING)


class BlinkstickPlugin():
    def __init__(self, rec_color, pause_color, pause_delay,
                 upcoming_color, upcoming_time):
        self.rec_color = rec_color
        self.pause_color = pause_color
        self.pause_delay = pause_delay
        self.upcoming_color = upcoming_color
        self.upcoming_time = upcoming_time

        self.bs = None
        self.off_color = '#000000'
        self.error = False

        # used to store tag of flash timer so it can be cleared
        self.flash = None

        # tried reading current color from device but seemed to
        # make things more unstable, so this can not be relied upon
        # and is only used to keep track of flashing
        self.led = self.off_color

        dispatcher.connect('timer-short', self._handle_timer)
        dispatcher.connect('recorder-status', self._handle_status_change)
        dispatcher.connect('recorder-upcoming-event', self._handle_upcoming)

        # make sure led is off when plugin starts
        self._handle_timer(self)

    def _handle_upcoming(self, sender):
        # called when the recorderui determines there is a recording upcoming
        self.set_status(UPCOMING_STATUS)

    def _handle_status_change(self, sender, status):
        # called when the record service status changes
        self.set_status(status)

    def _handle_timer(self, sender):
        # called by the timer-short signal
        # to make sure status is correct even if blinkstick unplugged
        # when the recording status changed
        status = recorder.status
        if status is PREVIEW_STATUS:
            next = repo.get_next_mediapackage()
            upcoming = False
            if next is not None:
                start = next.getLocalDate()
                delta = start - datetime.datetime.now()
                upcoming = delta <= datetime.timedelta(
                                                    seconds=self.upcoming_time)
            if upcoming:
                status = UPCOMING_STATUS
        if not self.flash:
            self.set_status(status)

    def set_status(self, status):
        # start flashing (if not already)
        if status is PAUSED_STATUS and not self.flash:
            self.flash = GLib.timeout_add(self.pause_delay, self.set_color,
                                          self.pause_color)
            return

        # not paused so we can stop flashing
        if self.flash:
            GLib.source_remove(self.flash)
        self.flash = None

        if status in [PREVIEW_STATUS, INIT_STATUS, ERROR_STATUS]:
            self.set_color(self.off_color)
        elif status == RECORDING_STATUS:
            self.set_color(self.rec_color)
        elif status == UPCOMING_STATUS:
            self.set_color(self.upcoming_color)

    def set_color(self, hex):
        # make sure we have a reference to a plugged in blinkstick
        if self.bs is None:
            self.bs = self.get_blinkstick()
        if self.bs is None:
            self.flash = None
            return

        # toggle color if flashing
        if self.flash and self.led == hex:
            hex = self.off_color

        # blinkstick square has multiple LEDs
        for i in range(LED_COUNT):
            try:
                self.bs.set_color(index=i, hex=hex)
            except usb.core.USBError:
                logger.warn('USB Error - Retrying LED {}'.format(i))
                # USB I/O errors happen occasionally,
                # probably due to lack of hardware USB?
                # so decrement the index in order to try this LED again
                i = i - 1
            except Exception as e:
                # only show error once or you can end up spamming logs
                if not self.error:
                    logger.error('Blinkstick Error: {}'.format(e))
                    # try and recover blinkstick
                    self.bs = self.get_blinkstick()
                    self.error = True
            else:
                self.error = False

        self.led = hex

        # returns true if still flashing so that glib timer is reset.
        # when false timer will not be called again
        return self.flash

    def get_blinkstick(self):
        bs = None
        try:
            bs = blinkstick.find_first()
        except:
            # more attempts to get around the blinkstick USB flakiness
            logger.warn('Trying to reset USB device...')
            dev = usb.core.find(find_all=False,
                                idVendor=blinkstick.VENDOR_ID,
                                idProduct=blinkstick.PRODUCT_ID)
            if dev:
                dev.reset()
                logger.warn('Reset USB device')
        return bs

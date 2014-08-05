import re
from threading import Timer

import pygst
pygst.require('0.10')
import gst

from galicaster.core import context
from galicaster.utils.gstreamer import WeakMethod

# options:
#  pause_mode = [hold|start_stop] (hold)
#  hold_code = <string> (hold)
#  start_code = <string> (start)
#  stop_code = <string> (stop)
#  prescale = <percentage> (100)
#  resolution = <WidthxHeight> (source) required if prescale < 100
#  hold_timeout = <secs> (1)

ZBAR_MESSAGE_PATTERN = ("timestamp=\(guint64\)(?P<timestamp>[0-9]+), "
                     "type=\(string\)(?P<type>.+), "
                     "symbol=\(string\)(?P<symbol>.+), "
                     "quality=\(int\)(?P<quality>[0-9]+)")

def init():
    try:
        conf = context.get_conf()
        mode = conf.get('qrcode', 'pause_mode') or 'hold'  # or 'start_stop'
        symbols = {}
        symbols['start'] = conf.get('qrcode', 'start_code') or 'start'
        symbols['stop'] = conf.get('qrcode', 'stop_code') or 'stop'
        symbols['hold'] = conf.get('qrcode', 'hold_code') or 'hold'
        prescale = int(conf.get('qrcode', 'prescale')) or 100  # %
        if prescale < 100:
            resolution =  conf.get('qrcode', 'resolution')
        else:
            resolution = 'source';
        hold_timeout = conf.get('qrcode', 'hold_timeout') or 1  # secs
        qr = QRCodeScanner(mode, symbols, hold_timeout, prescale, resolution, context.get_logger())
        
        dispatcher = context.get_dispatcher()
        dispatcher.connect('gst-pipeline-created', qr.qrcode_add_pipeline)
        # only process sync-messages when recording to reduce overhead
        dispatcher.connect('starting-record', qr.qrcode_connect_to_sync_message)
        dispatcher.connect('recording-closed', qr.qrcode_disconnect_to_sync_message)
        
    except ValueError:
        pass


class QRCodeScanner():
  
    def __init__(self, mode, symbols, hold_timeout, prescale, resolution, logger=None):
        self.symbol_start = symbols['start']
        self.symbol_stop = symbols['stop']
        self.symbol_hold = symbols['hold']
        self.mode = mode
        self.prescale = prescale
        self.resolution = resolution
        self.hold_timeout = hold_timeout  # secs
        self.hold_timeout_ps = hold_timeout*1000000000  # pico secs
        self.hold_timestamp = 0
        self.hold_timer = None
        self.hold_timer_timestamp = 0
        self.logger = logger
        self.pipeline = None
        self.bins = None
        self.recording_paused = False
        self.sync_msg_handler = None
        self.msg_pattern = re.compile(ZBAR_MESSAGE_PATTERN)
  
    def qrcode_connect_to_sync_message(self, recorderui):
        #print "Connecting to sync messages"
        dispatcher = context.get_dispatcher()
        self.sync_msg_handler = dispatcher.connect('gst-sync-message', self.qrcode_on_sync_message)
    
    def qrcode_disconnect_to_sync_message(self, recorderui, mpurl):
        #print "Disconnecting from sync messages"
        dispatcher = context.get_dispatcher()
        dispatcher.disconnect(self.sync_msg_handler)

    def qrcode_on_sync_message(self, dispatcher, recorder, bus, message):
        if message.structure.get_name() == "barcode":
            # Message fields are:
            # name, timestamp, type, symbol, quality
            # but there is no get_value function!
            fieldstr = message.structure.to_string()

            m = re.search(self.msg_pattern, fieldstr)
            timestamp = int(m.group('timestamp'))
            type = m.group('type')
            symbol = m.group('symbol')
            quality = int(m.group('quality'))

            # ingore non qrcodes
            if type == 'QR-Code':
                self.handle_symbol(recorder, symbol, timestamp)

    def handle_symbol(self, recorder, symbol, timestamp):
        #print recorder.get_status()
        #print symbol
        gst_status = recorder.get_status()[1]

        if context.get_state().is_recording and gst_status == gst.STATE_PLAYING:
            if self.mode == 'start_stop' :
                if symbol == self.symbol_stop and not self.recording_paused:
                    #print 'PAUSING'
                    self.logger.info('Pause recording at {}'.format(timestamp))
                    self.recording_paused = True
                    recorder.pause_record()

                if symbol == self.symbol_start and self.recording_paused:
                    #print 'RESUMING'
                    self.logger.info('Resume recording at {}'.format(timestamp))
                    self.recording_paused = False
                    recorder.record()
                    
            else: # mode == hold 
                if symbol == self.symbol_hold :
                    # pause
                    if not self.recording_paused:
                        #print 'PAUSING'
                        recorder.pause_record()
                        self.logger.info('Paused recording at {}'.format(timestamp))
                        self.recording_paused = True
                        self.hold_timestamp = 0
                        self.hold_timer = None
                        self.hold_timer_timestamp = 0
                        
                    # setup restart
                    # every hold_timeout create a timer call 2xhold_timeout in the future
                    # max delay in resume is 2x hold_timeout
                    if not self.hold_timer or ((timestamp - self.hold_timer_timestamp) >= self.hold_timeout_ps):
                        #print "Creating timer...{} {}".format(timestamp, self.hold_timer_timestamp)
                        self.hold_timer = Timer(self.hold_timeout*2, self.has_hold_timed_out, [recorder, timestamp])
                        self.hold_timer.start()
                        self.hold_timer_timestamp = timestamp
                    
                    # store this TS
                    self.hold_timestamp = timestamp

    def hold_timed_out(self, recorder):
        #print 'RESUMING'
        self.logger.info('Resume recording at {}'.format(self.hold_timestamp + self.hold_timeout_ps))
        self.recording_paused = False
        recorder.record()  # recorder
        
    def has_hold_timed_out(self, recorder, timestamp):
        #print '...timer testing {} {} {}'.format(timestamp, self.hold_timestamp, self.hold_timestamp-timestamp)       
        # how old is self.hold_timestamp?
        if (self.hold_timestamp-timestamp) < self.hold_timeout_ps:
            #print 'RESUMING {} {}'.format(timestamp, self.hold_timestamp)
            self.logger.info('Resume recording at {}'.format(self.hold_timestamp + self.hold_timeout_ps))
            self.recording_paused = False
            recorder.record()  # recorder
            self.hold_timer = None
        
    # find the video device with the configured flavour
    # and add the zbar pipe to that
    def qrcode_add_pipeline(self, recorder, pipeline, bus, bins):
        for name, bin in bins.iteritems():
            if bin.has_video:
                device = bin.options['device']

                # Create the following subpipe:
                # queue name=zbar-queue ! valve name=zbar-valve drop=False 
                # ! ffmpegcolorspace ! videoscale ! capsfilter name=zbar-filter
                # ! zbar name=zbar message=true ! fakesink'

                zbar_queue = gst.element_factory_make("queue", "zbar-{}-queue".format(device))
                zbar_valve = gst.element_factory_make("valve", "zbar-{}-valve".format(device))
                zbar_ffmpegcs = gst.element_factory_make("ffmpegcolorspace")
                zbar_videoscale = gst.element_factory_make("videoscale")
                zbar_filter = gst.element_factory_make("capsfilter", "zbar-{}-filter".format(device))
                zbar_zbar = gst.element_factory_make("zbar", "zbar-{}-zbar".format(device))
                zbar_fakesink = gst.element_factory_make("fakesink")

                # FIXME: Assumes all video bins are the same size
                if self.prescale < 100:
                    expr='[0-9]+[\,x\:][0-9]+'  # Parse custom size     
                    if re.match(expr,self.resolution): 
                        wh = [int(a) for a in self.resolution.split(re.search('[,x:]', self.resolution).group())]
                    width, height = int(wh[0]*self.prescale/100), int(wh[1]*self.prescale/100)
                    zbar_caps = gst.Caps("video/x-raw-yuv,width={},height={}".format(width, height))
                    zbar_filter.set_property("caps", zbar_caps)
                else :
                    zbar_caps = gst.Caps("video/x-raw-yuv")
                zbar_filter.set_property("caps", zbar_caps)
                
                tee_name = 'gc-' + device + '-tee'
                tee = pipeline.get_by_name(tee_name)

                pipeline.add(zbar_queue, zbar_valve, zbar_ffmpegcs, 
                      zbar_videoscale, zbar_filter,
                      zbar_zbar,zbar_fakesink)
                gst.element_link_many(tee, zbar_queue, zbar_valve, zbar_ffmpegcs, 
                      zbar_videoscale, zbar_filter,
                      zbar_zbar,zbar_fakesink)
                      
        self.pipeline = pipeline
        self.bins = bins

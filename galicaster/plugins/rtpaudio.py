import pygst
pygst.require('0.10')
import gst

from galicaster.core import context

__author__ = 'andrew wilson'


def init():
    try:
        conf = context.get_conf()
        dispatcher = context.get_dispatcher()
        dispatcher.connect('gst-pipeline-created', qrcode_add_pipeline)

    except ValueError:
        pass


def qrcode_add_pipeline(recorder, pipeline, bus, bins):
        for name, bin in bins.iteritems():
            if bin.has_audio:
                device = bin.options['device']

                # Create the following subpipe:
                # queue name=stream-queue ! audio/x-raw-int,channels=1,depth=16,width=16,rate=22000 ! rtpL16pay send-config=true ! udpsink host=127.0.0.1 port=5000
                # lamemp3enc target=1 bitrate=192 cbr=true
                # gst-launch pulsesrc device=alsa_input.usb-Samson_Technologies_Samson_UB1-00-UB1.analog-stereo ! lamemp3enc ! rtpmpapay ! udpsink host=127.0.0.1 port=5000
#                 v=0
# m=audio 5000 RTP/AVP 97
# c=IN IP4 127.0.0.1
# a=rtpmap:97 MPA/90000
                stream_queue = gst.element_factory_make("queue", "stream-{}-queue".format(device))
                #zbar_ffmpegcs = gst.element_factory_make("ffenc_mpeg4")
                # zbar_filter = gst.element_factory_make("capsfilter", "zbar-{}-filter".format(device))
                #zbar_caps = gst.Caps("audio/x-raw-int,channels=1,depth=16,width=16,rate=22000")
                # zbar_filter.set_property("caps", zbar_caps)
                stream_enc = gst.element_factory_make("lamemp3enc", "lamemp3enc")
                #faudioenc.set_property("target", 1)
                #faudioenc.set_property("bitrate", 128)
                # faudioenc.set_property("cbr", "true")
                stream_rtp = gst.element_factory_make("rtpmpapay")
                stream_rtp.set_property('pt', 97)
                #zbar_videoscale.set_property('send-config', 'true')
                stream_udpsink = gst.element_factory_make("udpsink")
                stream_udpsink.set_property('host', '127.0.0.1')
                stream_udpsink.set_property('port', 5000)

                tee_name = 'tee-aud'
                tee = pipeline.get_by_name(tee_name)

                pipeline.add(stream_queue, stream_enc, stream_rtp, stream_udpsink)
                gst.element_link_many(tee, stream_queue, stream_enc, stream_rtp, stream_udpsink)

        pipeline = pipeline
        bins = bins

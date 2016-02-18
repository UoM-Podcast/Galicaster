import pygst
pygst.require('0.10')
import gst

from galicaster.core import context

__author__ = 'andrew wilson'


def init():
    try:
        conf = context.get_conf()
        dispatcher = context.get_dispatcher()
        dispatcher.connect('gst-pipeline-created', stream)

    except ValueError:
        pass


def stream(recorder, pipeline, bus, bins):
        for name, bin in bins.iteritems():
            if bin.has_video:
                device = bin.options['device']

                # Create the following subpipe:
                # video only
                # queue name=stream-queue ! ffenc_mpeg4 ! rtpmp4vpay send-config=true ! udpsink host=127.0.0.1 port=5000
# v=0
# m=video 5000 RTP/AVP 96
# a=rtpmap:96 MP4V-ES/90000
# c=IN IP4 127.0.0.1
                stream_queue = gst.element_factory_make("queue", "stream-{}-queue".format(device))
                stream_ffmpegcs = gst.element_factory_make("ffenc_mpeg4")
                stream_rtp = gst.element_factory_make("rtpmp4vpay")
                stream_rtp.set_property('send-config', 'true')
                stream_rtp.set_property('pt', 96)
                stream_udpsink = gst.element_factory_make("udpsink")
                stream_udpsink.set_property('host', '127.0.0.1')
                stream_udpsink.set_property('port', 5004)

                tee_name = 'gc-' + device + '-tee'
                tee = pipeline.get_by_name(tee_name)

                pipeline.add(stream_queue, stream_ffmpegcs, stream_rtp, stream_udpsink)
                gst.element_link_many(tee, stream_queue, stream_ffmpegcs, stream_rtp, stream_udpsink)

        pipeline = pipeline
        bins = bins

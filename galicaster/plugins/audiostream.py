# AudioStream galicaster plugin
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

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import os
import requests
from SocketServer import ThreadingMixIn
import subprocess
from threading import Thread
from galicaster.core import context

conf = context.get_conf()
dispatcher = context.get_dispatcher()
_http_host = conf.get('ddp', 'http_host')
_id = conf.get('ingest', 'hostname')
_port = conf.get_int('audiostream', 'port') or 31337
src = conf.get('audiostream', 'src') or 'alsasrc'
device = conf.get('audiostream', 'device') or None
if device:
    device_params = 'device=' + device
else:
    device_params = ''


def init():
    audiostream = AudioStream()
    audiostream.start()


class AudioStream(Thread):

    def __init__(self):
        Thread.__init__(self)
        serveraddr = ('', _port)
        server = ThreadedHTTPServer(serveraddr, AudioStreamer)
        server.allow_reuse_address = True
        server.timeout = 30
        self.server = server
        dispatcher.connect('action-quit', self.shutdown)

    def run(self):
        self.server.serve_forever()

    def shutdown(self, whatever):
        self.server.shutdown()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class AudioStreamer(BaseHTTPRequestHandler):
    def _writeheaders(self):

        self.send_response(200)  # 200 OK http response
        self.send_header('Content-type', 'audio/mpeg')
        self.end_headers()

    def _not_allowed(self):
        self.send_response(403)  # 200 OK http response
        self.end_headers()

    def do_HEAD(self):
        self._writeheaders()

    def do_GET(self):
        data = {'_id': _id, 'streamKey': self.path[1:]}
        r = requests.post(_http_host + '/stream_key', data=data)
        # key
        try:
            self._writeheaders()
            DataChunkSize = 10000
            devnull = open(os.devnull, 'wb')
            command = 'gst-launch-1.0 {} {} ! '.format(src, device_params) + \
                      'lamemp3enc bitrate=128 cbr=true ! ' + \
                      'filesink location=/dev/stdout'
            p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=devnull,
                bufsize=-1,
                shell=True)
            while(p.poll() is None):
                stdoutdata = p.stdout.read(DataChunkSize)
                self.wfile.write(stdoutdata)
            stdoutdata = p.stdout.read(DataChunkSize)
            self.wfile.write(stdoutdata)

        except Exception:
            pass
        p.kill()

        try:
            self.wfile.flush()
            self.wfile.close()
        except:
            pass

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except:
            self.close_connection = 1
            self.rfile = None
            self.wfile = None

    def finish(self):
        try:
            BaseHTTPRequestHandler.finish(self)
        except:
            pass
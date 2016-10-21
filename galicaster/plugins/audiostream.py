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
_port = conf.get('audiostream', 'port') or 31337


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
            command = 'gst-launch-1.0 alsasrc ! ' + \
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
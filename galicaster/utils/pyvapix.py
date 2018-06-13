import requests
from requests.auth import HTTPDigestAuth
import io
from PIL import Image


class Vapix(object):

    def __init__(self, ip='192.168.0.90', username='root', password='pass', debug=None):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = 'http://{}/axis-cgi/'.format(ip)
        self.debug_mode = debug
        self.headers = {'X-Requested-Auth': 'Digest'}

    def user_or_password_error(self):
        # FIXME raise an exception
        print('[-] Username or password error')

    def error_with_status_code(self, r):
        # FIXME raise an exception
        print('[-] Error: ' + str(r.status_code))

    def get_VAPIX_version(self):
        """ displays the version of Axis VAPIX API supported by the camera """
        try:
            print('[*] Requesting VAPIX version...')
            r = requests.get(self.base_url + 'param.cgi?action=list&group=Properties.API.HTTP.Version')
            if r.status_code == 200:
                r = str(r.content.decode('utf-8'))
                vapix_version = r.split("=")[1]
                print('[+] VAPIX version: ' + vapix_version)

            elif r.status_code == 401:
                self.user_or_password_error()

            else:
                self.error_with_status_code(r)

        except:
            print('[-] Error: getting VAPIX verision')
            pass

    def restart(self):
        """ Restarts the Axis camera """
        try:
            r = requests.get(self.base_url + '/admin/restart.cgi')
            print('[*] Restaring ' + self.ip)
            if r.status_code == 200:
                print('[+] Axis camera has been restarted successfully')
            elif r.status_code == 401:
                self.user_or_password_error()
            else:
                self.error_with_status_code(r)
        except:
            self.error_with_status_code(r)
            pass

    def display_live_image(self):
        """ Gets the latest image from the camera and displays it using PIL package """
        r = requests.get(self.base_url + 'jpg/image.cgi')
        if r.status_code == 200:
            f = io.BytesIO(r.content)
            img = Image.open(f)
            img.show()

    def set_overlay_text(self, text='test'):
        requests.get(self.base_url + 'param.cgi?action=update%20&Image.I0.Text.TextEnabled=yes&Image.I0.Text.String=' + text)

    def _handle_request(self, request_type, request_data):
        """
        will only handle GET, POST requests
        :param request_type:
        :param request_data:
        :return:
        """
        if self.debug_mode:
            print('[+] DEBUG MODE ENABLED: not sending requests')
            return True

        r = None

        if request_type == 'POST':
            try:
                headers = {'X-Requested-Auth': 'Digest'}
                r = requests.post(self.base_url + request_data, headers=headers, auth=HTTPDigestAuth(self.username, self.password), timeout=5)
            except Exception as e:
                #FIXME this should be a specific exception
                print('[-] Error: ' + str(e))
                return True

        if request_type == 'GET':
            try:
                headers = {'X-Requested-Auth': 'Digest'}
                r = requests.get(self.base_url + request_data, headers=headers, auth=HTTPDigestAuth(self.username, self.password), timeout=5)
            except Exception as e:
                #FIXME this should be a specific exception
                print('[-] Error: ' + str(e))
                return True

        if r and self._handle_status(r):
            print('[+] VAPIX HTTP request successful')
            return True

    def _handle_status(self, request):
        if request.status_code == 200:
            return True

        if request.status_code == 204:
            return True

        elif request.status_code == 401:
            self.user_or_password_error()
            return False

        else:
            self.error_with_status_code(request)
            return False


    def continuouspantiltmove(self, pan_dir_speed, tilt_dir_speed):
        """
        Continuous pan/tilt motion. Positive values mean right (pan) and up (tilt), negative values mean left (pan) and
        down (tilt). 0,0 means stop. Values as <pan speed>,<tilt speed>.
        :param pan_dir_speed: <int>
        :param tilt_dir_speed: <int>
        :return:
        """
        # FIXME figure out how to print out if movement request is left, right, up or down is happening from the number
        print('[*] moving camera: ' + pan_dir_speed, tilt_dir_speed)
        self._handle_request('GET', 'com/ptz.cgi?continuouspantiltmove={},{}'.format(pan_dir_speed, tilt_dir_speed))

    def stop(self):
        self._handle_request('GET', 'com/ptz.cgi?continuouspantiltmove={},{}'.format('0', '0'))

    def continuouszoommove(self, zoom_type_speed):
        """
        Continuous zoom motion. Positive values mean zoom in and negative values mean zoom out. 0 means stop.
        :param zoom_type_speed: <int>
        :return:
        """
        # FIXME figure out how to print out if zoom in or zoom out request is happening from the number
        print('[*] zooming camera: ' + zoom_type_speed)
        self._handle_request('GET', 'com/ptz.cgi?continuouszoommove={}'.format(zoom_type_speed))

    def move(self, move_cmd):
        """
        Absolute:Moves the image 25 % of the image field width in the specified direction. Relative: Moves the device
        approx. 50-90 degrees in the specified direction.
        home = Moves the image to the home position.
        up = Moves the image up.
        down = Moves the image down.
        left = Moves the image to the left.
        right = Moves the image to the right.
        upleft = Moves the image up diagonal to the left.
        upright = Moves the image up diagonal to the right.
        downleft = Moves the image down diagonal to the left.
        downright = Moves the image down diagonal to the right.
        stop = Stops the pan/tilt movement
        :param move_cmd: <string>
        :return:
        """
        print('[*] moving camera: ' + move_cmd)
        self._handle_request('GET', 'com/ptz.cgi?move={}'.format(move_cmd))

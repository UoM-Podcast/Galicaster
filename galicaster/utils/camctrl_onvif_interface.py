from onvif import ONVIFCamera
import os

# for use with Galicaster only
from galicaster.core import context
# TODO remove prints
# TODO split identify_presets in two

'''
If getting bad request while connecting, check cameras date and time 
settings and make sure it has the same time as the operating machine.
'''
# DEFAULTS
HOMEPATH = os.path.expanduser("~/.local/wsdl")
SYSPATH = '/etc/onvif/wsdl'

class AXIS_V5915():
    
    # connect to the Galicaster logger
    global logger
    logger = context.get_logger()

    # Connection to the onvif protocol with credentials
    def connect(self, ip, port, username, password):
        global ptz, img
        # Connect to ONVIF camera
        logger.info('IP camera initialization...')
        if os.path.exists(SYSPATH):
            path = SYSPATH
        else:
            path = HOMEPATH
        mycam = ONVIFCamera(ip, port, username, password, path)
        host = mycam.devicemgmt.GetHostname()
        logger.info('  Connected to ONVIF camera ' + str(host.Name))


        # Create media service object
        logger.info('  Creating media service...')
        media = mycam.create_media_service()
        logger.info('  Creating media service... Done.')
        # Get media profile (first element if we don't have multiple profiles)
        media_profiles = media.GetProfiles()
        media_profile_h264 = media_profiles[0]
        #  media_profile_jpg = media_profiles[1]

        # Get video sources
        #  video_source = media.GetVideoSources()[0]

        # We need the profile token
        token = media_profile_h264._token

        # PTZ
        # Create ptz service object
        logger.info('  Creating PTZ service...')
        ptz = mycam.create_ptz_service()
        logger.info('  Creating PTZ service... Done.')

        # Next we want to automatically define all functions, in requesting those from the ptz-service
        self.define_requests(token)

    def define_requests(self, token):
        logger.info('  Defining requests...')
        global req_move, req_stop, req_set_preset, req_remove_preset, \
            req_get_presets, req_goto_preset, req_set_home, req_goto_home

        req_move = ptz.create_type('ContinuousMove')
        req_move.ProfileToken = token

        req_stop = ptz.create_type('Stop')
        req_stop.ProfileToken = token

        req_set_preset = ptz.create_type('SetPreset')
        req_set_preset.ProfileToken = token

        req_remove_preset = ptz.create_type("RemovePreset")
        req_remove_preset.ProfileToken = token

        req_get_presets = ptz.create_type("GetPresets")
        req_get_presets.ProfileToken = token

        req_goto_preset = ptz.create_type('GotoPreset')
        req_goto_preset.ProfileToken = token

        req_set_home = ptz.create_type('SetHomePosition')
        req_set_home.ProfileToken = token

        req_goto_home = ptz.create_type('GotoHomePosition')
        req_goto_home.ProfileToken = token

        logger.info('  Defining requests... Done.')
        logger.info('Ip camera initialization... Done.')

    # ptz functionality
    # stop all current and pending ptz actions
    def stop(self):
        req_stop.PanTilt = True
        req_stop.Zoom = True
        ptz.Stop(req_stop)

    # NOTE: Absolute and relative movment cannot be implemented,
    # so all movement is done with continuous movement
    # Continuous movement for x seconds
    def go_left(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = -speed
        req_move.Velocity.PanTilt._y = 0.0
        ptz.ContinuousMove(req_move)

    def go_right(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = speed
        req_move.Velocity.PanTilt._y = 0.0
        ptz.ContinuousMove(req_move)

    def go_down(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = 0.0
        req_move.Velocity.PanTilt._y = -speed
        ptz.ContinuousMove(req_move)

    def go_up(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = 0.0
        req_move.Velocity.PanTilt._y = speed
        ptz.ContinuousMove(req_move)

    def go_right_up(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = speed
        req_move.Velocity.PanTilt._y = speed
        ptz.ContinuousMove(req_move)

    def go_left_up(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = -speed
        req_move.Velocity.PanTilt._y = speed
        ptz.ContinuousMove(req_move)

    def go_right_down(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = speed
        req_move.Velocity.PanTilt._y = -speed
        ptz.ContinuousMove(req_move)

    def go_left_down(self, speed):
        self.stop()
        req_move.Velocity.Zoom._x = 0.0
        req_move.Velocity.PanTilt._x = -speed
        req_move.Velocity.PanTilt._y = -speed
        ptz.ContinuousMove(req_move)


    # presets and home
    # Go to home preset
    def go_home(self):
        ptz.GotoHomePosition(req_goto_home)

    #Sets current Position to the new home preset
    def set_home(self):
        ptz.SetHomePosition(req_set_home)

    # Changes current Camera Position to a preset by its number (use identifyPreset to go by name)
    def go_to_preset(self, number):
        req_goto_preset.PresetToken = number
        ptz.GotoPreset(req_goto_preset)
        logger.debug('Going to Preset %s', number)

    # Sets the current Camera Position to a new Preset, with the "name" attribute
    # setPreset takes the next free available number, starting with "2"
    def set_preset(self, name):
        self.stop()
        req_set_preset.PresetName = name
        preset = ptz.SetPreset(req_set_preset)
        logger.debug('Current Position set to Preset %s', preset)

    # Remove a preset by its number (use identifyPreset to delete by name)
    def remove_preset(self, number):
        req_remove_preset.PresetToken = number
        ptz.RemovePreset(req_remove_preset)
        logger.debug('Removed Preset %s', number)

    # Get a list of all present presets except for preset number 1 which is home
    def get_presets(self):
        PresetList = ptz.GetPresets(req_get_presets)
        return PresetList

    # Identify a preset by its "name"
    def identify_preset(self, name):
        for preset in ptz.GetPresets(req_get_presets):
            if preset.Name == name:
                number = preset._token
                return number

    # Identify a preset by its "number"
    def identify_preset_number(self, number):
        for preset in ptz.GetPresets(req_get_presets):
            if preset._token == number:
                name = preset.Name
                return name

    # zoom
    def zoom_in(self, speed):
        self.stop()
        req_move.Velocity.PanTilt._x = 0.0
        req_move.Velocity.PanTilt._y = 0.0
        req_move.Velocity.Zoom._x = speed
        ptz.ContinuousMove(req_move)

    def zoom_out(self, speed):
        self.stop()
        req_move.Velocity.PanTilt._x = 0.0
        req_move.Velocity.PanTilt._y = 0.0
        req_move.Velocity.Zoom._x = -speed
        ptz.ContinuousMove(req_move)

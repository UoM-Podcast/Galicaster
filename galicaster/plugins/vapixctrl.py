"""Copyright (C) 2017  The University of Manchester

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""


import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, Pango
from galicaster.core import context
from galicaster.classui import get_ui_path
from galicaster.classui import get_image_path
import galicaster.utils.pyvapix as vapix


# DEFAULTS
# This is the default  device this plugin talks to
DEFAULT_DEVICE = 1

# This is the default preset to set when the camera is recording
DEFAULT_RECORD_PRESET = "record"
DEFAULT_RECORD_PRESET_INT = 0

# This is the default preset to set when the camera is switching off
DEFAULT_IDLE_PRESET = "idle"
DEFAULT_IDLE_PRESET_INT = 5

# This is the key containing the preset to use when recording
RECORD_PRESET_KEY = 'record-preset'

# This is the key containing the preset to set the camera to just after switching it off
IDLE_PRESET_KEY= 'idle-preset'

# This is the key containing the port (path to the device) to use when recording
PORT_KEY = "serial-port"

# This is the key specifying the backend (  or vapix)
BACKEND = 'backend'

# This is the name of this plugin's section in the configuration file
CONFIG_SECTION = "camctrl"

# This are the credentials, which have to be set in the configuration file
IPADDRESS = "ip"
USERNAME = "username"
PASSWORD = "password"
PORT = "port"

# DEFAULt VALUES
DEFAULT_PORT = 80

#  
DEFAULT_MOVESCALE = 7
DEFAULT_BRIGHTNESS = 15
DEFAULT_BRIGHTSCALE = 0
DEFAULT_ZOOM = 0
DEFAULT_ZOOMSCALE = 3.5

# vapix
DEFAULT_ZOOMSCALE_vapix = '30'
DEFAULT_MOVESCALE_vapix = '30'


def init():
    global recorder, dispatcher, logger, config, repo

    config = context.get_conf().get_section(CONFIG_SECTION) or {}
    dispatcher = context.get_dispatcher()
    repo = context.get_repository()
    logger = context.get_logger()
    recorder = context.get_recorder()

    backend = config.get(BACKEND)

    if backend == "vapix":
        # global cam
        global axis_http
        import galicaster.utils.pyvapix as camera
        import galicaster.utils.camctrl_http_interface as axis_web
        # connect to the camera
        ip = config.get(IPADDRESS)
        username = config.get(USERNAME)
        password = config.get(PASSWORD)
        # Initiate axis web UI
        web_username = config.get('web_username')
        web_password = config.get('web_password')
        axis_http = axis_web.AxisWeb(ip, web_username, web_password)

        # cam = camera.Vapix(ip, username, password)
        # initiate the vapix user interface
        dispatcher.connect("init", init_vapix_ui)
    else:
        logger.warn("WARNING: You have to choose a backend in the config file before starting Galicaster, otherwise the cameracontrol plugin does not work.")
        raise RuntimeError("No backend for the cameracontrol plugin defined.") 
    logger.info("Camera connected.")


def init_vapix_ui(element):
    """
    build the galicaster UI tab for the vapix controls
    :param element: 
    :return: 
    """
    global recorder_ui, movescale, zoomscale, presetdelbutton, flybutton, builder, prefbutton, newpreset, movelabel, zoomlabel, res, bins

    vapix = vapix_interface()
    dispatcher.connect("recorder-starting", vapix.on_start_recording)
    dispatcher.connect("recorder-stopped", vapix.on_stop_recording)

    recorder_ui = context.get_mainwindow().nbox.get_nth_page(0).gui

    # load css file
    # css = Gtk.CssProvider()
    # css.load_from_path(get_ui_path("camctrl.css"))
    #
    # Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())
    # Gtk.StyleContext.add_provider_for_screen(
    #     Gdk.Screen.get_default(),
    #     css,
    #     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    # )

    # load glade file
    builder = Gtk.Builder()
    builder.add_from_file(get_ui_path("camctrl-vapix.glade"))

    # calculate resolution for scaling
    window_size = context.get_mainwindow().get_size()
    res = window_size[0]/1920.0

    # scale images
    imgs = ["ctrl", "zoom"]
    for i in imgs:
        get_stock_icon(i)
    # scale label
    labels = []
    for i in labels:
        get_label(i)


    # add new settings tab to the notebook
    notebook = recorder_ui.get_object("data_panel")
    mainbox = builder.get_object("mainbox")

    notebook.append_page(mainbox, get_label("notebook"))

    notebook.show_all()

    # buttons
    # movement
    button = builder.get_object("left")
    button.add(get_icon("left"))
    button.connect("pressed", vapix.move_left)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("leftup")
    button.add(get_icon("leftup"))
    button.connect("pressed", vapix.move_leftup)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("leftdown")
    button.add(get_icon("leftdown"))
    button.connect("pressed", vapix.move_leftdown)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("right")
    button.add(get_icon("right"))
    button.connect("pressed", vapix.move_right)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("rightup")
    button.add(get_icon("rightup"))
    button.connect("pressed", vapix.move_rightup)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("rightdown")
    button.add(get_icon("rightdown"))
    button.connect("pressed", vapix.move_rightdown)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("up")
    button.add(get_icon("up"))
    button.connect("pressed", vapix.move_up)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("down")
    button.add(get_icon("down"))
    button.connect("pressed", vapix.move_down)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("home")
    button.add(get_icon("home"))
    button.connect("clicked", vapix.move_home)

    # zoom
    button = builder.get_object("zoomin")
    button.add(get_stock_icon("zoomin"))
    button.connect("pressed", vapix.zoom_in)
    button.connect("released", vapix.stop_move)

    button = builder.get_object("zoomout")
    button.add(get_stock_icon("zoomout"))
    button.connect("pressed", vapix.zoom_out)
    button.connect("released", vapix.stop_move)

    # add cameras to a selection list
    camlist = builder.get_object("comboboxtext1")

    try:
        bins = recorder.recorder.bins
    except AttributeError as e:
        print e

    for name, bin in bins.iteritems():
        if bin.options['type'] == 'video/camera':
            camlist.append(name, name)
            # if me['ptzmove'].split('_')[2] == name.split('_')[1]:
            #     # print name
            #     cam_ip = str(bin.options['location'].split('@')[1].split(':')[0]).strip()
            #     # print cam_ip
            #     self.last_cam_ip = cam_ip

    # for cams in ['cam1', 'cam2']:
    #
    #     camlist.append(cams, cams)
    camlist.set_active(0)
    camlist.connect("changed", vapix.change_cam)

    #REMOVED
    # # presets
    # # presetlist = builder.get_object("preset_list")
    # # add home position to list
    # # presetlist.insert(0, "home", "home")
    # # fill the list with current presets
    # for preset in cam.get_presets():
    #     # presetlist.append(preset.Name, preset.Name)
    # # presetlist.connect("changed", vapix.change_preset)
    #
    # # to set a new preset
    # newpreset = builder.get_object("newpreset")
    # newpreset.connect("activate", vapix.save_preset)
    # newpreset.connect("icon-press", vapix.save_preset_icon)
    #
    #
    # # to delete a preset
    # presetdelbutton = builder.get_object("presetdel")
    # presetdelbutton.add(get_stock_icon("presetdel"))
    # presetdelbutton.connect("clicked", vapix.empty_entry)
# REMOVED
    # # fly-mode for camera-movement
    # flybutton = builder.get_object("fly")
    # flybutton.add(get_stock_icon("fly"))
    # flybutton.connect("clicked", vapix.fly_mode)
    #
    # # reset all settings
    # button = builder.get_object("reset")
    # button.add(get_stock_icon("reset"))
    # button.connect("clicked", vapix.reset)
# REMOVED
    # # show/hide preferences
    # prefbutton = builder.get_object("pref")
    # prefbutton.add(get_stock_icon("settings"))
    # prefbutton.connect("clicked", vapix.show_pref)

    movescale = builder.get_object("movescale")
    movelabel = get_label("move")
    movelabel.set_text("{0:.1f}".format(movescale.get_value() * 100))
    movescale.connect("value-changed", vapix.set_move)

    zoomscale = builder.get_object("zoomscale")
    zoomlabel = get_label("zoom")
    zoomlabel.set_text("{0:.1f}".format(zoomscale.get_value() * 100))
    zoomscale.connect("value-changed", vapix.set_zoom)


class vapix_interface():

    def __init__(self):
        # set the default camera name from the camera profile names in the config
        self.camera_names = []
        self.camera_ips = []
        self.camera_users = []
        self.camera_passes = []
        self.bins = {}
        try:
            self.bins = recorder.recorder.bins
        except AttributeError as e:
            print e

        for name, bin in self.bins.iteritems():
            if bin.options['type'] == 'video/camera':
                self.camera_names.append(name)
                self.camera_ips.append(str(bin.options['location'].split('@')[1].split(':')[0]).strip())
                self.camera_users.append(str(bin.options['location'].split('@')[0].split(':')[1].split('//')[1]))
                self.camera_passes.append(str(bin.options['location'].split('@')[0].split(':')[2]))
        self.camera_name = self.camera_names[0]
        self.camera_ip = self.camera_ips[0]
        self.camera_user = self.camera_users[0]
        self.camera_pass = self.camera_passes[0]

    # movement functions
    def move_left(self, button):
        print self.camera_name
        print self.camera_ip
        print self.camera_user
        print self.camera_pass
        logger.debug("I move left")
        self.send_ptz('-' + str(movescale.get_value() * 100), '0')
        # presetlist.set_active(-1)


    def move_leftup(self, button):
        logger.debug("I move leftup")
        self.send_ptz('-' + str(movescale.get_value() * 100), str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def move_leftdown(self, button):
        logger.debug("I move leftdown")
        self.send_ptz('-' + str(movescale.get_value() * 100), '-' + str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def move_right(self, button):
        logger.debug("I move right")
        self.send_ptz(str(movescale.get_value() * 100), '0')
        # presetlist.set_active(-1)


    def move_rightup(self, button):
        logger.debug("I move rightup")
        self.send_ptz(str(movescale.get_value() * 100), str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def move_rightdown(self, button):
        logger.debug("I move rightdown")
        self.send_ptz(str(movescale.get_value() * 100), '-' + str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def move_up(self, button):
        logger.debug("I move up")
        self.send_ptz('0', str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def move_down(self, button):
        logger.debug("I move down")
        self.send_ptz('0', '-' + str(movescale.get_value() * 100))
        # presetlist.set_active(-1)


    def stop_move(self, button):
        logger.debug("I make a break")
        vapix.Vapix(ip=self.camera_ip, username=self.camera_user, password=self.camera_pass).stop()
        self.send_ptzzoom('0')


    def move_home(self, button):
        logger.debug("I move home")
        self.send_ptzhome('home')
        # # presetlist.set_active_id("home")


    # zoom functions
    def zoom_in(self, button):
        logger.debug("zoom in")
        self.send_ptzzoom(str(zoomscale.get_value() * 100))
        # presetlist.set_active(-1)


    def zoom_out(self, button):
        logger.debug("zoom out")
        self.send_ptzzoom('-' + str(zoomscale.get_value() * 100))
        # presetlist.set_active(-1)

    #COMMAND EXECUTION
    def send_ptz(self, cmd1, cmd2):
        # send ptz commands to the specified camera
        vapix.Vapix(ip=self.camera_ip, username=self.camera_user, password=self.camera_pass).continuouspantiltmove(cmd1,cmd2)

    def send_ptzhome(self, cmd1):
        # send absolute ptz commands to the specified camera
        vapix.Vapix(ip=self.camera_ip, username=self.camera_user, password=self.camera_pass).move(cmd1)

    def send_ptzzoom(self, cmd1):
        # send ptz zoom commands to the specified camera
        vapix.Vapix(ip=self.camera_ip, username=self.camera_user, password=self.camera_pass).continuouszoommove(cmd1)

    # MOVING ZOOMING SPEEDS
    def set_zoom(self, zoomscale):
        zoomlabel.set_text("{0:.1f}".format(zoomscale.get_value()))

    def set_move(self, movescale):
        movelabel.set_text("{0:.1f}".format( movescale.get_value() * 100))

    def on_start_recording(self, elem):

        preset = config.get(RECORD_PRESET_KEY, DEFAULT_RECORD_PRESET)
        mp = repo.get_next_mediapackage()
        axis_http.tallyled(True)
        if mp is not None:
                try:
                    properties = mp.getOCCaptureAgentProperties()
                    preset = properties['org.opencastproject.workflow.config.cameraPreset']
                except Exception as e:
                    logger.warn("Error loading a preset from the OC properties! Error:", e)

        try:
            pass
            # presetlist.set_active_id(preset)
            #  cam.goToPreset(cam.identifyPreset(preset))

        except Exception as e:
            logger.warn("Error accessing the IP camera on recording start. The recording may be incorrect! Error:", e)


    def on_stop_recording(self, elem, elem2):
        axis_http.tallyled(False)
        try:
            pass
            # presetlist.set_active_id(config.get(IDLE_PRESET_KEY, DEFAULT_IDLE_PRESET))
            #  cam.goToPreset(cam.identifyPreset(config.get(IDLE_PRESET_KEY, DEFAULT_IDLE_PRESET)))

        except Exception as e:
            logger.warn("Error accessing the IP camera on recording end. The recording may be incorrect! Error: ", e)

    def change_cam(self, cam_option):
        # changing which camea is used
        self.camera_name = cam_option.get_active_text()
        for name, bin in self.bins.iteritems():
            if bin.options['type'] == 'video/camera':
                if self.camera_name == name:
                    self.camera_ip = str(bin.options['location'].split('@')[1].split(':')[0]).strip()
                    self.camera_user = str(bin.options['location'].split('@')[0].split(':')[1].split('//')[1])
                    self.camera_pass = str(bin.options['location'].split('@')[0].split(':')[2])


def get_icon(imgname):
    size = res * 56
    pix = GdkPixbuf.Pixbuf.new_from_file_at_size(get_image_path("img/"+imgname+".svg"), size, size)
    img = Gtk.Image.new_from_pixbuf(pix)
    img.show()
    return img

def get_stock_icon(imgname):
    size = res * 28
    if imgname == "stop":
        size = res * 56
    if imgname == "zoomin":
        size = res * 56
    img = builder.get_object(imgname+"img")
    img.set_pixel_size(size)
    img.show()
    return img

def get_label(labelname):
    label = builder.get_object(labelname+"_label")
    size = res * 18
    if labelname == "settings" \
       or labelname == "control":
        size = res * 20
    elif labelname == "notebook":
        size = res * 20
        label.set_property("ypad",10)
        #  label.set_property("xpad",5)
        #  label.set_property("vexpand-set",True)
        #  label.set_property("vexpand",True)
    elif labelname == "bright" or \
            labelname == "move" or \
            labelname == "zoom":
        size = res * 14
    label.set_use_markup(True)
    label.modify_font(Pango.FontDescription(str(size)))
    return label
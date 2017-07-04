"""Copyright (C) 2017  Robin Lachmann

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


# DEFAULTS
# This is the default Visca device this plugin talks to
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

# This is the key specifying the backend (visca or onvif)
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

# VISCA
DEFAULT_MOVESCALE = 7
DEFAULT_BRIGHTNESS = 15
DEFAULT_BRIGHTSCALE = 0
DEFAULT_ZOOM = 0
DEFAULT_ZOOMSCALE = 3.5

# ONVIF
DEFAULT_ZOOMSCALE_ONVIF = 0.5
DEFAULT_MOVESCALE_0NVIF = 0.5


def init():
    global recorder, dispatcher, logger, config, repo

    config = context.get_conf().get_section(CONFIG_SECTION) or {}
    dispatcher = context.get_dispatcher()
    repo = context.get_repository()
    logger = context.get_logger()

    backend = config.get(BACKEND)

    if backend == "onvif":
        global cam
        import galicaster.utils.camctrl_onvif_interface as camera
        # connect to the camera
        ip = config.get(IPADDRESS)
        username = config.get(USERNAME)
        password = config.get(PASSWORD)
        if config.get(PORT) is None:
            port = DEFAULT_PORT
        else:
            port = config.get(PORT)
        cam = camera.AXIS_V5915()
        cam.connect(ip, port, username, password)
        # initiate the onvif user interface
        dispatcher.connect("init", init_onvif_ui)
    elif backend == "visca":
        global pysca 
        import galicaster.utils.pysca as pysca
        # If port is not defined, a None value will make this method fail
        pysca.connect(config.get(PORT_KEY))
        # initiate the visca user interface
        dispatcher.connect("init", init_visca_ui)
    else:
        logger.warn("WARNING: You have to choose a backend in the config file before starting Galicaster, otherwise the cameracontrol plugin does not work.")
        raise RuntimeError("No backend for the cameracontrol plugin defined.") 
    logger.info("Camera connected.")


# VISCA USER INTERFACE
def init_visca_ui(element):
    global recorder_ui, brightscale, movescale, zoomscale, presetbutton, flybutton, builder, onoffbutton, prefbutton, zoomlabel, movelabel, brightlabel, res

    visca = visca_interface()

    dispatcher.connect('recorder-starting', visca.on_start_recording)
    dispatcher.connect('recorder-stopped', visca.on_stop_recording)

    recorder_ui = context.get_mainwindow().nbox.get_nth_page(0).gui

    # load css file
    css = Gtk.CssProvider()
    css.load_from_path(get_ui_path("camctrl.css"))

    Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # load glade file
    builder = Gtk.Builder()
    builder.add_from_file(get_ui_path("camctrl-visca.glade"))

    # calculate resolution for scaling
    window_size = context.get_mainwindow().get_size()
    res = window_size[0]/1920.0

    # scale images
    imgs = ["ctrl", "zoom", "bright", "dummy", "settings"]
    for i in imgs:
        get_stock_icon(i)
    # scale label
    labels = ["control", "settings", "1", "2", "3", "4", "5", "6"]
    for i in labels:
        get_label(i)


    # add new settings tab to the notebook
    notebook = recorder_ui.get_object("data_panel")
    mainbox = builder.get_object("mainbox")

    notebook.append_page(mainbox, get_label("notebook"))

    # buttons
    # movement
    button = builder.get_object("left")
    button.add(get_icon("left"))
    button.connect("pressed", visca.move_left)
    button.connect("released", visca.stop_move)

    button = builder.get_object("leftup")
    button.add(get_icon("leftup"))
    button.connect("pressed", visca.move_leftup)
    button.connect("released", visca.stop_move)

    button = builder.get_object("leftdown")
    button.add(get_icon("leftdown"))
    button.connect("pressed", visca.move_leftdown)
    button.connect("released", visca.stop_move)

    button = builder.get_object("right")
    button.add(get_icon("right"))
    button.connect("pressed", visca.move_right)
    button.connect("released", visca.stop_move)

    button = builder.get_object("rightup")
    button.add(get_icon("rightup"))
    button.connect("pressed", visca.move_rightup)
    button.connect("released", visca.stop_move)

    button = builder.get_object("rightdown")
    button.add(get_icon("rightdown"))
    button.connect("pressed", visca.move_rightdown)
    button.connect("released", visca.stop_move)

    button = builder.get_object("up")
    button.add(get_icon("up"))
    button.connect("pressed", visca.move_up)
    button.connect("released", visca.stop_move)

    button = builder.get_object("down")
    button.add(get_icon("down"))
    button.connect("pressed", visca.move_down)
    button.connect("released", visca.stop_move)

    button = builder.get_object("home")
    button.add(get_icon("home"))
    button.connect("clicked", visca.move_home)

    # zoom
    button = builder.get_object("zoomin")
    button.add(get_stock_icon("zoomin"))
    button.connect("pressed", visca.zoom_in)
    button.connect("released", visca.stop_zoom)

    button = builder.get_object("zoomout")
    button.add(get_stock_icon("zoomout"))
    button.connect("pressed", visca.zoom_out)
    button.connect("released", visca.stop_zoom)

    # presets
    button = builder.get_object("1")
    button.connect("clicked", visca.preset1)

    button = builder.get_object("2")
    button.connect("clicked", visca.preset2)

    button = builder.get_object("3")
    button.connect("clicked", visca.preset3)

    button = builder.get_object("4")
    button.connect("clicked", visca.preset4)

    button = builder.get_object("5")
    button.connect("clicked", visca.preset5)

    button = builder.get_object("6")
    button.connect("clicked", visca.preset6)

    # to set a new preset
    presetbutton = builder.get_object("preset")
    presetbutton.add(get_stock_icon("preset"))

    # fly-mode for camera-movement
    flybutton = builder.get_object("fly")
    flybutton.add(get_stock_icon("fly"))
    flybutton.connect("clicked", visca.fly_mode)

    # on-off button
    onoffbutton = builder.get_object("on-off")
    onoffbutton.connect("state-set", visca.turn_on_off)

    # reset all settings
    button = builder.get_object("reset")
    button.add(get_stock_icon("reset"))
    button.connect("clicked", visca.reset)

    # scales
    brightscale = builder.get_object("brightscale")
    brightlabel = get_label("bright")
    brightlabel.set_text(str(int(brightscale.get_value())))
    brightscale.connect("value-changed", visca.set_bright)

    movescale = builder.get_object("movescale")
    movelabel = get_label("move")
    movelabel.set_text(str(int(movescale.get_value())))
    movescale.connect("value-changed", visca.set_move)

    zoomscale = builder.get_object("zoomscale")
    zoomlabel = get_label("zoom")
    zoomlabel.set_text(str(int(zoomscale.get_value())))
    zoomscale.connect("value-changed", visca.set_zoom)

    # show/hide preferences
    prefbutton = builder.get_object("pref")
    prefbutton.connect("clicked", visca.show_pref)


# ONVIF USER INTERFACE
def init_onvif_ui(element):
    global recorder_ui, movescale, zoomscale, presetlist, presetdelbutton, flybutton, builder, prefbutton, newpreset, movelabel, zoomlabel, res

    onvif = onvif_interface()
    dispatcher.connect("recorder-starting", onvif.on_start_recording)
    dispatcher.connect("recorder-stopped", onvif.on_stop_recording)

    recorder_ui = context.get_mainwindow().nbox.get_nth_page(0).gui

    # load css file
    css = Gtk.CssProvider()
    css.load_from_path(get_ui_path("camctrl.css"))

    Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # load glade file
    builder = Gtk.Builder()
    builder.add_from_file(get_ui_path("camctrl-onvif.glade"))

    # calculate resolution for scaling
    window_size = context.get_mainwindow().get_size()
    res = window_size[0]/1920.0

    # scale images
    imgs = ["ctrl", "zoom", "dummy"]
    for i in imgs:
        get_stock_icon(i)
    # scale label
    labels = ["control", "settings"]
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
    button.connect("pressed", onvif.move_left)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("leftup")
    button.add(get_icon("leftup"))
    button.connect("pressed", onvif.move_leftup)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("leftdown")
    button.add(get_icon("leftdown"))
    button.connect("pressed", onvif.move_leftdown)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("right")
    button.add(get_icon("right"))
    button.connect("pressed", onvif.move_right)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("rightup")
    button.add(get_icon("rightup"))
    button.connect("pressed", onvif.move_rightup)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("rightdown")
    button.add(get_icon("rightdown"))
    button.connect("pressed", onvif.move_rightdown)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("up")
    button.add(get_icon("up"))
    button.connect("pressed", onvif.move_up)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("down")
    button.add(get_icon("down"))
    button.connect("pressed", onvif.move_down)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("home")
    button.add(get_icon("home"))
    button.connect("clicked", onvif.move_home)

    # zoom
    button = builder.get_object("zoomin")
    button.add(get_stock_icon("zoomin"))
    button.connect("pressed", onvif.zoom_in)
    button.connect("released", onvif.stop_move)

    button = builder.get_object("zoomout")
    button.add(get_stock_icon("zoomout"))
    button.connect("pressed", onvif.zoom_out)
    button.connect("released", onvif.stop_move)

    # presets
    presetlist = builder.get_object("preset_list")
    # add home position to list
    presetlist.insert(0, "home", "home")
    # fill the list with current presets
    for preset in cam.get_presets():
        presetlist.append(preset.Name, preset.Name)
    presetlist.connect("changed", onvif.change_preset)

    # to set a new preset
    newpreset = builder.get_object("newpreset")
    newpreset.connect("activate", onvif.save_preset)
    newpreset.connect("icon-press", onvif.save_preset_icon)


    # to delete a preset
    presetdelbutton = builder.get_object("presetdel")
    presetdelbutton.add(get_stock_icon("presetdel"))
    presetdelbutton.connect("clicked", onvif.empty_entry)

    # fly-mode for camera-movement
    flybutton = builder.get_object("fly")
    flybutton.add(get_stock_icon("fly"))
    flybutton.connect("clicked", onvif.fly_mode)

    # reset all settings
    button = builder.get_object("reset")
    button.add(get_stock_icon("reset"))
    button.connect("clicked", onvif.reset)

    # show/hide preferences
    prefbutton = builder.get_object("pref")
    prefbutton.add(get_stock_icon("settings"))
    prefbutton.connect("clicked", onvif.show_pref)

    movescale = builder.get_object("movescale")
    movelabel = get_label("move")
    movelabel.set_text("{0:.1f}".format(movescale.get_value()))
    movescale.connect("value-changed", onvif.set_move)

    zoomscale = builder.get_object("zoomscale")
    zoomlabel = get_label("zoom")
    zoomlabel.set_text("{0:.1f}".format(zoomscale.get_value()))
    zoomscale.connect("value-changed", onvif.set_zoom)

# visca function interface
class visca_interface():
    #  import galicaster.utils.pysca as pysca
    # movement functions
    def move_left(self, button):
        logger.debug("I move left")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=-int(movescale.get_value()))


    def move_leftup(self, button):
        logger.debug("I move leftup")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=-int(movescale.get_value()), tilt=int(movescale.get_value()))


    def move_leftdown(self, button):
        logger.debug("I move leftdown")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=-int(movescale.get_value()), tilt=-int(movescale.get_value()))


    def move_right(self, button):
        logger.debug("I move right")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=int(movescale.get_value()))


    def move_rightup(self, button):
        logger.debug("I move rightup")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=int(movescale.get_value()), tilt=int(movescale.get_value()))


    def move_rightdown(self, button):
        logger.debug("I move rightdown")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=int(movescale.get_value()), tilt=-int(movescale.get_value()))


    def move_up(self, button):
        logger.debug("I move up")
        pysca.pan_tilt(DEFAULT_DEVICE, tilt=int(movescale.get_value()))


    def move_down(self, button):
        logger.debug("I move down")
        pysca.pan_tilt(DEFAULT_DEVICE, tilt=-int(movescale.get_value()))


    def stop_move(self, button):
        logger.debug("I make a break")
        pysca.pan_tilt(DEFAULT_DEVICE, pan=0, tilt=0)


    def move_home(self, button):
        logger.debug("I move home")
        pysca.pan_tilt_home(DEFAULT_DEVICE)


    # zoom functions
    def zoom_in(self, button):
        logger.debug("zoom in")
        pysca.zoom(DEFAULT_DEVICE, pysca.ZOOM_ACTION_TELE, speed=int(zoomscale.get_value()))


    def zoom_out(self, button):
        logger.debug("zoom out")
        pysca.zoom(DEFAULT_DEVICE, pysca.ZOOM_ACTION_WIDE, speed=int(zoomscale.get_value()))


    def stop_zoom(self, button):
        logger.debug("stop zoom")
        pysca.zoom(DEFAULT_DEVICE, pysca.ZOOM_ACTION_STOP)


    # preset functions
    def preset1(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 0)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 0)


    def preset2(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 1)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 1)


    def preset3(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 2)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 2)


    def preset4(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 3)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 3)


    def preset5(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 4)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 4)


    def preset6(self, button):
        if presetbutton.get_active():
            pysca.set_memory(DEFAULT_DEVICE, 5)
            presetbutton.set_active(False)
        else:
            pysca.recall_memory(DEFAULT_DEVICE, 5)


    # brightness scale
    def set_bright(self, brightscale):
        brightlabel.set_text(str(int(brightscale.get_value())))
        pysca.set_ae_mode(DEFAULT_DEVICE, pysca.AUTO_EXPOSURE_BRIGHT_MODE)
        pysca.set_brightness(DEFAULT_DEVICE, int(brightscale.get_value()) + DEFAULT_BRIGHTNESS)

    def set_zoom(self, zoomscale):
        zoomlabel.set_text(str(int(zoomscale.get_value())))

    def set_move(self, movescale):
        movelabel.set_text(str(int(movescale.get_value())))

    # reset all settings
    def reset(self, button):
        # reset brightness
        pysca.set_ae_mode(DEFAULT_DEVICE, pysca.AUTO_EXPOSURE_BRIGHT_MODE)
        pysca.set_brightness(DEFAULT_DEVICE, DEFAULT_BRIGHTNESS)
        brightscale.set_value(DEFAULT_BRIGHTSCALE)
        movescale.set_value(DEFAULT_MOVESCALE)
        zoomscale.set_value(DEFAULT_ZOOMSCALE)
        # reset zoom
        pysca.set_zoom(DEFAULT_DEVICE, DEFAULT_ZOOM)
        # reset location
        pysca.pan_tilt_home(DEFAULT_DEVICE)


    # turns the camera on/off
    def turn_on_off(self, onoffbutton, state):
        if onoffbutton.get_active():
            pysca.set_power_on(DEFAULT_DEVICE, True)
        else:
            pysca.set_power_on(DEFAULT_DEVICE, False)


    # hides/shows the advanced preferences
    def show_pref(self, prefbutton):
        scalebox1 = builder.get_object("scales1")
        scalebox2 = builder.get_object("scales2")
        scalebox3 = builder.get_object("scales3")
        # settings button activated
        if scalebox1.get_property("visible"):
            print ("hide advanced settings")
            scalebox1.hide()
            scalebox2.hide()
            scalebox3.hide()
        # settings button deactivated
        else:
            print ("show advanced settings")
            scalebox1.show()
            scalebox2.show()
            scalebox3.show()


    # flymode activation connects clicked signal and disconnects
    # pressed/released to keep the movement
    def fly_mode(self, flybutton):
        # fly mode turned on
        if flybutton.get_active():
            logger.debug("fly mode turned on")
            button = builder.get_object("left")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_left)

            button = builder.get_object("leftup")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_leftup)

            button = builder.get_object("leftdown")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_leftdown)

            button = builder.get_object("right")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_right)

            button = builder.get_object("rightup")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_rightup)

            button = builder.get_object("rightdown")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_rightdown)

            button = builder.get_object("up")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_up)

            button = builder.get_object("down")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_down)

            button = builder.get_object("home")
            GObject.signal_handlers_destroy(button)
            button.set_image(get_stock_icon("stop"))
            button.connect("clicked", self.stop_move)


        # fly mode turned off
        else:
            logger.debug("fly mode turned off")

            button = builder.get_object("left")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_left)
            button.connect("released", self.stop_move)

            button = builder.get_object("leftup")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_leftup)
            button.connect("released", self.stop_move)

            button = builder.get_object("leftdown")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_leftdown)
            button.connect("released", self.stop_move)

            button = builder.get_object("right")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_right)
            button.connect("released", self.stop_move)

            button = builder.get_object("rightup")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_rightup)
            button.connect("released", self.stop_move)

            button = builder.get_object("rightdown")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_rightdown)
            button.connect("released", self.stop_move)

            button = builder.get_object("up")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_up)
            button.connect("released", self.stop_move)

            button = builder.get_object("down")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_down)
            button.connect("released", self.stop_move)

            button = builder.get_object("home")
            GObject.signal_handlers_destroy(button)
            button.set_image(get_icon("home"))
            button.connect("clicked", self.move_home)


    def on_start_recording(self, elem):

        preset = config.get(RECORD_PRESET_KEY, DEFAULT_RECORD_PRESET_INT)
        mp = repo.get_next_mediapackage()

        if mp is not None:
            try:
                properties = mp.getOCCaptureAgentProperties()
                preset = int(properties['org.opencastproject.workflow.config.cameraPreset'])
            except Exception as e:
                logger.warn("Error loading the preset from the OC properties! Error:", e)

        try:
            pysca.set_power_on(DEFAULT_DEVICE, True, )
            onoffbutton.set_active(True)
            pysca.recall_memory(DEFAULT_DEVICE, (preset))

        except Exception as e:
            logger.warn("Error accessing the Visca device %u on recording start. The recording may be incorrect! Error: %s" % (DEFAULT_DEVICE, e))


    def on_stop_recording(self, elem, elem2):

        try:
            pysca.recall_memory(DEFAULT_DEVICE, config.get(IDLE_PRESET_KEY, DEFAULT_IDLE_PRESET_INT))
            pysca.set_power_on(DEFAULT_DEVICE, False)
            onoffbutton.set_active(False)

        except Exception as e:
            logger.warn("Error accessing the Visca device %u on recording end. The recording may be incorrect! Error: %s" % (DEFAULT_DEVICE, e))


# onvif function interface
class onvif_interface():

    # movement functions
    def move_left(self, button):
        logger.debug("I move left")
        cam.go_left(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_leftup(self, button):
        logger.debug("I move leftup")
        cam.go_left_up(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_leftdown(self, button):
        logger.debug("I move leftdown")
        cam.go_left_down(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_right(self, button):
        logger.debug("I move right")
        cam.go_right(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_rightup(self, button):
        logger.debug("I move rightup")
        cam.go_right_up(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_rightdown(self, button):
        logger.debug("I move rightdown")
        cam.go_right_down(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_up(self, button):
        logger.debug("I move up")
        cam.go_up(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def move_down(self, button):
        logger.debug("I move down")
        cam.go_down(float("{0:.1f}".format(movescale.get_value())))
        presetlist.set_active(-1)


    def stop_move(self, button):
        logger.debug("I make a break")
        cam.stop()


    def move_home(self, button):
        logger.debug("I move home")
        presetlist.set_active_id("home")


    # zoom functions
    def zoom_in(self, button):
        logger.debug("zoom in")
        cam.zoom_in(float("{0:.1f}".format(zoomscale.get_value())))
        presetlist.set_active(-1)


    def zoom_out(self, button):
        logger.debug("zoom out")
        cam.zoom_out(float("{0:.1f}".format(zoomscale.get_value())))
        presetlist.set_active(-1)


    # preset functions
    def change_preset(self, presetlist):
        if len(newpreset.get_text()) > 0:
            if newpreset.get_text() == "home":
                logger.debug("New Home set to current position.")
            else:
                logger.debug("New Preset saved: %s", newpreset.get_text())
        elif presetlist.get_active_text() == "home":
            logger.debug("Going Home")
            cam.go_home()
        else:
            if presetdelbutton.get_active() and not presetlist.get_active_text() is None:
                cam.remove_preset(cam.identify_preset(presetlist.get_active_text()))
                presetdelbutton.set_active(False)
                presetlist.remove(presetlist.get_active())
                
            else:
                if not presetlist.get_active_text() is None:
                    logger.debug("Going to: " + presetlist.get_active_text())
                    cam.go_to_preset(cam.identify_preset(presetlist.get_active_text()))


    def empty_entry(self, presetdelbutton):
        if presetdelbutton.get_active():
            presetlist.set_active(-1)
            presetlist.remove(0)
        elif not presetdelbutton.get_active():
            presetlist.insert(0, "home", "home")


    def save_preset_icon(self, newpreset, pos, event):
        if newpreset.get_text() == "home":
            cam.set_home()
            presetlist.set_active_id(newpreset.get_text())
            newpreset.set_text("")
        else:
            cam.set_preset(newpreset.get_text())
            presetlist.append(newpreset.get_text(), newpreset.get_text())
            presetlist.set_active_id(newpreset.get_text())
            newpreset.set_text("")


    def save_preset(self, newpreset):
        if newpreset.get_text() == "home":
            cam.set_home()
            presetlist.set_active_id(newpreset.get_text())
            newpreset.set_text("")
        else:
            cam.set_preset(newpreset.get_text())
            presetlist.append(newpreset.get_text(), newpreset.get_text())
            presetlist.set_active_id(newpreset.get_text())
            newpreset.set_text("")


    # reset all settings
    def reset(self, button):
        movescale.set_value(DEFAULT_MOVESCALE_0NVIF)
        zoomscale.set_value(DEFAULT_ZOOMSCALE_ONVIF)
        # reset location
        cam.go_home()


    def set_zoom(self, zoomscale):
        zoomlabel.set_text("{0:.1f}".format(zoomscale.get_value()))

    def set_move(self, movescale):
        movelabel.set_text("{0:.1f}".format(movescale.get_value()))

    # hides/shows the advanced preferences
    def show_pref(self, prefbutton):
        scalebox1 = builder.get_object("scales1")
        scalebox2 = builder.get_object("scales2")
        # settings button activated
        if scalebox1.get_property("visible"):
            logger.debug("hide advanced settings")
            scalebox1.hide()
            scalebox2.hide()
        # settings button deactivated
        else:
            logger.debug("show advanced settings")
            scalebox1.show()
            scalebox2.show()


    # flymode activation connects clicked signal and disconnects
    # pressed/released to keep the movement
    def fly_mode(self, flybutton):
        # fly mode turned on
        if flybutton.get_active():
            logger.debug("fly mode turned on")
            button = builder.get_object("left")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_left)

            button = builder.get_object("leftup")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_leftup)

            button = builder.get_object("leftdown")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_leftdown)

            button = builder.get_object("right")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_right)

            button = builder.get_object("rightup")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_rightup)

            button = builder.get_object("rightdown")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_rightdown)

            button = builder.get_object("up")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_up)

            button = builder.get_object("down")
            GObject.signal_handlers_destroy(button)
            button.connect("clicked", self.move_down)

            button = builder.get_object("home")
            GObject.signal_handlers_destroy(button)
            button.set_image(get_stock_icon("stop"))
            button.connect("clicked", self.stop_move)

        # fly mode turned off
        else:
            logger.debug("fly mode turned off")

            button = builder.get_object("left")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_left)
            button.connect("released", self.stop_move)

            button = builder.get_object("leftup")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_leftup)
            button.connect("released", self.stop_move)

            button = builder.get_object("leftdown")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_leftdown)
            button.connect("released", self.stop_move)

            button = builder.get_object("right")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_right)
            button.connect("released", self.stop_move)

            button = builder.get_object("rightup")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_rightup)
            button.connect("released", self.stop_move)

            button = builder.get_object("rightdown")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_rightdown)
            button.connect("released", self.stop_move)

            button = builder.get_object("up")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_up)
            button.connect("released", self.stop_move)

            button = builder.get_object("down")
            GObject.signal_handlers_destroy(button)
            button.connect("pressed", self.move_down)
            button.connect("released", self.stop_move)

            button = builder.get_object("home")
            GObject.signal_handlers_destroy(button)
            button.set_image(get_icon("home"))
            button.connect("clicked", self.move_home)


    def on_start_recording(self, elem):

        preset = config.get(RECORD_PRESET_KEY, DEFAULT_RECORD_PRESET)
        mp = repo.get_next_mediapackage()

        if mp is not None:
                try:
                    properties = mp.getOCCaptureAgentProperties()
                    preset = properties['org.opencastproject.workflow.config.cameraPreset']
                except Exception as e:
                    logger.warn("Error loading a preset from the OC properties! Error:", e)

        try:
            presetlist.set_active_id(preset)
            #  cam.goToPreset(cam.identifyPreset(preset))

        except Exception as e:
            logger.warn("Error accessing the IP camera on recording start. The recording may be incorrect! Error:", e)


    def on_stop_recording(self, elem, elem2):

        try:
            presetlist.set_active_id(config.get(IDLE_PRESET_KEY, DEFAULT_IDLE_PRESET))
            #  cam.goToPreset(cam.identifyPreset(config.get(IDLE_PRESET_KEY, DEFAULT_IDLE_PRESET)))

        except Exception as e:
            logger.warn("Error accessing the IP camera on recording end. The recording may be incorrect! Error: ", e)


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

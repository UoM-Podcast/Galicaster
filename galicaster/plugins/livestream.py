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
import shlex
from subprocess import Popen
from multiprocessing.pool import ThreadPool


def init():
    GObject.threads_init()
    global recorder, dispatcher, logger, repo, conf

    dispatcher = context.get_dispatcher()
    repo = context.get_repository()
    logger = context.get_logger()
    conf = context.get_conf()

    dispatcher.connect("init", init_ls_ui)


def init_ls_ui(element):
    global recorder_ui, movescale, zoomscale, presetlist, presetdelbutton, flybutton, builder, prefbutton, newpreset, movelabel, zoomlabel, res


    recorder_ui = context.get_mainwindow().nbox.get_nth_page(0).gui

    # load css file
    # css = Gtk.CssProvider()
    # css.load_from_path(get_ui_path("livestream.css"))
    #
    # Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())
    # Gtk.StyleContext.add_provider_for_screen(
    #     Gdk.Screen.get_default(),
    #     css,
    #     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    # )

    # load glade file
    builder = Gtk.Builder()
    builder.add_from_file(get_ui_path("livestream.glade"))

    # calculate resolution for scaling
    window_size = context.get_mainwindow().get_size()
    res = window_size[0]/1920.0

    # scale images
    imgs = []
    for i in imgs:
        get_stock_icon(i)
    # scale label
    labels = ["settings"]
    for i in labels:
        get_label(i)


    # add new settings tab to the notebook
    notebook = recorder_ui.get_object("data_panel")
    mainbox = builder.get_object("mainbox")

    notebook.append_page(mainbox, get_label("notebook"))

    notebook.show_all()

    # show/hide preferences
    prefbutton = builder.get_object("pref")
    # prefbutton.add(get_stock_icon("settings"))
    prefbutton.connect("toggled", DoingThings().on_button_toggled)
    # prefbutton.set_active(True)


class DoingThings():
    def __init__(self):
        self.megas = None
        self.full_cmd = conf.get('livestream', 'livestream_ffmpeg')


    def on_button_toggled(self, button):

        if button.get_active():
            # Make an obvious notification in UI when livestreaming
            slamm = builder.get_object("box2")
            slamm.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(255, 0, 0, 1))
            sidenote = get_label("notebook")
            sidenote.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(255, 0, 0, 1))
            setts = builder.get_object("settings_label")
            setts.set_markup('<b>Livestream: ON AIR</b>')
            # setts.set_name('red_coloured')
            self.megas = self.output_1()
        else:
            # return UI to normal
            slamm = builder.get_object("box2")
            sidenote = get_label("notebook")
            slamm.override_background_color(Gtk.StateType.NORMAL)
            sidenote.override_background_color(Gtk.StateType.NORMAL)
            setts = builder.get_object("settings_label")
            setts.set_text('Livestream Stopped')
            # setts.set_name('black_coloured')
            self.megas.get().terminate()


    def livestream_exec(self):
        #subprocess.call(full_cmd, shell=True)
        p = Popen(shlex.split(self.full_cmd))
        return p

    def output_1(self):
        # thread = threading.Thread(target=livestream_exec)
        # thread.daemon = True
        # thread.start()
        print 'go'

        pool = ThreadPool(processes=1)

        async_result = pool.apply_async(self.livestream_exec)
        return async_result


def get_icon(imgname):
    size = res * 56
    pix = GdkPixbuf.Pixbuf.new_from_file_at_size(get_image_path("img/"+imgname+".svg"), size, size)
    img = Gtk.Image.new_from_pixbuf(pix)
    img.show()
    return img

def get_stock_icon(imgname):
    size = res * 100
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
       or labelname == "control" \
       or labelname == "livestream":
        size = res * 20
    elif labelname == "notebook":
        size = res * 20
        label.set_property("ypad",10)
        # label.set_property("xpad",5)
        # label.set_property("vexpand-set",True)
        # label.set_property("vexpand",True)
    elif labelname == "bright" or \
            labelname == "move" or \
            labelname == "zoom":
        size = res * 14
    label.set_use_markup(True)
    label.modify_font(Pango.FontDescription(str(size)))
    return label
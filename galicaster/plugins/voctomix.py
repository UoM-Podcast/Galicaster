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
import socket



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

    # load glade file
    builder = Gtk.Builder()
    builder.add_from_file(get_ui_path("voctomix.glade"))

    # calculate resolution for scaling
    window_size = context.get_mainwindow().get_size()
    res = window_size[0]/1920.0


    # add new settings tab to the notebook
    notebook = recorder_ui.get_object("data_panel")
    mainbox = builder.get_object("mainbox")

    notebook.append_page(mainbox, get_label("notebook"))

    notebook.show_all()

    # buttons for mix options
    sbsbtn = builder.get_object("sbs")
    sbsbtn.connect("clicked", SendMix().on_button_toggled, "set_composite_mode side_by_side_equal")

    fullscreenbtn = builder.get_object("full")
    fullscreenbtn.connect("clicked", SendMix().on_button_toggled, "set_composite_mode fullscreen")

    pipbtn = builder.get_object("pip")
    pipbtn.connect("clicked", SendMix().on_button_toggled, "set_composite_mode picture_in_picture")


    camonebtn = builder.get_object("cam1")
    camonebtn.connect("clicked", SendMix().on_button_toggled, "set_video_a cam1")

    camtwobtn = builder.get_object("cam2")
    camtwobtn.connect("clicked", SendMix().on_button_toggled, "set_video_a cam2")

    screenbtn = builder.get_object("grabber")
    screenbtn.connect("clicked", SendMix().on_button_toggled, "set_video_a grabber")

    pausebtn = builder.get_object("pause")
    pausebtn.connect("clicked", SendMix().on_button_toggled, "set_stream_blank pause")

    noavbtn = builder.get_object("noav")
    noavbtn.connect("clicked", SendMix().on_button_toggled, "set_stream_blank nostream")

    livebtn = builder.get_object("livestreamm")
    livebtn.connect("clicked", SendMix().on_button_toggled, "set_stream_live")



class Netcat:
    """ Python 'netcat like' module """
    def __init__(self, ip, port):
        self.buff = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, port))

    def read(self, length=1024):
        """ Read 1024 bytes off the socket """

        return self.socket.recv(length)

    def read_until(self, data):
        """ Read data into the buffer until we have data """

        while not data in self.buff:
            self.buff += self.socket.recv(1024)

        pos = self.buff.find(data)
        rval = self.buff[:pos + len(data)]
        self.buff = self.buff[pos + len(data):]

        return rval

    def write(self, data):
        self.socket.send(data)

    def close(self):
        self.socket.close()


class SendMix():
    def __init__(self):
        pass

    def on_button_toggled(self, button, mixcmd):
        nc = Netcat('127.0.0.1', 9999)
        nc.write(mixcmd + '\n')


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
    elif labelname == "bright" or \
            labelname == "move" or \
            labelname == "zoom":
        size = res * 14
    label.set_use_markup(True)
    label.modify_font(Pango.FontDescription(str(size)))
    return label
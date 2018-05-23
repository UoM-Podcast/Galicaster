# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/lockscreen
#
# Copyright (c) 2016, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.

"""
"""

from galicaster.classui import message
from galicaster.core import context

from galicaster.utils.i18n import _

from gi.repository import Gtk
from galicaster.core.core import PAGES

conf = None
logger = None
user_list = []
WORKFLOW_CONFIG = 'org.opencastproject.workflow.config'


def init():
    global conf, logger, user_list, ocservice
    dispatcher = context.get_dispatcher()
    logger = context.get_logger()
    conf = context.get_conf()
    ocservice = context.get_ocservice()
    dispatcher.connect('init', show_msg)
    dispatcher.connect('recorder-stopped', update_mediapackage_nfcuserlist)

def show_msg(element=None, signal=None):
    buttonDIS = show_buttons(PAGES['DIS'])
    buttonREC = show_buttons(PAGES['REC'])
    buttonMMA = show_buttons(PAGES['MMA'])

    text = {"title" : _("Locked")}

    show = []
    auth_method = conf.get_choice('lockscreen', 'authentication', ['basic', 'ldap'], 'basic')
    # quit_button = conf.get_boolean('lockscreen','enable_quit_button')

    # if auth_method == "ldap":
    # show = ["username_label","username_entry"]
    #     text = {"title" : _("Lock screen"),
    #         "main" : _("LDAP authentication")}
    # if quit_button:
    # show.append("quitbutton")

    if buttonDIS is not None:
        buttonDIS.connect("clicked",lock,text,show,None)
    if buttonREC is not None:
        buttonREC.connect("clicked",lock,text,show,None)
    if buttonMMA is not None:
        buttonMMA.connect("clicked",lock,text,show,None)

    lock(None,text,show,None)

def lock(element,text,show, last_users):
    message.PopUp(message.NFC_LOCKSCREEN, text,
                            context.get_mainwindow(),
                            None, response_action=on_unlock, close_on_response=False,show=show,close_parent=True, close_before_response_action = False, last_users=last_users)
    logger.info("Galicaster locked")

def show_buttons(ui):
    # this makes the button in the mainwindow ui
    try:
        builder = context.get_mainwindow().nbox.get_nth_page(ui).gui
    except Exception as error:
        logger.error("Exception (Does the view exists?): "+error)
        return None

    box = builder.get_object("box2")
    button = Gtk.Button()
    hbox = Gtk.Box()
    button.add(hbox)
    label = Gtk.Label("Lockscreen")
    label.set_padding(10,10)
    icon = Gtk.Image().new_from_icon_name("gtk-dialog-authentication",3)
    hbox.pack_start(label,True,True,0)
    hbox.pack_start(icon,True,True,0)
    box.pack_start(button,True,True,0)
    box.reorder_child(button,0)
    box.set_spacing(5)
    box.show_all()
    return button



def on_unlock(*args, **kwargs):
    global conf, logger

    builder = kwargs.get('builder', None)
    popup = kwargs.get('popup', None)

    lentry = builder.get_object("unlockpass")
    # userentry = builder.get_object("username_entry")

    auth_method = conf.get_choice('lockscreen', 'authentication', ['basic', 'ldap'], 'basic')

    if len(message.user_list) > 0:
        # make sure empty strings arent valid
        if message.user_list[-1] is not '':
            logger.info("Galicaster unlocked")
            # id_concat = str(lentry.get_text())
            # ids_size = 12
            # spot_ids = [id_concat[i:i+ids_size] for i in range(0, len(id_concat), ids_size)]
            # for i in spot_ids:
            #     user_list.append(i)
            # print user_list
            popup.dialog_destroy()
        else:
            lmessage = builder.get_object("lockmessage")
            lmessage.set_text("Error: User ID not recognised. Please try again")
            lmessage.show()
    elif len(message.user_list) < 1:
        lmessage = builder.get_object("lockmessage")
        lmessage.set_text("Error: User ID not recognised. Please try again")
        lmessage.show()
    else:
        lmessage = builder.get_object("lockmessage")
        lmessage.set_text("Wrong username/password")
        lmessage.show()

def update_mediapackage_nfcuserlist(sender, mpURI):
    # post-process the ID
    for i in message.user_list:
        removed_nine = i.lstrip('9')[:-1]
        user_list.append(removed_nine.lstrip('0'))
    user_list_fmt = list(set(user_list))
    user_list_str = ','.join(map(str, user_list_fmt))
    # add IDs to the org.opencast.properties file
    recorder = context.get_recorder()
    mp = recorder.current_mediapackage
    occap = mp.getOCCaptureAgentProperties()
    occap[WORKFLOW_CONFIG + '.spotIDs'] = user_list_str
    occap_list = []
    for prpt, value in occap.items():
        occap_list.append(prpt + '=' + str(value))

    prpts_str = '\n'.join(occap_list)

    mp.addAttachmentAsString(prpts_str, 'org.opencastproject.capture.agent.properties',
                             'org.opencastproject.capture.agent.properties')

    # add ids to workflow acls
    current_wf_acl = ocservice.get_wfparams('aclRoles')
    ocservice.change_wfparams('aclRoles', user_list_str + ',' + current_wf_acl)
    ocservice.change_wfparams('spotIDs', user_list_str)
    # re lock once stopped
    text = {"title": _("Locked")}

    show = []
    last_user_list = []
    for i in message.user_list:
        last_user_list.append(i)
    lock(None, text, show, last_user_list)

    # print user_list
    # important list is deleted
    del message.user_list[:]
    del user_list[:]
    # print user_list


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

import os
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
    dispatcher.connect('operation-started', addacl_on_ingest)

def show_msg(element=None, signal=None):
    buttonDIS = show_buttons(PAGES['DIS'])
    buttonREC = show_buttons(PAGES['REC'])
    buttonMMA = show_buttons(PAGES['MMA'])

    text = {"title" : _("Locked")}

    show = []
    auth_method = conf.get_choice('lockscreen', 'authentication', ['basic', 'ldap'], 'basic')


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
    # Remove buttons not needed for user interactions
    recorder_ui = context.get_mainwindow().nbox.get_nth_page(0).gui
    recorder_ui.get_object("previousbutton").hide()
    recorder_ui.get_object("editbutton").hide()
    recorder_ui.get_object("swapbutton").hide()
    recorder_ui.get_object("label_channels").hide()

    return button



def on_unlock(*args, **kwargs):
    global conf, logger

    builder = kwargs.get('builder', None)
    popup = kwargs.get('popup', None)

    lentry = builder.get_object("unlockpass")

    auth_method = conf.get_choice('lockscreen', 'authentication', ['basic', 'ldap'], 'basic')

    if len(message.user_list) > 0:
        # make sure empty strings arent valid
        if message.user_list[-1] is not '':
            logger.info("Galicaster unlocked")

            popup.dialog_destroy()
        else:
            lmessage = builder.get_object("lockmessage")
            lmessage.set_text("Error: User ID not recognised. Please try again")
            lmessage.show()
            lentry.grab_focus()
    elif len(message.user_list) < 1:
        lmessage = builder.get_object("lockmessage")
        lmessage.set_text("No ID Found: Tap card to the reader")
        lmessage.show()
        lentry.grab_focus()
    else:
        lmessage = builder.get_object("lockmessage")
        lmessage.set_text("Wrong username/password")
        lmessage.show()
        lentry.grab_focus()

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


    # add ids to workflow acls
    workflowparams = conf.get_dict('ingest', 'workflow-parameters')
    current_wf_acl = workflowparams['aclRoles']
    #combine acl roles from config and scanned spotids and turn into a list
    if user_list_str == '':
        full_wf_acl = (current_wf_acl).split(',')
    else:
        full_wf_acl = (user_list_str + ',' + current_wf_acl).split(',')
    # remove duplicates
    full_wf_acl = list(set(full_wf_acl))
    full_spotid = list(set(full_wf_acl))
    # turn back into a sting
    full_wf_acl = ','.join(map(str, full_wf_acl))
    # ocservice.change_wfparams('aclRoles', full_wf_acl)
    #remove the role_admin from the list so just to have the ids
    full_spotid.remove('ROLE_ADMIN')
    full_spotid = ','.join(map(str, full_spotid))

    spotid_attachment = 'spotid.attach'
    mpUri = mp.getURI()
    dest = os.path.join(mpUri, spotid_attachment)
    if not os.path.isfile(dest):
        spotidfile = open(dest, "w")
        spotidfile.write(full_spotid)
        spotidfile.close()

    # re lock once stopped
    text = {"title": _("Locked")}
    show = []
    last_user_list = []
    for i in message.user_list:
        last_user_list.append(i)
    lock(None, text, show, last_user_list)

    # important list is deleted
    del message.user_list[:]
    del user_list[:]


def addacl_on_ingest(signal, action, mp):
    ocservice = context.get_ocservice()
    current_wf_acl = ocservice.get_wfparams('aclRoles')
    # read spotids from file
    spotid_attachment = 'spotid.attach'
    mpUri = mp.getURI()
    dest = os.path.join(mpUri, spotid_attachment)
    spotidfile = open(dest, "r")
    try:
        get_spotids = spotidfile.readline()
    except Exception as e:
        print e
        return
    spotidfile.close()
    new_wf_acl = 'ROLE_ADMIN' + ',' + get_spotids
    ocservice.change_wfparams('spotIDs', get_spotids)
    ocservice.change_wfparams('aclRoles', new_wf_acl)
    repo = context.get_repository()
    repo.update(mp)


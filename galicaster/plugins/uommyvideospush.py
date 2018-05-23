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
import pymssql

from galicaster.core import context

from galicaster.utils.i18n import _

from gi.repository import Gtk

conf = None
logger = None
user_list = []
WORKFLOW_CONFIG = 'org.opencastproject.workflow.config'


def init():
    global conf, logger, user_list
    dispatcher = context.get_dispatcher()
    logger = context.get_logger()
    conf = context.get_conf()
    dispatcher.connect('operation-stopped', update_mediapackage_nfcuserlist)


def update_mediapackage_nfcuserlist(sender, op_code, mp, op_ok, exc):
    server = conf.get('uommyvideospush', 'server')
    port = conf.get('uommyvideospush', 'port')
    user = conf.get('uommyvideospush', 'user')
    password = conf.get('uommyvideospush', 'password')
    table = conf.get('uommyvideospush', 'table')
    ounit = conf.get('uommyvideospush', 'ounit')

    conn = pymssql.connect(server, user, password, table, port=port)
    cursor = conn.cursor()

    occap = mp.getOCCaptureAgentProperties()
    idsis = occap[WORKFLOW_CONFIG + '.spotIDs']

    query = """
    INSERT INTO VideoDetails (mediapackageId, title, spotId, typeId, workflowInstanceId, orgNumber, date, hidden, visibleTypeId, titleHash, workflowTypeId)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (mp.getIdentifier(), mp.getTitle(), idsis, 6, exc, ounit, mp.getDate(), 0, 2, None, None))

    conn.commit()

    conn.close()

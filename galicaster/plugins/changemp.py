# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/plugins/changemp
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.
"""
Changemp plugin. This plugin can override the workflow of a matterhorn
scheduled mediapackage with a specified workflow. An existing series
from matterhorn can be attached to manual recordings and an
episode title can be added if specified. note - workflows can already
be specified for manual recordings in /etc/galicaster/conf.ini
"""

from galicaster.core import context


logger = context.get_logger()
conf = context.get_conf()
mhclient = context.get_mhclient()

workflow_new = conf.get('changemp', 'workflow')
workflow_parameters = conf.get('changemp', 'workflow-parameters')
remove_parameters = conf.get('changemp', 'remove-parameters')
series = conf.get('changemp', 'set-series')
title = conf.get('changemp', 'set-title')
oc_definition = 'org.opencastproject.workflow.definition'
workflow_config = 'org.opencastproject.workflow.config'


def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('start-operation', changemp)
    except ValueError:
        pass


def changemp(self, action, mp):
    occap = mp.getOCCaptureAgentProperties()
    start = mp.getStartDateAsString()
    if series and mp.manual:
        series_title = mhclient.get_single_series(series)['title'][0]['value']
        series_dict = {'identifier': series, 'title': series_title}
        mp.setSeries(series_dict)
        logger.info('series {0} - {1} was set for manual recording {2}'.format(series, series_title, mp.getIdentifier()))
    if title and mp.manual:
        mp.setTitle(title + ' ' + mp.getStartDateAsString())
    try:
        workflow = occap[oc_definition]
    except:
        workflow = None
    if workflow != workflow_new and workflow is not None:
        occap[oc_definition] = workflow_new
        if workflow_parameters:
            #add each of the workflow parameters to the dict
            wp_split = workflow_parameters.split(';')
            for wp in wp_split:
                occap[workflow_config + '.' + wp.split(':')[0]] = wp.split(':')[1]
        if remove_parameters:
            #remove parameters from the dict
            rp_split = remove_parameters.split(';')
            for rp in rp_split:
                occap.pop(workflow_config + '.' + rp.split(':')[0], None)
        #build the list of parameters and write to file
        occap_list = ['#Capture Agent specific data', '#' + start]
        for prpt, value in occap.items():
            occap_list.append(prpt + '=' + value)
        properties_str = '\n'.join(occap_list)
        mp.addAttachmentAsString(properties_str, 'org.opencastproject.capture.agent.properties', True, 'org.opencastproject.capture.agent.properties')
        logger.info('mediapackage id:{0} changed workflow from {1} to {2}'.format(mp.getIdentifier(), workflow, workflow_new))


# The MIT License (MIT)
#
# Copyright (c) 2014 The University of Manchester
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from galicaster.core import context
from galicaster.opencast.series import get_default_series
from galicaster.opencast.series import getSeriesbyId

"""
plugin changemp
used to set custom parameters to mediapackages at ingest time for manual mediapackages
the use case being for hard-set locations that have user interactivity with the Galicaster
UI but no control over the metadata
used to set the title, series, source and workflow parameters
"""


logger = context.get_logger()
conf = context.get_conf()
default_series = get_default_series()

workflow_new = conf.get('changemp', 'workflow')
workflow_parameters = conf.get('changemp', 'workflow-parameters')
remove_parameters = conf.get('changemp', 'remove-parameters')
series = conf.get('changemp', 'set-series')
source = conf.get('changemp', 'set-source')
title = conf.get('changemp', 'set-title')
oc_definition = 'org.opencastproject.workflow.definition'
workflow_config = 'org.opencastproject.workflow.config'
oc_event_series= 'event.series'


def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('operation-started', changemp)
    except ValueError:
        pass


def changemp(self, action, mp):
    if mp.manual:
        occap = mp.getOCCaptureAgentProperties()
        start = mp.getStartDateAsString()
        repo = context.get_repository()
        if series:
            # series_title = mhclient.get_single_series(series)['title'][0]['value']
            # series_title = getSeriesbyId(get_default_series())['list']['title']
            # series_dict = {'identifier': series, 'title': series_title}
            # get the full series from OC
            series_dict = getSeriesbyId(get_default_series())['list']
            mp.setSeries(series_dict)
            logger.info('series {0} was set for manual recording {1}'.format(series, mp.getIdentifier()))
        if source:
            source_dict = {'source': source}
            mp.setSource(source_dict)
        if title:
            mp.setTitle(title + ' ' + mp.getStartDateAsString())
        try:
            workflow = occap[oc_definition]
        except:
            workflow = None
        if series:
            occap[oc_event_series] = get_default_series()
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
            mp.addAttachmentAsString(properties_str, 'org.opencastproject.capture.agent.properties', 'org.opencastproject.capture.agent.properties')
            logger.info('mediapackage id:{0} changed workflow from {1} to {2}'.format(mp.getIdentifier(), workflow, workflow_new))
        # Update the mp with the changes
        repo.update(mp)

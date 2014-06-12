__author__ = 'andrew'

from galicaster.core import context
import datetime

logger = context.get_logger()
conf = context.get_conf()

workflow_new = conf.get('workflowoverride', 'workflow')
workflow_parameters = conf.get('workflowoverride', 'workflow-parameters')
remove_parameters = conf.get('workflowoverride', 'remove-parameters')
OC_definition = 'org.opencastproject.workflow.definition'
workflow_config = 'org.opencastproject.workflow.config'

def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('start-operation', workflowoverride)
    except ValueError:
        pass

def workflowoverride(self, action, mp):
    # dictionary of opencast properties
    occap = mp.getOCCaptureAgentProperties()
    try:
        workflow = occap[OC_definition]
    except:
        workflow = None
    if workflow != workflow_new and workflow is not None:
        OCproperties = mp.getURI() + '/org.opencastproject.capture.agent.properties'
        occap[OC_definition] = workflow_new
        if workflow_parameters is not None:
            #add each of the workflow parameters to the dict
            wp_split = workflow_parameters.split(';')
            for wp in wp_split:
                occap[workflow_config + '.' + wp.split(':')[0]] = wp.split(':')[1]
        if remove_parameters is not None:
            #remove parameters
            rp_split = remove_parameters.split(';')
            for rp in rp_split:
                occap.pop(workflow_config + '.' + rp.split(':')[0], None)
        with open(OCproperties, 'w') as mp_OC_file:
            #write dict to file
            now = datetime.datetime.utcnow()
            mp_OC_file.write('#Capture Agent specific data\n')
            mp_OC_file.write('#' + now.strftime('%d-%m-%Y %H:%M') + '\n')
            for d in occap.items():
                mp_OC_file.write(d[0] + '=' + d[1] + '\n')
        mp_OC_file.close()

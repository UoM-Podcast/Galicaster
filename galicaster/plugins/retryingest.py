# retryingest galicaster plugin
#
# Copyright 2014 University of Sussex
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time

from galicaster.core import context
from galicaster.mediapackage import mediapackage

logger = context.get_logger()
conf = context.get_conf()
occlient = context.get_occlient()
repo = context.get_repository()

check_ingested = conf.get_boolean('retryingest', 'check_ingested')
check_published = conf.get_boolean('retryingest', 'check_published')
check_after = conf.get_int('retryingest', 'check_after') or 300
check_nightly = conf.get_boolean('retryingest', 'nightly')
check_state = conf.get_boolean('retryingest', 'check_state')
last_checked = time.time()


def init():
    logger.debug('check_ingested set to {}'.format(check_ingested))
    logger.debug('check_published set to {}'.format(check_published))
    logger.debug('check_after set to {}'.format(str(check_after)))
    logger.debug('check_nightly set to {}'.format(check_nightly))
    logger.debug('check_state set to {}'.format(check_state))

    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('timer-short', reingest)
    except ValueError:
        pass


def has_ingested(mp_id, mp):
    # check if the mediapackage has been ingested
    search_result = occlient.search_by_mp_workflow_id(mp_id)['workflow']['operations']['operation'][2]
    if search_result['id'] == 'ingest' and search_result['state'] == 'SUCCEEDED':
        logger.debug('mediapackage %s has already been ingested', mp_id)
        # mediapackage with workflow id has actually been ingested successfully at some point
        mp.setOpStatus('ingest', mediapackage.OP_DONE)
        repo.update(mp)
        return True
    logger.debug('mediapackage %s has not been ingested', mp_id)
    return False


def has_succeeded(mp_id, mp):
    #check if the mediapackage has the workflow.status file
    try:
        mp_workflow_state = mp.getAttachment('workflow.status')
    except:
        mp_workflow_state = None
    if mp_workflow_state:
        logger.debug('mp {} already marked as failed workflow - Ignoring'.format(mp_id))
    else:
        if mp.getOpStatus('ingest') == mediapackage.OP_DONE or mp.getOpStatus('ingest') == mediapackage.OP_NIGHTLY:
            # check for the current mediapackage workflow state
            try:
                workflow_state = occlient.search_by_mp_workflow_id(mp_id)['workflow']['state']
            except IOError:
                return True
            logger.debug('mp {0}. mhorn state: {1}'.format(mp_id, workflow_state))
            if workflow_state == 'FAILED':
                logger.info('mp {} : Workflow Failed'.format(mp_id))
                mp.addAttachmentAsString('#' + workflow_state, 'workflow.status', False, 'workflow.status')
                mp.setOpStatus('ingest', mediapackage.OP_FAILED)
                repo.update(mp)
                return False
    return True


def is_published(mp_id, mp):
    # check if the mediapackage is published to the search index
    search_result = occlient.search_by_mp_id(mp_id)
    if int(search_result['total']):
        logger.debug('mediapackage {} is already published'.format(mp_id))
        # mediapackage has actually been ingested successfully at some point
        # as it is published in opencast so set the state to "done"
        mp.setOpStatus('ingest', mediapackage.OP_DONE)
        repo.update(mp)
        return True
    logger.debug('mediapackage {} is not published'.format(mp_id))
    return False


def reingest(sender=None):
    global last_checked

    # only run if it is time
    if (last_checked + check_after) >= time.time():
        return

    worker = context.get_worker()
    for mp_id, mp in repo.iteritems():
        logger.debug('reingest checking: {0} status: {1}'.format(mp_id, mediapackage.op_status[mp.getOpStatus('ingest')]))
        # only finished recordings
        if mp.status not in [mediapackage.SCHEDULED, mediapackage.RECORDING]:

            if check_ingested or check_state:
                # make sure the mediapackage is not manual before checking the workflow state
                # OC will not know the GC mpid given
                if mp.getOCCaptureAgentProperties() != {}:
                    try:
                        if check_state and not has_succeeded(mp_id, mp):
                            logger.info('Set mediapackage to Failed: Failed Workflow: %s', mp_id)
                    except RuntimeError as e:
                        logger.debug('matterhorn ' + str(e))
                    logger.debug('reingest checking: %s status: %s', mp_id, mediapackage.op_status[mp.getOpStatus('ingest')])
                if mp.getOpStatus('ingest') == mediapackage.OP_FAILED or mp.getOpStatus('ingest') == mediapackage.OP_IDLE:
                    # check mediapackage status on matterhorn if needed
                    if (check_ingested and not has_ingested(mp_id, mp)) or not check_ingested:
                        if check_nightly:
                            logger.info('scheduled nightly reingest of failed mediapackage: {}'.format(mp_id))
                            mp.setOpStatus("ingest", mediapackage.OP_NIGHTLY)
                            repo.update(mp)
                        else:
                            logger.info('Starting reingest of failed mediapackage: {}'.format(mp_id))
                            worker.enqueue_job_by_name('ingest', mp)

            if check_published:
                if mp.getOpStatus('ingest') == mediapackage.OP_FAILED:
                    # check mediapackage status on opencast if needed
                    if (check_published and not is_published(mp_id, mp)) or not check_published:
                        # postpone the ingest until the 'nightly' ingest time else ingest immediately
                        if check_nightly:
                            logger.info('scheduled nightly reingest of failed mediapackage: {}'.format(mp_id))
                            mp.setOpStatus("ingest", mediapackage.OP_NIGHTLY)
                            repo.update(mp)
                        else:
                            logger.info('Starting reingest of failed mediapackage: {}'.format(mp_id))
                            worker.enqueue_job_by_name('ingest',mp)
    last_checked = time.time()

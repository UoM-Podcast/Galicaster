# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
# galicaster/utils/mhhttpclient
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

import re
import json
import urllib
import socket
import random
#IDEA use cStringIO to improve performance
from StringIO import StringIO
import pycurl
from collections import OrderedDict

INIT_ENDPOINT = '/info/me.json'
ME_ENDPOINT = '/info/me.json'
SETRECORDINGSTATE_ENDPOINT = '/capture-admin/recordings/{id}'
SETSTATE_ENDPOINT = '/capture-admin/agents/{hostname}'
SETCONF_ENDPOINT = '/capture-admin/agents/{hostname}/configuration'
INGEST_ENDPOINT = '/ingest/addZippedMediaPackage'
ICAL_ENDPOINT = '/recordings/calendars?agentid={hostname}'
SERIES_ENDPOINT = '/series/series.json?count={count}'
SERVICE_REGISTRY_ENDPOINT = '/services/available.json?serviceType={serviceType}'
WORKFLOW_ENDPOINT = '/workflow/instance/{id}.json'

WORKFLOW_SERVICE_TYPE = 'org.opencastproject.workflow'
INGEST_SERVICE_TYPE = 'org.opencastproject.ingest'


class MHHTTPClient(object):

    def __init__(self, server, user, password, hostname='galicaster', address=None, multiple_ingest=False,
                 random_ingest=False, ingest_to_admin=True, workflow='full', workflow_parameters={'trimHold':'true'},
                 polling_short=10, polling_long=60, logger=None):
        """
        Arguments:

        server -- Matterhorn server URL.
        user -- Account used to operate the Matterhorn REST endpoints service.
        password -- Password for the account  used to operate the Matterhorn REST endpoints service.
        hostname -- Capture agent hostname, optional galicaster by default.
        address -- Capture agent IP address, optional socket.gethostbyname(socket.gethostname()) by default.
        workflow -- Name of the workflow used to ingest the recordings., optional `full` by default.
        workflow_parameters -- string (k1=v1;k2=v2) or dict of parameters used to ingest, opcional {'trimHold':'true'} by default.
        """
        self.server = server
        self.user = user
        self.password = password
        self.hostname = hostname
        self.address = address or socket.gethostbyname(socket.gethostname())
        self.multiple_ingest = multiple_ingest
        self.random_ingest = random_ingest
        self.ingest_to_admin = ingest_to_admin
        self.workflow = workflow
        self.logger = logger
        if isinstance(workflow_parameters, basestring):
            self.workflow_parameters = dict(item.split(":") for item in workflow_parameters.split(";"))
        else:
            self.workflow_parameters = workflow_parameters
        self.workflow_server = None
        self.polling_schedule = polling_long
        self.polling_state = polling_short
        # FIXME should be long? https://github.com/teltek/Galicaster/issues/114
        self.polling_caps = polling_short
        self.polling_config = polling_short
        self.response = {'Status-Code': '', 'Content-Type': '', 'ETag': ''}
        self.ical_etag = -1


    def __call(self, method, endpoint, params={}, postfield={}, urlencode=True, server=None, timeout=True, headers={}):

        theServer = server or self.server
        c = pycurl.Curl()
        b = StringIO()
        c.setopt(pycurl.URL, theServer + endpoint.format(**params))
        # FOLLOWLOCATION, True used for ssl redirect
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.setopt(pycurl.CONNECTTIMEOUT, 2)
        if timeout:
            c.setopt(pycurl.TIMEOUT, 10)
        c.setopt(pycurl.NOSIGNAL, 1)
        c.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
        c.setopt(pycurl.USERPWD, self.user + ':' + self.password)
        sendheaders = ['X-Requested-Auth: Digest']
        if headers:
            for h, v in headers.iteritems():
                  sendheaders.append('{}: {}'.format(h, v))
            # implies we might be interested in passing the response headers
            c.setopt(pycurl.HEADERFUNCTION, self.scanforetag)
        c.setopt(pycurl.HTTPHEADER, sendheaders)
        c.setopt(pycurl.USERAGENT, 'Galicaster')
        if (method == 'POST'):
            if urlencode:
                c.setopt(pycurl.POST, 1)
                c.setopt(pycurl.POSTFIELDS, urllib.urlencode(postfield))
            else:
                c.setopt(pycurl.HTTPPOST, postfield)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        #c.setopt(pycurl.VERBOSE, True)
        try:
            c.perform()
        except:
            raise RuntimeError, 'connect timed out!'
        status_code = c.getinfo(pycurl.HTTP_CODE)
        self.response['Status-Code'] = status_code
        self.response['Content-Type'] = c.getinfo(pycurl.CONTENT_TYPE)
        c.close()
        # client will accept 200, 302 and 304 HTTP codes
        if not (status_code == 200 or status_code == 302 or status_code == 304):
            if self.logger:
                self.logger.error('call error in %s, status code {%r}',
                                  theServer + endpoint.format(**params), status_code)
            raise IOError, 'Error in Matterhorn client'
        return b.getvalue()


    def scanforetag(self, buffer):
        if buffer.startswith('ETag:'):
            etag = buffer[5:]
            self.response['ETag'] = etag.strip()


    def whoami(self):
        return json.loads(self.__call('GET', ME_ENDPOINT))

    def welcome(self):
        return self.__call('GET', INIT_ENDPOINT)


    def ical(self):
        icalendar = self.__call('GET', ICAL_ENDPOINT, {'hostname': self.hostname}, headers={'If-None-Match': self.ical_etag})

        if self.response['Status-Code'] == 304:
            if self.logger:
                self.logger.info("iCal Not modified")
            return None

        self.ical_etag = self.response['ETag']
        if self.logger:
                self.logger.info("iCal modified")
        return icalendar


    def setstate(self, state):
        """
        Los posibles estados son: shutting_down, capturing, uploading, unknown, idle
        """
        pass
        #return self.__call('POST', SETSTATE_ENDPOINT, {'hostname': self.hostname},
        #{'address': self.address, 'state': state})


    def setrecordingstate(self, recording_id, state):
        """
        Los posibles estados son: unknown, capturing, capture_finished, capture_error, manifest, 
        manifest_error, manifest_finished, compressing, compressing_error, uploading, upload_finished, upload_error
        """
        pass
        #return self.__call('POST', SETRECORDINGSTATE_ENDPOINT, {'id': recording_id}, {'state': state})


    def setconfiguration(self, capture_devices):
        client_conf_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                             <!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
                             <properties version="1.0">{0}</properties>"""
        client_conf_xml_body = '<entry key="{key}">{value}</entry>'

        client_conf = {
            'service.pid': 'galicaster',
            'capture.confidence.debug': 'false',
            'capture.confidence.enable': 'false',
            'capture.config.remote.polling.interval': self.polling_config,
            'capture.agent.name': self.hostname,
            'capture.agent.state.remote.polling.interval': self.polling_state,
            'capture.agent.capabilities.remote.polling.interval': self.polling_caps,
            'capture.agent.state.remote.endpoint.url': self.server + '/capture-admin/agents',
            'capture.recording.shutdown.timeout': '60',
            'capture.recording.state.remote.endpoint.url': self.server + '/capture-admin/recordings',
            'capture.schedule.event.drop': 'false',
            'capture.schedule.remote.polling.interval': int(self.polling_schedule) / 60,
            'capture.schedule.event.buffertime': '1',
            'capture.schedule.remote.endpoint.url': self.server + '/recordings/calendars',
            'capture.schedule.cache.url': '/opt/matterhorn/storage/cache/schedule.ics',
            'capture.ingest.retry.interval': '300',
            'capture.ingest.retry.limit': '5',
            'capture.ingest.pause.time': '3600',
            'capture.cleaner.interval': '3600',
            'capture.cleaner.maxarchivaldays': '30',
            'capture.cleaner.mindiskspace': '536870912',
            'capture.error.messagebody': '&quot;Capture agent was not running, and was just started.&quot;',
            'capture.error.subject': '&quot;%hostname capture agent started at %date&quot;',
            'org.opencastproject.server.url': 'http://172.20.209.88:8080',
            'org.opencastproject.capture.core.url': self.server,
            'capture.max.length': '28800'
        }

        client_conf.update(capture_devices)

        xml = ""
        for k, v in client_conf.iteritems():
            xml = xml + client_conf_xml_body.format(key=k, value=v)
        client_conf = client_conf_xml.format(xml)

        return self.__call('POST', SETCONF_ENDPOINT, {'hostname': self.hostname}, {'configuration': client_conf})


    def _prepare_ingest(self, mp_file, workflow=None, workflow_instance=None, workflow_parameters=None):
        "refactor of ingest to unit test"
        postdict = OrderedDict()
        postdict[u'workflowDefinitionId'] = workflow or self.workflow
        if workflow_instance:
            postdict['workflowInstanceId'] = str(workflow_instance)
        if isinstance(workflow_parameters, basestring):
            postdict.update(dict(item.split(":") for item in workflow_parameters.split(";")))
        elif isinstance(workflow_parameters, dict) and workflow_parameters:
            postdict.update(workflow_parameters)
        else:
            postdict.update(self.workflow_parameters)
        postdict[u'track'] = (pycurl.FORM_FILE, mp_file)
        return postdict


    def _get_endpoints(self, service_type):
        if self.logger:
            self.logger.debug('Looking up Matterhorn endpoint for %s', service_type)
        services = self.__call('GET', SERVICE_REGISTRY_ENDPOINT, {'serviceType': service_type}, {},
                               True, None, True)
        services = json.loads(services)
        return services['services']['service']

    def _get_workflow_server(self):
        if not self.workflow_server:
            service = self._get_endpoints(WORKFLOW_SERVICE_TYPE)
            self.workflow_server = str(service['host'])
        return self.workflow_server

    def search_by_mp_id(self, mp_id):
        """ Returns result of workflow search for mediapackage workflow id """
        workflow_server = self._get_workflow_server()
        result = self.__call('GET', WORKFLOW_ENDPOINT, {'id': mp_id}, {}, True, workflow_server, True)
        search_result = json.loads(result)
        return search_result


    def verify_ingest_server(self, server):
        """ if we have multiple ingest servers the get_ingest_server should never 
        return the admin node to ingest to, This is verified by the IP address so 
        we can meke sure that it doesn't come up through a DNS alias, If all ingest 
        services are offline the ingest will still fall back to the server provided 
        to Galicaster as then None will be returned by get_ingest_server  """

        p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'
        m = re.search(p, server['host'])
        host = m.group('host')
        m = re.search(p, self.server)
        adminHost = m.group('host')
        if (not server['online']):
            return False
        if (server['maintenance']):
            return False
        adminIP = socket.gethostbyname(adminHost);
        hostIP = socket.gethostbyname(host)
        if (adminIP != hostIP):
            return True
        return False


    def get_ingest_server(self):
        """ get the ingest server information from the admin node: 
        if there are more than one ingest servers the first from the list will be used
        as they are returned in order of their load, if there is only one returned this 
        will be the admin node, so we can use the information we already have """
        servers = self.__call('GET', SERVICE_REGISTRY_ENDPOINT, {'serviceType': 'org.opencastproject.ingest'}, {},
                              True, None, True)
        servers_avail = json.loads(servers)
        all_servers = servers_avail['services']['service']
        if type(all_servers) is list:
            if self.random_ingest:
                    attempt = 0
                    while attempt < 10:
                        result = random.choice(all_servers)
                        if self.verify_ingest_server(result):
                            return str(result['host'])
                        attempt += 1
            for serv in all_servers:
                if self.verify_ingest_server(serv):
                    return str(serv['host'])  # Returns least loaded served
        if self.verify_ingest_server(all_servers):
            return str(all_servers['host'])  # There's only one server
        if not self.ingest_to_admin:
            raise ValueError("Ingest nodes are currently unavailable")
        return None  # it will use the admin server

    def ingest(self, mp_file, workflow=None, workflow_instance=None, workflow_parameters=None):
        postdict = self._prepare_ingest(mp_file, workflow, workflow_instance, workflow_parameters)
        server = self.server if not self.multiple_ingest else self.get_ingest_server()
        self.logger.info('Ingesting to Server {0}'.format(server))
        return self.__call('POST', INGEST_ENDPOINT, {}, postdict.items(), False, server, False)


    def getseries(self):
        """ Get all series upto 100"""
        # TODO No limit, to get all
        return self.__call('GET', SERIES_ENDPOINT, {'count': 100})

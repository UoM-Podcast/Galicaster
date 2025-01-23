# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/opencast/series
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California, 94105, USA.

from os import path
from galicaster.core import context
from galicaster.mediapackage.mediapackage import Catalog
import json


NAMESP = 'http://purl.org/dc/terms/'


def parse_json_series(json_series):
    series = {}
    for term in json_series[NAMESP].iterkeys():
        try:
            series[term] = json_series[NAMESP][term][0]['value']
        except (KeyError, IndexError):
            # Ignore non-existant items
            # TODO Log the exception
            pass

    return (series['identifier'], series )


def transform(a):
    return a.strip()


def get_default_series():
    return context.get_conf().get('series', 'default')


def filterSeriesbyId(list_series, seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    for element in list_series:
        if seriesid and seriesid in element[1]["identifier"].encode('utf8'):
            try:
                match = {"id": seriesid, "name": element[1]["title"], "list": element[1]}
                return match
            except Exception:
                return None


def getSeriesbyId(seriesid):
    """
    Generate a list with the series value name, shortname and id
    """
    ocservice = context.get_ocservice()
    json_series = json.loads(ocservice.client.getseries_byid(seriesid))
    id, series = parse_json_series(json_series)
    try:
        match = {"id": seriesid, "name": series['title'], "list": series}
        return match
    except Exception:
        return None


def serialize_series(series_list, series_path):
    in_json = json.dumps(series_list)
    if path.isfile(series_path):
        with open(series_path, 'w') as f:
            f.write(in_json)
            f.close()

def deserialize_series(series_path):
    in_json = json.loads(series_path)
    return in_json


def setSeriebyId(mp, seriesname):
    """
    Put the serie by the id in the mediapackage
    """
    setSerie(mp, getSeriesbyId(seriesname))

def setSerie(mp, series_list):
    """
    Put the serie received in the mediapackage
    """
    if series_list:
        mp.setSeries(series_list['list'])
        if not mp.getCatalogs("dublincore/series") and mp.getURI():
            new_series = Catalog(path.join(mp.getURI(),"series.xml"),mimetype="text/xml",flavor="dublincore/series")
            mp.add(new_series)
    else:
        mp.setSeries(None)
        catalog= mp.getCatalogs("dublincore/series")
        if catalog:
            mp.remove(catalog[0])

__author__ = 'andrew wilson'

import time
from galicaster.core import context
from galicaster.mediapackage import mediapackage
import collections

logger = context.get_logger()
conf = context.get_conf()
mhclient = context.get_mhclient()
repo = context.get_repository()

check_after = conf.get_int('checkdupes', 'check_after') or 2 #300
last_checked = time.time()

logger.debug('check_after set to %i', check_after)


def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('galicaster-notify-timer-short', checkdupes)
    except ValueError:
        pass

def checkdupes(sender=None):
    global last_checked

    # only run if it is time
    if (last_checked + check_after) >= time.time():
        return

    worker = context.get_worker()
    ham = {}
    for mp_id, mp in repo.iteritems():
        ham[mp_id] = str(mp.getDate())
    print ham
    for x in get_repeated_values(ham):
        print x

def get_repeated_values(sessions):
    known = set()
    already_repeated = set()
    for lst in sessions.itervalues():
        session_set = set(tuple(x) for x in lst)
        repeated = (known & session_set) - already_repeated
        already_repeated |= repeated
        known |= session_set
        for val in repeated:
            yield val


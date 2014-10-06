__author__ = 'andrew wilson'

from galicaster.core import context
import collections

logger = context.get_logger()
conf = context.get_conf()
mhclient = context.get_mhclient()
repo = context.get_repository()

check_exists = conf.get_boolean('checkdupes', 'check_exists') or True


def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('after-process-ical', checkdupes)
    except ValueError:
        pass


def instance_exists(mp):
    try:
        return mhclient.search_by_mp_id(mp)
    except IOError:
        return False


def checkdupes(sender=None):
    mp_dates = {}
    for mp_id, mp in repo.iteritems():
        mp_dates[mp_id] = str(mp.getDate())
    value_occurrences = collections.Counter(mp_dates.values())
    for ti, count in value_occurrences.items():
        if count > 1:
            logger.info('mediapackages with identical start times found')
            dupe_time = ti
            for i, t in mp_dates.items():
                if t == dupe_time:
                    if check_exists and instance_exists(i) is False:
                        logger.info('workflow {} not found in matterhorn deleting mp {}'.format(i, repo.get(i).getURI()))
                        repo.delete(repo.get(i))
                    elif check_exists is False:
                        # FIXME working on the assumption that the repo will be updated with correct mps
                        logger.info('deleting all mps with same start times {}'.format(i, repo.get(i).getURI()))
                        repo.delete(repo.get(i))



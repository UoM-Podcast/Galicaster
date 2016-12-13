# need to make a backup folder in /mnt with user:group ownership by the user
# in /etc/fstab add this line //server/share_dir /mnt/yourbackup cifs noauto,user,user=shareuser,password=sharepassword,uid=currentuser,gid=currentuser 0 0

import os

from galicaster.core import context
from galicaster.mediapackage import mediapackage

logger = context.get_logger()
worker = context.get_worker()
conf = context.get_conf()

CA_NAME = conf.get('ingest', 'hostname')
MOUNT_POINT = conf.get('backuprepo', 'mount_point')
NAS_PATH = conf.get('backuprepo', 'nas_path')


def init():
    try:
        dispatcher = context.get_dispatcher()
        dispatcher.connect('galicaster-notify-nightly', backuprepo)

    except ValueError:
        pass


def backuprepo(sender=None):
    repo = context.get_repository()
    backup_uris = []
    for mp_id, mp in repo.iteritems():
        if not (mp.status == mediapackage.SCHEDULED or mp.status == mediapackage.RECORDING or
                        mp.getOpStatus('ingest') == mediapackage.OP_DELAYED):
            mpUri = mp.getURI()
            backup_uris.append(mpUri)
    # mount from fstab
    try:
        os.system('mount {}'.format(MOUNT_POINT))
    except Exception:
        logger.debug('could not mount share')
    if os.path.exists(NAS_PATH):
        if not os.path.exists(NAS_PATH + CA_NAME):
            try:
                os.makedirs(NAS_PATH + CA_NAME)
            except Exception:
                logger.debug('failed to make backup dir for capture agent')
                return
    else:
        return
    if not backup_uris:
        return
    for mps in backup_uris:
        try:
            os.system('rsync -zavr --update ' + mps + ' ' + NAS_PATH + CA_NAME + '/')
        except Exception:
            pass
            logger.debug('failed to backup {0} to shared area'.format(mps))
    os.system('umount {}'.format(MOUNT_POINT))

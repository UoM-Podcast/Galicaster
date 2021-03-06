"""
mount a shared network attached storage and backup the current mediapackage repository at night
notes:
depends on rsync
to use a NFS share: `sudo apt-get install nfs-common`
need to make a mount directory with user:group ownership by the galicaster user
in /etc/fstab add:
windows CIFS: //server/share_dir    /mnt/yourbackup     cifs    noauto,user,user=shareuser,password=sharepassword,uid=currentuser,gid=currentuser   0   0
NFS:  192.168.0.1:share/Repository       /mnt/backup-repo  nfs     defaults,users        0       0
"""

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
        dispatcher.connect('timer-nightly', backuprepo)

    except ValueError:
        pass


def backuprepo(sender=None):
    repo = context.get_repository()
    backup_uris = []
    for mp_id, mp in repo.iteritems():
        if not (mp.status == mediapackage.SCHEDULED or mp.status == mediapackage.RECORDING or
                        mp.getOpStatus('ingest') == mediapackage.OP_NIGHTLY):
            mpUri = mp.getURI()
            backup_uris.append(mpUri)
    # mount from fstab
    try:
        os.system('mount {}'.format(MOUNT_POINT))
    except Exception:
        logger.debug('could not mount share')

    if not backup_uris:
        return
    for mps in backup_uris:
        try:
            os.system('rsync -zavr --update ' + mps + ' ' + MOUNT_POINT + NAS_PATH)
        except Exception:
            pass
            logger.debug('failed to backup {0} to shared area'.format(mps))
    os.system('umount {}'.format(MOUNT_POINT))

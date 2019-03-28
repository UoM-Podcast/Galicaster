
from galicaster.core import context
from os import path, utime, remove

pause_state_file = path.join(context.get_repository().get_rectemp_path(), "paused")

def init():
    dispatcher = context.get_dispatcher()
    dispatcher.connect('recorder-paused', write_pause_state)

def write_pause_state(signal, state):
  if state:
      if path.exists(pause_state_file):
          utime(pause_state_file, None)
      else:
          open(pause_state_file, 'a').close()
  else:
      remove(pause_state_file)

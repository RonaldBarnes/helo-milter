
"""
	Test if identity given by `helo` command matches DNS lookup on connecting IP
"""

## from Milter import Milter
import Milter

## Need to chown and chmod the socket:
import os, stat
from pwd import getpwnam


## Threading helps responsiveness and allows signal catching:
import threading

## Catch exit signals and remove socket before exiting:
import signal

from time import sleep


import logging
logging.basicConfig(
	level=logging.DEBUG,
	## level=logging.INFO,
	## level=logging.WARNING,
	## level=logging.ERROR,
	## level=logging.CRITICAL,
	format='%(asctime)s [%(levelname)s] %(message)s',
		datefmt="%Y-%m-%d %H:%M:%S"
	)




SOCKET_FILE = "/var/spool/postfix/milter.sock"

## Actions to take while analyzing helo:
ACTIONS = {
	"match_true": {
		"add_header": True,
		},
	"match_false": {
		"add_header": True,
		"quarantine": False,
		"reject": True,
		},
	}

HELO_MILTER_HEADER = "X-HELO-MILTER-MATCHED-DNS"



def chown_socket():
	"""
		Change owner of socket to postfix.
	"""

	logging.debug( f"chown_socket()")

	try:
		uid = getpwnam("postfix").pw_uid
		gid = getpwnam("postfix").pw_gid

		os.chown(SOCKET_FILE, uid, gid)

		logging.debug( f"Changed owner: {SOCKET_FILE} to postfix {uid}:{gid}")

	except KeyError as e:
		logging.critical( f"ERROR getting user postfix: {e}")
		cleanup_socket()
		os._exit(255)
	except Exception as e:
		logging.critical( f"ERROR getting user postfix: {type(e).__name__}")
		cleanup_socket()
		os._exit(255)

	file_perms()



def file_perms():
	logging.debug( f"file_perms()")

	try:
		os.chmod(SOCKET_FILE, stat.S_IRUSR | stat.S_IWUSR)
		file_mode = os.stat(SOCKET_FILE).st_mode

		perms = [
			"s" if stat.S_ISSOCK( os.stat(SOCKET_FILE).st_mode) else "?",
			"r" if file_mode & stat.S_IRUSR else "-",
			"w" if file_mode & stat.S_IWUSR else "-",
			"x" if file_mode & stat.S_IXUSR else "-",
			"r" if file_mode & stat.S_IRGRP else "-",
			"w" if file_mode & stat.S_IWGRP else "-",
			"x" if file_mode & stat.S_IXGRP else "-",
			"r" if file_mode & stat.S_IROTH else "-",
			"w" if file_mode & stat.S_IWOTH else "-",
			"x" if file_mode & stat.S_IXOTH else "-",
			]

		logging.info( f"{''.join(perms)} postfix {SOCKET_FILE}")

	except FileNotFoundError:
		logging.critical( f"ERROR: {SOCKET_FILE} not found")
		os._exit(255)

	except Exception as e:
		logging.critical( f"ERROR setting perms on {SOCKET_FILE}: {e}")
		cleanup_socket()
		os._exit(255)






class HeloCheckMilter(Milter.Base):
  def __init__(self):
    ## logging.debug( f"class HeloCheckMilter __init__()")
    super().__init__()

  def connect(self, hostname, family, host_addr_port):
    logging.debug(
      f"connect() hostname:{hostname} "
      ## f"family:{family} "
      f"{host_addr_port[0]}:{host_addr_port[1]}"
      )
    self.connect_from = hostname
    return Milter.CONTINUE


  ##############################
  def hello(self, hostname):
    logging.debug( f"hello() hostname: {hostname}")

    ## Store this - addheader() MAY be in eom() ONLY
    self.helo_from = hostname

    if hostname == self.connect_from:
      logging.debug( f"hello() helo matches: ({hostname} == {self.connect_from})")
    else:
      logging.warning( f"hello() helo MISMATCH: ({hostname} ≠ {self.connect_from})")
      if ACTIONS["match_false"]["reject"]:
        return Milter.REJECT

    return Milter.CONTINUE



  def envfrom(self, f, *str):
    return Milter.CONTINUE

  def envrcpt(self, to, *str):
    return Milter.CONTINUE

  def header(self, field, value):
    logging.debug( f"header() {field}:{value}")
    return Milter.CONTINUE

  def eoh(self):
    logging.debug( f"eoh() End Of Headers")
    return Milter.CONTINUE


  ##############################
  def eom(self):
    logging.debug( f"eom() End Of Message")

    if self.helo_from == self.connect_from:
      if ACTIONS["match_true"]["add_header"]:
        self.addheader(HELO_MILTER_HEADER, "True")
      return Milter.CONTINUE

    ## Mismatched helo & DNS:
    if ACTIONS["match_false"]["add_header"]:
      self.addheader(HELO_MILTER_HEADER, "False")

    if ACTIONS["match_false"]["quarantine"]:
      self.quarantine("Unmatched helo and DNS connect string")

    ## REJECT would have been issued during hello():
    return Milter.CONTINUE



  def abort(self):
    logging.debug( f"abort() Abnormal connection termination")
    return Milter.CONTINUE

  def close(self):
    logging.debug( f"close() Connection closed")
    return Milter.CONTINUE



def cleanup_socket():
  try:
    os.remove(SOCKET_FILE)
    logging.info( f"Removed socket file {SOCKET_FILE}")
  except FileNotFoundError:
    logging.error( f"File not found: {SOCKET_FILE}")
  except PermissionError:
    logging.error( f"Permission denied to remove {SOCKET_FILE}")
  except OSError as e:
    logging.critical( f"ERROR removing socket file {SOCKET_FILE}: {e}")
  except Exception as e:
    logging.critical( f"ERROR removing socket file {SOCKET_FILE}: {e}")




def signal_handler(sig_num, frame):
  sig_name =                                            \
    "SIGHUP / Hangup"     if sig_num ==  1        else  \
    "SIGINT / CTRL+C"     if sig_num ==  2        else  \
    "SIGQUIT / Quit"      if sig_num ==  3        else  \
    "SIGILL / Illegal"    if sig_num ==  4        else  \
    "SIGTRAP / Trap"      if sig_num ==  5        else  \
    "SIGABRT / Abort"     if sig_num ==  6        else  \
    "SIGTERM / Terminate" if sig_num == 15        else  \
    "SIGPWR / Power"      if sig_num == 30        else  \
    "Unknown signal"

  logging.warning( f"Caught signal {sig_name} ({sig_num})")

  cleanup_socket()
  os._exit(sig_num)




def run_milter():
	logging.info( f"run_milter() Starting...")

	try:
		Milter.factory = HeloCheckMilter
		Milter.runmilter("HeloCheckMilter", SOCKET_FILE, 10)
	except Exception as e:
		logging.critical( f"ERROR: cannot run milter: {e}")
		os._exit(255)




def main():
	logging.debug("main()")

	## Hangup (with systemd RestartForceExitStatus (?) = 1, can restart on HUP:
	signal.signal(signal.SIGHUP, signal_handler)
	## Catch CTRL+C signal:
	signal.signal(signal.SIGINT, signal_handler)
	## Catch SIGQUIT:
	signal.signal(signal.SIGQUIT, signal_handler)
	## ILLegal op:
	signal.signal(signal.SIGILL, signal_handler)
	## SIGTRAP (need this?)
	signal.signal(signal.SIGTRAP, signal_handler)
	## Abort:
	signal.signal(signal.SIGABRT, signal_handler)
	## Terminate
	signal.signal(signal.SIGTERM, signal_handler)
	##
	## signal.signal(signal.SIGCONT, signal_handler)
	## ERROR on this SIGSTOP: OSError: [Errno 22] Invalid argument
	## CANNOT be caught, STOPS (pauses) the systemd service!
	## Resume systemd service via SIGCONT
	## signal.signal(signal.SIGSTOP, signal_handler)
	signal.signal(signal.SIGPWR, signal_handler)


	## Sanity check on actions:
	if ACTIONS["match_false"]["quarantine"] and ACTIONS["match_false"]["reject"]:
		logging.critical("Cannot reject AND quarantine; must choose one")
		cleanup_socket()
		os._exit(99)


	milter_thread = threading.Thread(target=run_milter)
	milter_thread.start()

	sleep(1)
	chown_socket()

	milter_thread.join()


if __name__ == "__main__":
	main()


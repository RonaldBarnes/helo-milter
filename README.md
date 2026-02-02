# Helo Milter

Checks for `helo` statement matching connecting IP's DNS lookup hostname

## Operations Supported:

* on match:
   * add header (optional)
* on non-match:
  * add header (optional)
  * reject (optional)
  * quarantine (send to `postfix` hold queue (optional)
    

## Installation

1. `apt install libmilter-dev`
2. `pip install pymilter`
3. Edit `helo-milter.service`:
   * Change `Environment=Path=` to point to your venv/bin (if using venv), else remove it
   * Change `ExecStart=` to point to location of your `helo-milter.py`
4. Edit `helo-milter.py`:
   * Modify `ACTIONS` dict to select preferred actions (default is add headers):
  '## Actions to take while analyzing helo:
  ```
  ACTIONS = {
    "match_true": {
      "add_header": True,
      },
    "match_false": {
      "add_header": True,
      "quarantine": False,
      "reject": False,
      },
    }
```
  * Modify `logging.basicConfig` to select preferred log level (default is DEBUG):
```
logging.basicConfig(
  level=logging.DEBUG,
  ## level=logging.INFO,
  ## level=logging.WARNING,
  ## level=logging.ERROR,
  ## level=logging.CRITICAL,
  format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S"
  )
```


## Logging Notes

Logging default level is DEBUG.

Logging outputs the date & time. Note that viewing output in `journalctl` will 
show another date & time. Change the `logging.basicConfig` to remove `%(asctime)s`
**or** run `journalctl --output=cat | -o cat` for pure logs with no additional
information.


## Signal Handling

Signals are caught by `helo-milter.py`, the socket file is removed, then script exits
with caught signal's numeric value.

This allows supporting `systemctl reload helo-milter.service` for a clean restart
via `SIGHUP`.

Successful exit codes are shown in `helo-milter.service`:
`SuccessExitStatus=1 SIGHUP 2 SIGINT 30 SIGPWR`

The unit file's `RestartForceExitStatus=1` will force a restart on exit code 1 (`SIGHUP`).

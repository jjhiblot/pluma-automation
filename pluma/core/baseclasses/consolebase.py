import time
import pexpect
import pexpect.fdpexpect
import json
import os

from deprecated import deprecated
from datetime import datetime
from abc import ABCMeta, abstractmethod
from typing import Callable

from functools import wraps
from pluma.utils import datetime_to_timestamp
from pluma.core.dataclasses import SystemContext

from .hardwarebase import HardwareBase
from .logging import LogLevel


class ConsoleError(Exception):
    pass


class ConsoleCannotOpenError(ConsoleError):
    pass


class ConsoleLoginFailedError(ConsoleError):
    pass


class ConsoleExceptionKeywordReceivedError(ConsoleError):
    pass


class ConsoleInvalidJSONReceivedError(ConsoleError):
    pass


class ConsoleBase(HardwareBase, metaclass=ABCMeta):
    """ Implements the console functionality not specific to a given transport layer """

    def __init__(self, encoding: str = None, linesep: str = None,
                 raw_logfile: str = None, system: SystemContext = None):
        if not hasattr(self, '_pex'):
            raise AttributeError(
                "Variable '_pex' must be created by inheriting class")

        timestamp = datetime_to_timestamp(datetime.now())
        default_raw_logfile = os.path.join(
            '/tmp', 'pluma',
            f'{self.__class__.__name__}_raw_{timestamp}.log')

        self.encoding = encoding or 'ascii'
        self.linesep = linesep or '\n'
        self.raw_logfile = raw_logfile or default_raw_logfile
        self.system = system or SystemContext()

        self._buffer = ''
        self._last_received = ''
        self._raw_logfile_fd = None
        self._pex = None
        self._requires_login = True

    @property
    @abstractmethod
    def is_open(self):
        """ Check if the transport layer is ready to send and receive"""

    @abstractmethod
    def open(f):
        @wraps(f)
        def wrap(self):
            f(self)

            self._pex.linesep = self.encode(self.linesep)

            if self.raw_logfile:
                # Create raw_logfile dir if it does not already exist
                os.makedirs(os.path.dirname(self.raw_logfile), exist_ok=True)

                self._raw_logfile_fd = open(self.raw_logfile, 'ab')
                self._pex.logfile = self._raw_logfile_fd
        return wrap

    @abstractmethod
    def close(f: Callable[[object], None]):
        @wraps(f)
        def wrap(self):
            f(self)
            if self._raw_logfile_fd:
                self._raw_logfile_fd.close()
                self._raw_logfile_fd = None
        return wrap

    def raw_logfile_clear(self):
        open(self.raw_logfile, 'w').close()

    @deprecated(version='2.0', reason='Use "read_all" instead')
    def flush(self, clear_buf=False):
        if clear_buf:
            # Preserve behavior of returning nothing when clearing
            self.read_all(preserve_read_buffer=False)
        else:
            return self.read_all(preserve_read_buffer=True)

    def read_all(self, preserve_read_buffer: bool = False) -> str:
        '''Read all from the console, empty and return the read buffer'''

        if not self.is_open:
            self.open()
        try:
            while 1:
                self._buffer += self.decode(
                    self._pex.read_nonblocking(1, 0.01))
        except pexpect.exceptions.TIMEOUT:
            pass
        except pexpect.exceptions.EOF:
            pass

        buffer = self._buffer
        if not preserve_read_buffer:
            if self._buffer.strip():
                self.log(f'<<flushed>>{self._buffer}<</flushed>>',
                         force_echo=False, level=LogLevel.DEBUG)
            self._buffer = ''

        return buffer

    @property
    def _buffer_size(self):
        '''Size of the Read buffer for the console'''
        return len(self._buffer)

    @deprecated(version='2.0', reason='You should use "read_all" and "_buffer_size" instead')
    def _flush_get_size(self, clear_buf=False):
        self.flush(clear_buf)
        return self._buffer_size

    def decode(self, text):
        return text.decode(self.encoding, 'replace')

    def encode(self, text):
        return text.encode(self.encoding)

    @deprecated(version='2.0', reason='You should use "wait_for_bytes" or "wait_for_quiet" instead')
    def wait_for_data(
            self, timeout=None, sleep_time=None,
            match=None, start_bytes=None, verbose=None):

        timeout = timeout or 10.0
        sleep_time = sleep_time or 0.1
        verbose = verbose if verbose is not None else False

        if match:
            return self._wait_for_match(
                match=match,
                timeout=timeout,
                verbose=verbose
            )
        else:
            return self.wait_for_bytes(
                timeout=timeout,
                sleep_time=sleep_time,
                start_bytes=start_bytes,
                verbose=verbose
            )

    def wait_for_match(self, match, timeout=None, verbose=None):
        verbose = verbose or False
        timeout = timeout or self._pex.timeout

        if not self.is_open:
            self.open()

        if not isinstance(match, list):
            match = [match]

        if verbose:
            self.log(f'Waiting up to {timeout}s for patterns: {match}...')

        matched_str = None
        try:
            index = self._pex.expect(match, timeout)
            matched_str = match[index]
        except pexpect.EOF:
            pass
        except pexpect.TIMEOUT:
            pass

        if verbose:
            if matched_str:
                self.log(f'Matched {matched_str}')
            else:
                self.log('No match found before timeout or EOF')

        return matched_str

    @deprecated(version='2.0', reason='You should use "wait_for_match" instead')
    def _wait_for_match(self, match, timeout, verbose=None):
        verbose = verbose or False

        old_timeout = self._pex.timeout
        self._pex.timeout = timeout

        if not self.is_open:
            self.open()

        if not isinstance(match, list):
            match = [match]
        watches = [pexpect.TIMEOUT, pexpect.EOF] + match

        if verbose:
            self.log("Waiting up to {}s for patterns: {}...".format(
                timeout, match))

        matched = watches[self._pex.expect(watches)]
        self._pex.timeout = old_timeout

        # Pexpect child `.after` is the text matched after calling `.expect`
        if matched in match:
            return self.decode(self._pex.after)

        return False

    def wait_for_bytes(
            self, timeout=None, sleep_time=None,
            start_bytes=None, verbose=None):
        timeout = timeout or 10.0
        sleep_time = sleep_time or 0.1
        verbose = verbose or False

        if not self.is_open:
            self.open()

        self.read_all(preserve_read_buffer=True)
        if start_bytes is None:
            start_bytes = self._buffer_size

        elapsed = 0.0

        while(elapsed < timeout):
            self.read_all(preserve_read_buffer=True)
            current_bytes = self._buffer_size
            if verbose:
                self.log("Waiting for data: Waited[{:.1f}/{:.1f}s] Received[{:.0f}B]...".format(
                    elapsed, timeout, current_bytes-start_bytes))
            if current_bytes > start_bytes:
                return True

            time.sleep(sleep_time)
            elapsed += sleep_time

        return False

    def wait_for_quiet(self, quiet: float = None, sleep_time: float = None,
                       timeout: float = None) -> bool:
        if not self.is_open:
            self.open()
        quiet = quiet if quiet is not None else 0.5
        sleep_time = sleep_time if sleep_time is not None else 0.1
        timeout = timeout if timeout is not None else 10.0

        last_read_buffer_size = 0
        start = time.time()
        now = start
        quiet_start = start
        while(now - start < timeout):
            time.sleep(sleep_time)

            self.read_all(preserve_read_buffer=True)
            read_buffer_size = self._buffer_size

            # Check if more data was received
            now = time.time()
            if read_buffer_size == last_read_buffer_size:
                if now - quiet_start > quiet:
                    return True
            else:
                quiet_start = now

            last_read_buffer_size = read_buffer_size
            log_string = ("Waiting for quiet... Waited[{:.1f}/{:.1f}s] "
                          "Quiet[{:.1f}/{:.1f}s] Received[{:.0f}B]...")
            self.log(log_string.format(now - start, timeout, now - quiet_start,
                                       quiet, read_buffer_size), level=LogLevel.DEBUG)

        # Timeout
        return False

    @deprecated(version='2.0', reason='You should use "send_nonblocking" instead')
    def send(self,
             cmd=None,
             receive=False,
             match=None,
             excepts=None,
             send_newline=True,
             log_verbose=True,
             timeout=None,
             sleep_time=None,
             quiet_time=None,
             flush_buffer=True
             ):
        if not self.is_open:
            self.open()
        if not self.is_open:
            raise ConsoleCannotOpenError

        cmd = cmd or ''
        if log_verbose:
            self.log(f"Sending command:\n    {cmd}", force_log_file=None)

        if isinstance(cmd, str):
            cmd = self.encode(cmd)

        match = match or []
        excepts = excepts or []
        watches = []

        if not isinstance(match, list):
            match = [match]

        if not isinstance(excepts, list):
            excepts = [excepts]

        watches.extend(match)
        watches.extend(excepts)

        data_timeout = timeout if timeout is not None else 5
        quiet_timeout = timeout if timeout is not None else 3
        quiet_sleep = sleep_time if sleep_time is not None else 0.1
        quiet_time = quiet_time if quiet_time is not None else 0.3

        if flush_buffer:
            self.flush(True)

        received = None
        matched = None
        if not receive and not watches:
            if send_newline:
                self._pex.sendline(cmd)
            else:
                self._pex.send(cmd)

            self.log('<<sent>>{}<</sent>>'.format(cmd), force_echo=False)

            return (None, None)
        else:
            if send_newline:
                self._pex.sendline(cmd)
            else:
                self._pex.send(cmd)

            self.log('<<sent>>{}<</sent>>'.format(cmd), force_echo=False)

            if watches:
                matched = self.wait_for_data(
                    timeout=data_timeout,
                    match=watches,
                    verbose=log_verbose)
                received = self.decode(self._pex.before)
                new_received = received[len(self._last_received):]
                if matched:
                    self._last_received = ''
                    match_str = '<<matched expects={}>>{}<</matched>>'.format(
                        watches, matched)
                else:
                    self._last_received = received
                    match_str = '<<not_matched expects={}>>'.format(watches)
                self.log("<<received>>{}{}<</received>>".format(
                    new_received, match_str), force_echo=False)
                if matched in excepts:
                    self.error('Matched [{}] is in exceptions list {}'.format(
                        matched, excepts), exception=ConsoleExceptionKeywordReceivedError)
            else:
                self.wait_for_quiet(
                    quiet=quiet_time,
                    sleep_time=quiet_sleep,
                    timeout=quiet_timeout)
                received = self._buffer

        return (received, matched)

    def send_and_read(self, cmd: str, timeout: int = None,
                      sleep_time: int = None, quiet_time: int = None,
                      send_newline: bool = True, flush_before: bool = True) -> str:
        timeout = timeout if timeout is not None else 3
        sleep_time = sleep_time if sleep_time is not None else 0.1
        quiet_time = quiet_time if quiet_time is not None else 0.3

        self.send_nonblocking(cmd, send_newline=send_newline,
                              flush_before=flush_before)
        self.wait_for_quiet(quiet=quiet_time, sleep_time=sleep_time,
                            timeout=timeout)
        return self.read_all()

    def send_and_expect(self, cmd: str, match: list,
                        excepts: list = None, timeout: int = None,
                        send_newline: bool = True, flush_before: bool = True) -> (str, int):
        match = match or []
        excepts = excepts or []
        timeout = timeout if timeout is not None else 5

        if not isinstance(match, list):
            match = [match]
        if not isinstance(excepts, list):
            excepts = [excepts]

        watches = []
        watches.extend(match)
        watches.extend(excepts)

        self.send_nonblocking(cmd, send_newline=send_newline,
                              flush_before=flush_before)

        matched_regex = self.wait_for_match(timeout=timeout, match=watches)
        received = self.decode(self._pex.before)
        new_received = received[len(self._last_received):]

        if matched_regex:
            matched_text = self.decode(self._pex.after)
            received += matched_text
            self._last_received = ''
            debug_match_str = f'<<matched expects={watches}>>{matched_regex}<</matched>>'
        else:
            matched_text = None
            self._last_received = received
            debug_match_str = f'<<not_matched expects={watches}>>'

        self.log(f'<<received>>{new_received}{debug_match_str}<</received>>',
                 force_echo=False, level=LogLevel.DEBUG)

        if matched_regex in excepts:
            self.error(f'Matched [{matched_regex}] is in exceptions list {excepts}',
                       exception=ConsoleExceptionKeywordReceivedError)

        return (received, matched_text)

    def send_nonblocking(self, cmd: str,
                         send_newline: bool = True,
                         flush_before: bool = True):

        if not self.is_open:
            self.open()
        if not self.is_open:
            raise ConsoleCannotOpenError

        cmd = cmd or ''
        self.log(f'Sending command: \'{cmd}\'', force_log_file=None,
                 level=LogLevel.DEBUG)

        if flush_before:
            self.read_all()

        if send_newline:
            self._pex.sendline(cmd)
        else:
            self._pex.send(cmd)

        self.log(f'<<sent>>{cmd}<</sent>>',
                 force_echo=False, level=LogLevel.DEBUG)

    def check_alive(self, timeout=10.0):
        '''Return True if the console responds to <Enter>'''

        self.read_all(preserve_read_buffer=True)
        start_bytes = self._buffer_size
        self.send_nonblocking('', flush_before=False)
        alive = self.wait_for_bytes(timeout=timeout, start_bytes=start_bytes)

        if alive:
            self.log(f'Got response from: {self}')
        else:
            self.log(f'No response from: {self}')

        return alive

    def login(self, username, username_match,
              password=None, password_match=None, success_match=None):
        matches = [username_match]
        if password_match:
            matches.append(password_match)
        if success_match:
            matches.append(success_match)

        fail_message = f'Failed to log in with login="{username}" and password="{password}"'
        (output, matched) = self.send_and_expect('', match=matches)
        if not matched:
            self.error(f'{fail_message}:{os.linesep}  Output: {output}',
                       ConsoleLoginFailedError)

        if matched == username_match:
            self.log(f'Login prompt detected, sending username "{username}"')
            matches.remove(username_match)
            (output, matched) = self.send_and_expect(cmd=username,
                                                     match=matches)

        if password_match and matched == password_match:
            if not password:
                self.error(f'{fail_message}: No password set, but password prompt detected',
                           ConsoleLoginFailedError)

            self.log('Password prompt detected, sending password')
            matches.remove(password_match)
            (output, matched) = self.send_and_expect(cmd=password,
                                                     match=matches)

        if matched:
            self.log('Prompt detected')
        elif not matched and success_match:
            self.error(f'{fail_message}: Failed to detect the prompt "{success_match}".'
                       'The prompt can be set in the target configuration with'
                       f' the "system.prompt_regex" attribute:{os.linesep}  Output: {output}',
                       ConsoleLoginFailedError)

        self.log('Login successful')

    def get_json_data(self, cmd):
        ''' Execute a command @cmd on target which generates JSON data.
        Parse this data, and return a dict of it.'''

        self.wait_for_quiet(quiet=1, sleep_time=0.5)
        received, matched = self.send_and_expect(cmd, match='{((.|\n)*)\n}')

        if not matched:
            raise ConsoleInvalidJSONReceivedError(
                f'Received is not JSON: {received}')

        data = json.loads(matched)
        return data

    def support_file_copy(self):
        return False

    def copy_to_target(self, source, destination, timeout=30):
        raise ValueError(
            f'Console type {self} does not support copying to target')

    def copy_to_host(self, source, destination, timeout=30):
        raise ValueError(
            f'Console type {self} does not support copying from target')

    @property
    def requires_login(self):
        return self._requires_login

    def wait_for_prompt(self, timeout: int = None):
        '''Wait for a prompt, throws if no prompt before timeout'''

        prompt_regex = self.system.prompt_regex
        self.log(f'Waiting for prompt "{prompt_regex}" for {timeout}s')
        self.wait_for_match(match=prompt_regex, timeout=timeout)

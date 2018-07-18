import sys
import time
import serial
import pexpect.fdpexpect

from console import Console


class SerialConsole(Console):
    def __init__(self, port, baud, timeout=10):
        self.port = port
        self.timeout = timeout
        self.baud = baud
        self._ser = None
        self._pex = None
        super().__init__(encoding='ascii', linesep=b'\r\n')

    def __repr__(self):
        return "Serial console device: {}".format(self._ser.port)

    @property
    def is_open(self):
        if not self._ser or not self._pex:
            return False
        else:
            return self._ser.isOpen()

    @property
    def bytes_recieved(self):
        if self.is_open:
            return self._ser.in_waiting
        self.log("Serial port not open")
        return 0

    def flush(self):
        if self.is_open:
            self._ser.reset_input_buffer()
        else:
            self.log("Cannot flush, serial port not open")

    def get_buffer(self):
        buffer = ''
        if self.is_open:
            while self._ser.in_waiting:
                buffer += self.decode(self._ser.read())
        return buffer

    def open(self):
        self.log("Trying to open serial port {}".format(self.port))
        for _ in range(10):
            try:
                self._ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baud,
                    timeout=self.timeout
                )
                self._pex = pexpect.fdpexpect.fdspawn(
                    fd=self._ser.fileno(), timeout=self.timeout)
                self.log("Init serial {} success".format(self.port))
                return
            except Exception as e:
                self.log("Failed to init serial ({}), Error -[{}]. Trying again.".format(self.port, e))
                time.sleep(1)

        raise RuntimeError(
            "Failed to open serial port {} and init pexpect".format(self.port))

    def close(self):
        if self.is_open:
            self._ser.flush()
            self._ser.close()
            self._ser = None
            self.log("Closed serial")
        else:
            self.log("Cannot close serial as it is not open")

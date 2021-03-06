from .hardwarebase import HardwareBase
import time
from abc import ABCMeta, abstractmethod
from functools import wraps


class PowerBase(HardwareBase, metaclass=ABCMeta):
    def __init__(self, reboot_delay=None):
        self.reboot_delay = reboot_delay or 0.5

    @abstractmethod
    def on(f):
        @wraps(f)
        def wrap(self, *args, **kwargs):
            self.log(f'{str(self)}: Power on')
            f(self, *args, **kwargs)
        return wrap

    @abstractmethod
    def off(f):
        @wraps(f)
        def wrap(self, *args, **kwargs):
            self.log(f'{str(self)}: Power off')
            f(self, *args, **kwargs)
        return wrap

    def reboot(self):
        self.off()
        self.log(f'{str(self)}: Waiting {self.reboot_delay}s to power on...')
        time.sleep(self.reboot_delay)
        self.on()

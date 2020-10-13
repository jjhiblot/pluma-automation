from pluma.core.baseclasses import Logger
from pluma.test import ExecutableTest
from pluma.cli import TestsConfigError
from .config import TestDefinition, TestsProvider
from .testsbuilder import TestsBuilder

log = Logger()


class ExtendedYmlProvider(TestsProvider):
    def __init__(self):
        pass

    def display_name(self):
        return 'Extended YML'

    def configuration_key(self):
        return 'xyml'

    def all_tests(self, key: str, config):
        if not config:
            return []
        file = config
        
        return []

import re

from os import path
from .includepaths import IncludePaths
from abc import ABC, abstractmethod
from pluma.core.baseclasses import Logger


class ConfigPreprocessor(ABC):
    @abstractmethod
    def preprocess(self, raw_config: str) -> str:
        '''Return an updated configuration from raw text'''
        pass

    def __add__(a, b):
        if isinstance(a, ConfigPreprocessorPipe):
            l = a.cpps
        else:
            l = [a]
        if isinstance(b, ConfigPreprocessorPipe):
            l = l + b.cpps
        else:
            l = l + [b]
        return ConfigPreprocessorPipe(l)


class ConfigPreprocessorPipe(ConfigPreprocessor):
    def __init__(self, cpps: list = None):
        self.cpps = cpps

    def preprocess(self, raw_config: str) -> str:
        s = raw_config
        for cpp in self.cpps:
            s = cpp.preprocess(s)
        return s


log = Logger()


class PlumaConfigPreprocessor(ConfigPreprocessor):
    def __init__(self, variables: dict):
        self.variables = variables or {}
        if not isinstance(self.variables, dict):
            raise ValueError('Variables must be a dictionary')

    def preprocess(self, raw_config: str) -> str:
        def token_to_variable(token):
            '''remove "${" and "}" '''
            return token[2:len(token)-2]

        missing_variables = []
        vars_found = re.findall(r'{{\w+}}', raw_config, flags=re.MULTILINE)
        unique_vars = set(map(token_to_variable, vars_found))
        vars_found = map(token_to_variable, vars_found)

        # Look for missing variables
        for variable in unique_vars:
            if variable not in self.variables:
                missing_variables.append(variable)

        if missing_variables:
            raise Exception('The following variables are used but not defined: '
                            f'{missing_variables}')

        for variable in unique_vars:
            log.debug(f'{{{{{variable}}}}}={self.variables[variable]}')
            raw_config = re.sub(r'{{'+variable+'}}', self.variables[variable],
                                raw_config)

        return raw_config

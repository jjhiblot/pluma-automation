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


class IncludePreprocessorError(Exception):
    pass


class IncludePreprocessor(ConfigPreprocessor):
    def __init__(self, cwd: str = None):
        self.regex = [re.compile('!include "(\S*)"(.*)'),
                      re.compile('!include (\S*)(.*)')]
        self.cwd = cwd

    def preprocess_lines(self, cwd: str, lines: list) -> list:
        out = []
        lines = [x.rstrip() for x in lines]
        for l in lines:
            if l.startswith('!include '):
                m = None
                for r in self.regex:
                    m = r.match(l)
                    if m:
                        break
                if not m:
                    raise IncludePreprocessorError(f'syntax error {l}. (missing " "  ?)')
                if m.group(2):
                    raise IncludePreprocessorError(f'syntax error {l}. too many tokens')
                if not m.group(1):
                    raise IncludePreprocessorError(f'syntax error {l}. (Must give a file)')

                yaml_file = IncludePaths.locate(
                    filename=m.group(1), current_dir=cwd)
                if not yaml_file:
                    raise IncludePreprocessorError(f'file not found {m.group(1)}.')
                try:
                    f = open(yaml_file, 'r')
                except FileNotFoundError as e:
                    raise IncludePreprocessorError(
                        f'{yaml_file} does not exist') from e
                except Exception as e:
                    raise IncludePreprocessorError(
                        f'Cannot open {yaml_file}') from e

                out.extend(self.preprocess_lines(
                    path.dirname(yaml_file), f.readlines()))
            else:
                out.append(l)
        return out

    def preprocess(self, raw_config: str) -> str:
        return '\n'.join(self.preprocess_lines(self.cwd, raw_config.splitlines()))


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

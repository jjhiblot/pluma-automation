import json
import os
from functools import partial
from typing import List, Union

from pluma.core.baseclasses import Logger, LogLevel
from pluma.test import TestController, TestRunner, TestBase
from pluma.test.stock.deffuncs import sc_run_n_iterations
from pluma.cli import Configuration, ConfigurationError, TestsConfigError, TestDefinition,\
    TestsProvider
from pluma import Board

log = Logger()

SETTINGS_SECTION = 'settings'


class TestsConfig:
    def __init__(self, config: Configuration, test_providers: List[TestsProvider]):
        if not config or not isinstance(config, Configuration):
            raise ValueError(
                f'Null or invalid \'config\', which must be of type \'{Configuration}\'')

        if not test_providers:
            raise ValueError('Null test providers passed')

        if not isinstance(test_providers, list):
            test_providers = [test_providers]

        self.settings_config = config.pop(SETTINGS_SECTION, Configuration())
        self.test_providers = test_providers
        self.tests = None

        self.__populate_tests(config)

        config.ensure_consumed()

    def create_test_controller(self, board: Board) -> TestController:
        '''Create a TestController from the configuration, and Board'''
        if not board or not isinstance(board, Board):
            raise ValueError(
                f'Null or invalid \'board\', which must be of type \'{Board}\'')

        settings = self.settings_config

        try:
            controller = self._create_test_controller(board, settings)
            settings.ensure_consumed()
        except ConfigurationError as e:
            raise TestsConfigError(e)
        else:
            return controller

    def _create_test_controller(self, board: Board, settings: Configuration) -> TestController:
        testrunner = TestRunner(
            board=board,
            tests=TestsConfig.create_tests(
                self.selected_tests(), board),
            sequential=True,
            email_on_fail=settings.pop('email_on_fail', default=False),
            continue_on_fail=settings.pop(
                'continue_on_fail',  default=True),
            skip_tasks=settings.pop('skip_tasks',  default=[]),
            use_testcore=settings.pop(
                'board_test_sequence', default=False)
        )

        controller = TestController(
            testrunner, log_func=partial(log.log, level=LogLevel.INFO),
            verbose_log_func=partial(log.log, level=LogLevel.NOTICE),
            debug_log_func=partial(log.log, level=LogLevel.DEBUG)
        )

        iterations = settings.pop('iterations')
        if iterations:
            controller.run_condition = sc_run_n_iterations(ntimes=int(iterations))

        return controller

    def __populate_tests(self, tests_config: Configuration):
        self.tests = []

        sequence = tests_config.pop('sequence')
        if sequence:
            self.tests = self.tests_from_sequence(sequence, self.test_providers)

    def supported_actions(self, test_providers: List[TestsProvider] = None) -> dict:
        '''Return a map of supported action key strings, and corresponding providers'''
        if test_providers is None:
            test_providers = self.test_providers

        return TestsConfig._supported_actions(test_providers)

    @staticmethod
    def _supported_actions(test_providers: List[TestsProvider]) -> dict:
        '''Return a map of supported action key strings, and corresponding providers'''
        if test_providers is None:
            raise ValueError('None test_providers provided.')

        actions = {}
        for provider in test_providers:
            keys = provider.configuration_key()
            if isinstance(keys, str):
                keys = [keys]

            for key in keys:
                if key in actions:
                    raise TestsConfigError(
                        f'Error adding keys for provider {str(provider)}: key "{key}"'
                        f' is already registered by {str(actions[key])}')
                actions[key] = provider

        return actions

    @classmethod
    def tests_from_sequence(cls, sequence: list, test_providers: List[TestsProvider]) \
            -> List[TestDefinition]:
        '''Return a list of all tests generated by providers from a sequence'''
        if not isinstance(sequence, list):
            raise TestsConfigError(
                f'Invalid sequence, "sequence" must be a list (currently defined as {sequence})')

        all_tests = []
        supported_actions = cls._supported_actions(test_providers)

        # Parse sequence
        for action in sequence:
            if not isinstance(action, dict):
                raise TestsConfigError(
                    f'Invalid sequence action "{action}", which is not a dictionary')

            if len(action) != 1:
                raise TestsConfigError(
                    f'Sequence list elements must be single key elements, but got "{action}".'
                    f' Supported actions: {supported_actions.keys()}')

            action_key = next(iter(action))
            tests = cls.tests_from_action(action_key=action_key,
                                          action_config=action[action_key],
                                          supported_actions=supported_actions)
            all_tests.extend(tests)

        return all_tests

    @staticmethod
    def tests_from_action(action_key: str, action_config: Union[dict, Configuration],
                          supported_actions: dict) -> List[TestDefinition]:
        '''Return a list of all test definitions for a specific action and action providers'''
        provider = supported_actions.get(action_key)
        if not provider:
            raise TestsConfigError(
                f'No test provider was found for sequence action "{action_key}".'
                f' Supported actions: {supported_actions.keys()}')

        if isinstance(action_config, dict):
            tests = provider.all_tests(key=action_key, config=Configuration(action_config))
        else:
            tests = provider.all_tests(key=action_key, config=action_config)

        return tests

    def selected_tests(self) -> List[TestDefinition]:
        '''Return only selected tests among all tests available'''
        return list(filter(lambda test: (test.selected), self.tests))

    def print_tests(self, log_level: LogLevel = None):
        TestsConfig.print_tests_definition(self.tests, log_level=log_level)

    @staticmethod
    def print_tests_definition(tests: List[TestDefinition], log_level: LogLevel = None):
        if not log_level:
            log_level = LogLevel.INFO

        tests = sorted(
            tests, key=lambda test: test.provider.__class__.__name__)

        last_provider = None
        for test in tests:
            if test.provider != last_provider:
                log.log(f'{os.linesep}{test.provider.display_name()}:',
                        bold=True, level=log_level)
                last_provider = test.provider

            check = 'x' if test.selected else ' '
            log.log(f'    [{check}] {test.name}',
                    color='green' if test.selected else 'normal', level=log_level)

            for test_parameters in test.parameter_sets:
                if test.selected and test_parameters:
                    printed_data = json.dumps(test_parameters)
                    log.log(f'          {printed_data}', level=log_level)

        log.log('', level=log_level)

    @staticmethod
    def create_tests(tests: List[TestDefinition], board: Board) -> List[TestBase]:
        test_objects = []
        for test in tests:
            try:
                for parameters in test.parameter_sets:
                    parameters = parameters if parameters else dict()

                    if isinstance(parameters, dict):
                        test_object = test.testclass(board, **parameters)
                    else:
                        test_object = test.testclass(board, parameters)

                    test_objects.append(test_object)
            except Exception as e:
                if f'{e}'.startswith('__init__()'):
                    raise TestsConfigError(
                        f'The test "{test.name}" requires one or more parameters to be provided '
                        f'in the "parameters" attribute in your "pluma.yml" file:{os.linesep}'
                        f'    {e}')
                else:
                    raise TestsConfigError(
                        f'Failed to create test "{test.name}":{os.linesep}    {e}')

        return test_objects

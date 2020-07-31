import json
import os
from functools import partial

from farmcore.baseclasses import Logger, LogLevel
from farmtest import TestController, TestRunner
from farmtest.stock.deffuncs import sc_run_n_iterations
from farmcli import Configuration, ConfigurationError, TestsConfigError
from farmcore import Board

log = Logger()

SETTINGS_SECTION = 'settings'
PYTHON_TESTS_SECTION = 'tests'
SCRIPT_TESTS_SECTION = 'script_tests'
C_TESTS_SECTION = 'c_tests'


class TestsConfig:
    def __init__(self, config: Configuration, test_providers: list):
        if not config or not isinstance(config, Configuration):
            raise ValueError(
                f'Null or invalid \'config\', which must be of type \'{Configuration}\'')

        if not test_providers:
            raise ValueError('Null test providers passed')

        if not isinstance(test_providers, list):
            test_providers = [test_providers]

        self.settings_config = config.pop(SETTINGS_SECTION)
        self.test_providers = test_providers
        self.tests = None

        self.__populate_tests(config)

        config.ensure_consumed()

    def create_test_controller(self, board: Board) -> TestController:
        if not board or not isinstance(board, Board):
            raise ValueError(
                f'Null or invalid \'board\', which must be of type \'{Board}\'')

        try:
            settings = self.settings_config

            controller = TestController(
                testrunner=TestRunner(
                    board=board,
                    tests=TestsConfig.create_tests(
                        self.selected_tests(), board),
                    sequential=settings.pop('sequential', default=True),
                    email_on_fail=settings.pop('email_on_fail', default=False),
                    continue_on_fail=settings.pop(
                        'continue_on_fail',  default=True),
                    skip_tasks=settings.pop('skip_tasks',  default=[]),
                    use_testcore=settings.pop(
                        'board_test_sequence', default=False)
                ),
                log_func=partial(log.log, level=LogLevel.INFO),
                verbose_log_func=partial(log.log, level=LogLevel.NOTICE)
            )

            iterations = settings.pop('iterations')
            if iterations:
                controller.run_condition = sc_run_n_iterations(
                    ntimes=int(iterations))

            settings.ensure_consumed()
        except ConfigurationError as e:
            raise TestsConfigError(e)

        return controller

    def __populate_tests(self, tests_config: Configuration):
        self.tests = []

        sequence = tests_config.pop('sequence')
        if sequence:
            self.tests = self.__all_tests_from_sequence(sequence)
        else:
            for provider in self.test_providers:
                provider_config = tests_config.pop(
                    provider.configuration_key())
                self.tests.extend(provider.all_tests(provider_config))

    def __all_tests_from_sequence(self, sequence: list) -> list:
        if not isinstance(sequence, list):
            raise TestsConfigError(
                f'Invalid sequence, "sequence" must be a list (currently defined as {sequence})')

        all_tests = []
        supported_actions = [p.configuration_key()
                             for p in self.test_providers]
        for action in sequence:
            if not isinstance(action, dict):
                raise TestsConfigError(
                    f'Invalid sequence action "{action}", which is not a dictionary')

            if len(action) != 1:
                raise TestsConfigError(
                    f'Sequence list elements must be single key elements, but got "{action}". Supported actions: {supported_actions}')

            action_key = next(iter(action))
            try:
                provider = next(p for p in self.test_providers
                                if p.configuration_key() == action_key)
                all_tests.extend(provider.all_tests(
                    Configuration(action[action_key])))
            except StopIteration:
                raise TestsConfigError(
                    f'No test provider was found for sequence action "{action_key}". Supported actions: {supported_actions}')

        return all_tests

    def selected_tests(self) -> list:
        return list(filter(lambda test: (test.selected), self.tests))

    def print_tests(self, log_level: LogLevel = None):
        TestsConfig.print_tests_definition(self.tests, log_level=log_level)

    @staticmethod
    def print_tests_definition(tests: list, log_level: LogLevel = None):
        if not log_level:
            log_level = LogLevel.INFO

        tests = sorted(
            tests, key=lambda test: test.provider.configuration_key())

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
                if test.selected and len(test_parameters) > 0:
                    printed_data = json.dumps(test_parameters)
                    log.log(f'          {printed_data}', level=log_level)

        log.log('', level=log_level)

    @staticmethod
    def create_tests(tests: list, board: Board) -> list:
        test_objects = []
        for test in tests:
            try:
                for parameters in test.parameter_sets:
                    test_object = test.testclass(board, **parameters)
                    test_objects.append(test_object)
            except Exception as e:
                if f'{e}'.startswith('__init__()'):
                    raise TestsConfigError(
                        f'The test "{test.name}" requires one or more parameters to be provided '
                        f'in the "parameters" attribute in your "pluma.yml" file:{os.linesep}    {e}')
                else:
                    raise TestsConfigError(
                        f'Failed to create test "{test.name}":{os.linesep}    {e}')

        return test_objects

from os import path
import os
import pytest

from pluma.cli import Pluma, ConfigurationError, TestsConfigError, TargetConfigError


config_folder = path.join(path.dirname(__file__), 'test-configs/')


def config_file_path(config: str):
    return path.join(config_folder, f'{config}.yml')


def run_all(test_file: str, target_file: str):
    test_file_path = path.join(config_file_path(test_file))
    target_file_path = path.join(config_file_path(target_file))

    Pluma.execute_tests(test_file_path, target_file_path)
    Pluma.execute_run(test_file_path, target_file_path, check_only=True)


def test_Pluma_minimal():
    run_all('minimal-tests', 'minimal-target')


def test_Pluma_works_with_samples():
    run_all('sample-tests', 'sample-target')


def test_Pluma_target_variables_substitution():
    run_all('variable-sub-tests', 'variable-sub-target')


def test_Pluma_create_target_context_should_parse_target_variables():
    context = Pluma.create_target_context(config_file_path('variable-sub-target'))
    assert context.variables['mymessage'] == 'echo hello script!'


def test_Pluma_create_target_context_variables_should_reflect_env_vars():
    env = dict(os.environ)
    try:
        os.environ['abc'] = 'def'
        context = Pluma.create_target_context(config_file_path('minimal-target'))

        assert context.variables['abc'] == 'def'
    finally:
        os.environ.clear()
        os.environ.update(env)


def test_Pluma_create_target_context_env_vars_should_override_target_variables():
    env = dict(os.environ)
    try:
        os.environ['mymessage'] = 'env message'
        context = Pluma.create_target_context(config_file_path('variable-sub-target'))
        assert context.variables['mymessage'] == 'env message'
    finally:
        os.environ.clear()
        os.environ.update(env)


def test_Pluma_env_substitution_should_read_from_env_vars():
    env = dict(os.environ)
    try:
        os.environ['console'] = 'console'
        os.environ['port'] = '/dev/random'
        os.environ['some_env_var'] = 'echo "from env var"'
        run_all('variable-env-sub-tests', 'variable-env-sub-target')
    finally:
        os.environ.clear()
        os.environ.update(env)


def test_Pluma_env_vars_substitution_should_error_if_var_not_set():
    with pytest.raises(ConfigurationError):
        run_all('variable-env-sub-tests', 'variable-env-sub-target')


def test_Pluma_env_vars_substitution_should_error_on_invalid_config():
    env = dict(os.environ)
    try:
        os.environ['console'] = 'not good'
        os.environ['port'] = '/dev/random'
        os.environ['some_env_var'] = 'echo "from env var"'
        with pytest.raises(TargetConfigError):
            run_all('variable-env-sub-tests', 'variable-env-sub-target')
    finally:
        os.environ.clear()
        os.environ.update(env)


def test_Pluma_tests_error_on_unknown_action():
    with pytest.raises(TestsConfigError):
        run_all('invalid-action-tests', 'minimal-target')


def test_Pluma_tests_error_on_unknown_attribute():
    with pytest.raises(ConfigurationError):
        run_all('invalid-attributes-tests', 'minimal-target')


def test_Pluma_target_error_on_unknown_attribute():
    with pytest.raises(TargetConfigError):
        run_all('minimal-tests', 'invalid-attributes-target')

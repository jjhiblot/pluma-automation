import time
import pytest
from pluma.core.exceptions import ConsoleLoginFailedError

from utils import nonblocking
from loremipsum import loremipsum


def test_SerialConsole_send_sends_data(serial_console_proxy):
    serial_console_proxy.console.send('Foo')

    written = serial_console_proxy.read_serial_output()

    assert written


def test_SerialConsole_send_sends_correct_data(serial_console_proxy):
    msg = loremipsum
    serial_console_proxy.console.send(msg)

    written = serial_console_proxy.read_serial_output()

    assert written == f'{msg}{serial_console_proxy.console.engine.linesep}'


def test_SerialConsole_send_doesnt_send_newline_when_send_newline_arg_false(serial_console_proxy):
    msg = loremipsum
    serial_console_proxy.console.send(msg, send_newline=False)

    written = serial_console_proxy.read_serial_output()

    assert written == msg


def test_SerialConsole_read_all_returns_all_data(serial_console_proxy):
    msg = 'Bar'

    serial_console_proxy.console.open()
    serial_console_proxy.fake_reception(msg)
    received = serial_console_proxy.console.read_all()

    assert received == msg


def test_SerialConsole_send_and_expect_matches_regex(serial_console_proxy):
    msg = 'Hello World! 123FooBarBaz'
    regex = '[0-3]+Foo'
    expected_match = '123Foo'

    async_result = nonblocking(serial_console_proxy.console.send_and_expect,
                               cmd='', match=regex)

    serial_console_proxy.fake_reception(msg)

    __, matched = async_result.get()
    assert matched == expected_match


def test_SerialConsole_send_and_expect_matches_regex(serial_console_proxy):
    expected_match = '123Match'
    expected_received = f'Multiline content\n and {expected_match}'
    regex = '[0-3]+Match'

    send_and_expect_result = nonblocking(serial_console_proxy.console.send_and_expect,
                                         cmd='abc', match=regex)

    serial_console_proxy.fake_reception(expected_received+'Trailing content')

    received, matched = send_and_expect_result.get()
    assert received == expected_received
    assert matched == expected_match


def test_SerialConsole_send_and_expect_matches_regex_with_previous_content(
        serial_console_proxy):
    expected_match = '123Match'
    expected_received = f'Multiline content\n and {expected_match}'
    regex = '[0-3]+Match'

    serial_console_proxy.fake_reception('Some content sent before trying to match')

    send_and_expect_result = nonblocking(serial_console_proxy.console.send_and_expect,
                                         cmd='abc', match=regex)

    serial_console_proxy.fake_reception(expected_received)

    received, matched = send_and_expect_result.get()
    assert received == expected_received
    assert matched == expected_match


def test_SerialConsole_send_and_expect_ignores_previous_content(serial_console_proxy):
    expected_received = 'Not really matching.'
    regex = '[0-3]+Match'

    serial_console_proxy.fake_reception(expected_received)

    send_and_expect_result = nonblocking(serial_console_proxy.console.send_and_expect,
                                         cmd='abc', match=regex, timeout=0.5)

    received, matched = send_and_expect_result.get()
    assert received == received
    assert matched is None


@pytest.mark.parametrize('timeout', [0.2, 1])
def test_SerialConsole_send_and_expect_returns_after_timeout(serial_console_proxy, timeout):
    start_time = time.time()

    send_and_expect_result = nonblocking(serial_console_proxy.console.send_and_expect,
                                         cmd='abc', match='NoFoo', timeout=timeout)

    serial_console_proxy.fake_reception('abc\ndef')

    send_and_expect_result.get()
    total_duration = time.time() - start_time

    assert 0.8 * timeout < total_duration < 1.2*timeout


def test_SerialConsole_check_alive_returns_true_when_target_responds(serial_console_proxy):
    async_result = nonblocking(
        serial_console_proxy.console.check_alive)

    # Send console a newline char
    serial_console_proxy.fake_reception(serial_console_proxy.console.engine.linesep)

    assert async_result.get() is True


def test_SerialConsole_check_alive_returns_true_when_target_not_responds(serial_console_proxy):
    async_result = nonblocking(
        serial_console_proxy.console.check_alive,
        timeout=1)

    # Send no response to console
    assert async_result.get() is False


def test_SerialConsole_login_finds_user_match_sends_correct_username(serial_console_proxy):
    user_match = 'Enter username: '
    username = 'Foo'

    nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        username=username)

    # Expect line break, to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected


def test_SerialConsole_login_success_with_no_password(serial_console_proxy):
    user_match = 'Enter username: '
    username = 'Foo'

    async_result = nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        username=username)

    # Expect line break, used to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    # Wait for console.login() to finish
    async_result.get()

    # If we've gotten to here without error then success
    assert True


def test_SerialConsole_login_finds_pass_match_sends_correct_pass(serial_console_proxy):
    user_match = 'Enter username: '
    pass_match = 'Enter password: '
    username = 'Foo'
    password = 'Bar'

    nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        password_match=pass_match,
        username=username,
        password=password)

    # Expect line break, used to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(pass_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{password}{serial_console_proxy.console.engine.linesep}'

    assert received == expected


def test_SerialConsole_login_no_exception_on_success_no_success_match(serial_console_proxy):
    user_match = 'Enter username: '
    pass_match = 'Enter password: '
    username = 'Foo'
    password = 'Bar'

    async_result = nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        password_match=pass_match,
        username=username,
        password=password)

    # Expect line break, used to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(pass_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{password}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    # Wait for console.login() to finish
    async_result.get()

    # If we've gotten to here without error then success
    assert True


def test_SerialConsole_login_no_exception_on_success_with_success_match(serial_console_proxy):
    user_match = 'Enter username: '
    pass_match = 'Enter password: '
    success_match = 'command prompt >>'
    username = 'Foo'
    password = 'Bar'

    async_result = nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        password_match=pass_match,
        username=username,
        password=password,
        success_match=success_match)

    # Expect line break, used to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(pass_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{password}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(success_match)

    # Wait for response
    time.sleep(0.01)

    # Wait for console.login() to finish
    async_result.get()

    # If we've gotten to here without error then success
    assert True


def test_SerialConsole_login_except_on_wrong_success_match(serial_console_proxy):
    user_match = 'Enter username: '
    pass_match = 'Enter password: '
    success_match = 'command prompt >>'
    username = 'Foo'
    password = 'Bar'

    async_result = nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        password_match=pass_match,
        username=username,
        password=password,
        success_match=success_match)

    # Wait short time for function to start
    time.sleep(0.1)

    # Expect line break, used to force printing the prompt
    received = serial_console_proxy.read_serial_output()
    expected = f'{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')
        time.sleep(0.01)

    serial_console_proxy.fake_reception(user_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{username}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(pass_match)

    received = serial_console_proxy.read_serial_output()
    expected = f'{password}{serial_console_proxy.console.engine.linesep}'

    assert received == expected

    serial_console_proxy.fake_reception(
        'This is not the success_match you are looking for')

    with pytest.raises(ConsoleLoginFailedError):
        # Wait for console.login() to finish
        async_result.get()


def test_SerialConsole_login_except_on_wrong_username_match(serial_console_proxy):
    user_match = 'Enter username: '
    username = 'Foo'

    async_result = nonblocking(
        serial_console_proxy.console.login,
        username_match=user_match,
        username=username)

    for i in range(0, 10):
        serial_console_proxy.fake_reception(
            f'Nonsense non matching line {i}...')

    serial_console_proxy.fake_reception(
        'This is not the username_match you are looking for')

    with pytest.raises(ConsoleLoginFailedError):
        # Wait for console.login() to finish
        async_result.get()


def test_SerialConsole_read_all_clears_buffer(serial_console_proxy):
    # Send console a newline char
    serial_console_proxy.fake_reception(serial_console_proxy.console.engine.linesep)

    time.sleep(0.01)

    serial_console_proxy.console.read_all()

    data_received = serial_console_proxy.console.wait_for_bytes(timeout=0.5)

    assert data_received is False


def test_SerialConsole_read_all_returns_received(serial_console_proxy):
    data1 = 'Line1'

    serial_console_proxy.console.open()
    serial_console_proxy.fake_reception(data1)

    assert serial_console_proxy.console.read_all() == data1


def test_SerialConsole_read_all_clears_received(serial_console_proxy):
    data1 = 'Line1'

    serial_console_proxy.console.open()
    serial_console_proxy.fake_reception(data1)

    assert serial_console_proxy.console.read_all() != ''
    assert serial_console_proxy.console.read_all() == ''


def test_SerialConsole_read_all_preserve_buffer(serial_console_proxy):
    data2 = 'Line2'
    serial_console_proxy.console.open()
    serial_console_proxy.fake_reception(data2)

    assert serial_console_proxy.console.read_all(
        preserve_read_buffer=True) == data2
    assert serial_console_proxy.console.read_all(
        preserve_read_buffer=True) == data2
    assert serial_console_proxy.console.read_all() == data2
    assert serial_console_proxy.console.read_all() == ''


def test_SerialConsole_does_not_require_login(serial_console_proxy):
    assert serial_console_proxy.console.requires_login is True

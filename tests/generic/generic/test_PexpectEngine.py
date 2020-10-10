import time
import pytest

from pluma.core.baseclasses import PexpectEngine


def test_PexpectEngine_open_shell_should_succeed():
    engine = PexpectEngine()
    engine.open(console_cmd='sh')
    assert engine.is_open


def test_PexpectEngine_close_shell_should_succeed():
    engine = PexpectEngine()
    engine.open(console_cmd='sh')
    engine.close()
    assert engine.is_open is False


def test_PexpectEngine_open_fd_should_succeed(pty_pair):
    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)
    assert engine.is_open


def test_PexpectEngine_send_line_write_content_and_line_break(pty_pair):
    sent = 'abcdef'
    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)
    engine.send_line(sent)

    assert pty_pair.secondary.read(timeout=0.5) == sent+'\n'


def test_PexpectEngine_read_all_reads_from_console(pty_pair):
    received = 'abc\ndef'
    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)

    pty_pair.secondary.write(received)
    received_actual = engine.read_all()

    assert received_actual == received


def test_PexpectEngine_read_all_returns_received_only_once(pty_pair):
    received = 'abc\ndef'
    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)

    pty_pair.secondary.write(received)
    received1_actual = engine.read_all()
    received2_actual = engine.read_all()

    assert received1_actual == received
    assert received2_actual == ''


def test_PexpectEngine_wait_for_match_return_match_and_if_matched(pty_pair):
    pattern = r'ab\S+yz'
    pattern_text = 'abcdyz'
    received = f'abcd {pattern_text}'

    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)

    pty_pair.secondary.write(received)
    match = engine.wait_for_match(match=[pattern], timeout=0.5)

    assert match.regex_matched == pattern
    assert match.text_matched == pattern_text
    assert match.text_received == received


def test_PexpectEngine_wait_for_match_return_received_if_not_matched(pty_pair):
    pattern = r'not going to match'
    received = f'abcd abcdyz'

    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)

    pty_pair.secondary.write(received)
    match = engine.wait_for_match(match=[pattern], timeout=0.5)

    assert match.regex_matched is None
    assert match.text_matched is None
    assert match.text_received == received


def test_PexpectEngine_wait_for_match_should_match_only_once(pty_pair):
    pattern = r'ab\S+yz'
    pattern_text = 'abcdyz'
    received = f'abcd {pattern_text}'

    engine = PexpectEngine()
    engine.open(console_fd=pty_pair.main.fd)

    pty_pair.secondary.write(received)
    match = engine.wait_for_match(match=[pattern], timeout=0.5)

    assert match.regex_matched

    match = engine.wait_for_match(match=[pattern], timeout=0.5)

    assert match.regex_matched is None
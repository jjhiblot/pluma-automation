from pluma.core.baseclasses import Logger
from pluma import HostConsole, Board
from pluma.core.baseclasses import ConsoleBase
from pluma.test import CommandRunner, TestBase, TaskFailed

log = Logger()


class ShellTest(TestBase):
    shell_test_index = 0

    def __init__(self, board: Board, script: str, name: str = None, should_print: list = None,
                 should_not_print: list = None, run_on_host: bool = False, timeout: int = None,
                 runs_in_shell: bool = True, login_automatically: bool = True):
        super().__init__(board)
        self.should_print = should_print or []
        self.should_not_print = should_not_print or []
        self.run_on_host = run_on_host
        self.timeout = timeout if timeout is not None else 5
        self.runs_in_shell = runs_in_shell
        self.login_automatically = login_automatically

        self.scripts = script
        if not isinstance(self.scripts, list):
            self.scripts = [self.scripts]

        if name:
            self._test_name += f'[{name}]'
        else:
            ShellTest.shell_test_index += 1
            self._test_name += f'[{ShellTest.shell_test_index}]'

        if not self.run_on_host and not self.board.console:
            raise ValueError(
                f'Cannot run script test "{self._test_name}" on target: no console'
                ' was defined. Define a console in "pluma-target.yml", or use '
                ' "run_on_host" test attribute to run on the host instead.')

    def test_body(self):
        self.run_commands()

    def run_commands(self, console: ConsoleBase = None,
                     scripts: str = None, timeout: int = None) -> str:
        timeout = timeout or self.timeout
        scripts = scripts or self.scripts

        if console is None:
            if self.run_on_host:
                console = HostConsole('sh')
            else:
                console = self.board.console
                if not console:
                    raise TaskFailed(f'Failed to run script test "{self._test_name}": '
                                     'no console available')

        if self.runs_in_shell and self.login_automatically and console.requires_login:
            self.board.login()

        output = ''
        for script in scripts:
            output += self.run_command(console=console, command=script)

        if self.should_print or self.should_not_print:
            CommandRunner.check_output(test_name=self._test_name, command=script, output=output,
                                       should_print=self.should_print,
                                       should_not_print=self.should_not_print)
        return output

    def run_command(self, console: ConsoleBase, script: str) -> str:
        if self.runs_in_shell:
            output = CommandRunner.run(test_name=self._test_name, console=console,
                                       command=script, timeout=self.timeout)
        else:
            output = CommandRunner.run_raw(test_name=self._test_name, console=console,
                                           command=script, timeout=self.timeout)

        return output

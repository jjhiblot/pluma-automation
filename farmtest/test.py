'''
class ExampleTest():
    def __init__(self, board):
        self.board = board

    # Any of the below tasks will be called at the correct time,
    # if they are implimented (All are optional)

    def __init__(self, board):
        self.board = board

    def prepare(self):
        pass

    def pre_board_on(self):
        pass

    def pre_board_mount(self):
        pass

    def post_board_mount(self):
        pass

    def test_body(self):
        pass

    def pre_board_unmount(self):
        pass

    def post_board_off(self):
        pass

    def report(self):
        pass
'''

import time

from farmcore.console import LoginFailed
from farmcore.board import BootValidationError


class TaskFailed(Exception):
    pass


class TestBase():
    tasks_failed = []


class TestCore(TestBase):
    tasks = [
        '_host_mount', 'prepare', '_host_unmount',
        'pre_board_on', '_board_on_and_validate',
        'pre_board_login', '_board_login',
        'pre_board_mount', '_board_mount', 'post_board_mount',
        'test_body',
        'pre_board_unmount', '_board_unmount',
        '_board_off', 'post_board_off',
        '_host_mount', 'report'
    ]

    def __init__(self, board):
        self.board = board

    def prepare(self):
        self.board.log("=== PREPARE ===")

    def _host_unmount(self):
        self.board.log("=!= HOST UNMOUNT =!=")

        #TODO: Move this functionality to the board class
        devnode = None
        for _ in range(1, 5):
            if not self.board.hub.get_part():
                time.sleep(1)
            else:
                devnode = self.board.hub.get_part()['devnode']
        if devnode:
            self.board.storage.unmount_host(devnode)
        else:
            self.board.log("Cannot find block device. Continuing anyway")

        self.board.storage.to_board()

    def pre_board_on(self):
        self.board.log("=== PRE BOARD ON ===")

    def _board_on_and_validate(self):
        self.board.log("=!= BOARD ON AND VALIDATE =!=")
        try:
            self.board.reboot_and_validate()
        except BootValidationError as e:
            raise TaskFailed(str(e))

    def pre_board_login(self):
        self.board.log("=== PRE BOARD LOGIN ===")

    def _board_login(self):
        self.board.log("=!= BOARD LOGIN =!=")
        try:
            self.board.login()
        except LoginFailed as e:
            raise TaskFailed(str(e))

    def pre_board_mount(self):
        self.board.log("=== PRE BOARD MOUNT ===")

    def _board_mount(self):
        self.board.log("=!= BOARD MOUNT =!=")
        self.board.storage.to_board()
        self.board.storage.mount_board()

    def post_board_mount(self):
        self.board.log("=== POST BOARD MOUNT ===")

    def test_body(self):
        self.board.log("=== TEST BODY ===")

    def pre_board_unmount(self):
        self.board.log("=== PRE BOARD UNMOUNT ===")

    def _board_unmount(self):
        self.board.log("=!= BOARD UNMOUNT =!=")
        self.board.storage.unmount_board()

    def _board_off(self):
        self.board.log("=!= BOARD OFF =!=")
        self.board.power.off()

    def post_board_off(self):
        self.board.log("=== POST BOARD OFF ===")

    def _host_mount(self):
        self.board.log("=!= HOST MOUNT =!=")
        self.board.storage.to_host()

        devnode = None
        for _ in range(1, 5):
            if not self.board.hub.get_part():
                time.sleep(1)
            else:
                devnode = self.board.hub.get_part()['devnode']
        if not devnode:
            raise TaskFailed('Cannot mount: No block device downstream of hub')

        self.board.storage.mount_host(devnode)

    def report(self):
        self.board.log("=== REPORT ===")


class TestRunner():
    def __init__(self, board, tests=None):
        self.board = board
        self.tests = []
        tests = tests or []
        if not isinstance(tests, list):
            tests = [tests]

        self.tasks = TestCore.tasks
        self.use_testcore = True

        # General purpose data for use globally between tests
        self.data = {}
        for test in tests:
            self.add_test(test)

    def __call__(self):
        self.run()

    def run(self):
        if (self.use_testcore and "TestCore" not in
                (_test_name(t) for t in self.tests)):
            self.add_test(TestCore(self.board), 0)

        self.board.log("Running tests: {}".format(
            list(map(lambda t: t.__class__.__name__, self.tests))))

        for task in self.tasks:
            self._run_task(task)

        self.board.log("== ALL TESTS COMPLETED ==")

    def add_test(self, test, index=None):
        if index is None:
            self.board.log("Appending test: {}".format(_test_name(test)))
            self.tests.append(test)
        else:
            self.board.log("Inserting test at position {}: {} ".format(
                index, _test_name(test)))
            self.tests.insert(index, test)

    def rm_test(self, test):
        if test in self.tests:
            self.board.log("Removed test: {}".format(_test_name(test)))
            self.tests.remove(test)

    def _run_task(self, task_name):
        if "mount" in task_name and not self.board.storage:
            self.board.log("Board does not have storage. Skipping task: {}".format(task_name))
            return

        for test in self.tests:
            task_func = getattr(test, task_name, None)
            if task_func:
                if test.__class__ != TestCore:
                    self.board.log("Running: {} - {}".format(
                        _test_name(test), task_name))
                try:
                    task_func()
                except TaskFailed as e:
                    self.board.log("Task failed: {} - {}: {}".format(
                        _test_name(test), task_name, str(e)))
                    test.tasks_failed.append({'name': task_name, 'cause': str(e)})
                    if 'report' in self.tasks:
                        if task_name == 'report':
                            raise e
                        else:
                            self._run_task('report')
                            sys.exit(1)



def _test_name(test):
    return test.__class__.__name__

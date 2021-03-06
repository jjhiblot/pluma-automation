from pluma.core import Board


class TestBase():
    """Base class for tests"""

    def __init__(self, board: Board, test_name_suffix: str = None):
        """Construct a TestBase with a board, and test suffix"""
        self.board = board

        if self.__class__.__module__:
            self._test_name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        else:
            self._test_name = self.__class__.__name__

        if test_name_suffix:
            assert isinstance(test_name_suffix, str)
            self._test_name += f'_{test_name_suffix}'

        # Settings to control this test instance
        self.settings = {}

        # Output data to be saved during the test
        self.data = {}

    def __repr__(self):
        """Return a human-readable name for the test"""
        return self._test_name

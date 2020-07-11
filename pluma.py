import sys
import json
import logging
import time

from farmcore import Board
from farmtest import TestController
from farmcli import Config, TestsConfig, TargetConfig


def main():
    log = logging.getLogger(__name__)

    tests_config_path = 'pluma.yml'
    target_config_path = 'pluma-target.yml'

    tests_config, target_config = Config.load_configuration(
        tests_config_path, target_config_path)

    board = TargetConfig.create_board(target_config)

    default_log = 'pluma-{}.log'.format(time.strftime("%Y%m%d-%H%M%S"))
    board.log_file = tests_config.get('log') or default_log

    tests_controller = TestsConfig.create_test_controller(tests_config, board)
    tests_controller.run()

    print(tests_controller.get_test_results())


if __name__ == "__main__":
    main()
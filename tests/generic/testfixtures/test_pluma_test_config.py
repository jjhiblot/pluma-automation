from pluma.plugins.testsuite.memory import MemorySize
from pluma.plugins.testsuite.networking import IperfBandwidth
from pluma.plugins.testsuite.kernel import KernelModulesLoaded


def test_pluma_config_file_should_create_config_with_one_core_test(pluma_config_file):

    expected_content = '''\
- core_tests:
    include: [testsuite.memory]
    parameters:
        testsuite.memory.MemorySize:
            total_mb: 985
            available_mb: 500\
'''

    config_file = pluma_config_file([
        (MemorySize, {
            'total_mb': 985,
            'available_mb': 500
        })
    ])

    with open(config_file, 'r') as f:
        content = f.read()
        assert expected_content == content


def test_pluma_config_file_should_create_config_with_multiple_core_tests(pluma_config_file):
    expected_content = '''\
- core_tests:
    include: [testsuite.memory, testsuite.networking, testsuite.kernel]
    parameters:
        testsuite.memory.MemorySize:
            total_mb: 985
            available_mb: 500
        testsuite.networking.IperfBandwidth:
            minimum_mbps: 10
        testsuite.kernel.KernelModulesLoaded:
            modules: [wlan, galcore]\
'''

    config_file = pluma_config_file([
        (MemorySize, {
            'total_mb': 985,
            'available_mb': 500
        }),
        (IperfBandwidth, {
            'minimum_mbps': 10,
        }),
        (KernelModulesLoaded, {
            'modules': '[wlan, galcore]',
        }),
    ])

    with open(config_file, 'r') as f:
        content = f.read()
        assert expected_content == content


def test_pluma_config_file_should_create_config_with_multiple_same_core_tests(pluma_config_file):

    expected_content = '''\
- core_tests:
    include: [testsuite.memory]
    parameters:
        testsuite.memory.MemorySize:
            total_mb: 985
            available_mb: 500
        testsuite.memory.MemorySize:
            total_mb: 100
            available_mb: 200\
'''

    config_file = pluma_config_file([
        (MemorySize, {
            'total_mb': 985,
            'available_mb': 500
        }),
        (MemorySize, {
            'total_mb': 100,
            'available_mb': 200
        })
    ])

    with open(config_file, 'r') as f:
        content = f.read()
        assert expected_content == content


def test_pluma_config_file_should_create_config_with_parameter_lists(pluma_config_file):

    expected_content = '''\
- core_tests:
    include: [testsuite.kernel]
    parameters:
        testsuite.kernel.KernelModulesLoaded:
            modules: [wlan, galcore]\
'''

    config_file = pluma_config_file([
        (KernelModulesLoaded, {
            'modules': ['wlan', 'galcore'],
        }),
    ])

    with open(config_file, 'r') as f:
        content = f.read()
        assert expected_content == content

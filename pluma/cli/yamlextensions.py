import inspect
import yaml
import os
from os import path
from typing import Any, IO
from .includepaths import IncludePaths
from .configpreprocessor import ConfigPreprocessor


class YamlExtendedLoader(yaml.FullLoader):
    def __init__(self, content: str, _root: str, preprocessor: ConfigPreprocessor = None) -> None:
        self.preprocessor = preprocessor
        self._root = _root
        if self.preprocessor:
            content = self.preprocessor.preprocess(content)
        super().__init__(content)


def construct_include(loader: YamlExtendedLoader, node: yaml.Node) -> Any:
    base_name = loader.construct_scalar(node)
    filename = IncludePaths.locate(
        current_dir=loader._root, filename=base_name)
    with open(filename, 'r') as f:
        content = f.read()

    appends = IncludePaths.locateall(
        current_dir=loader._root, filename=base_name+"_append")
    for filename in appends:
        with open(filename, 'r') as f:
            content += "\n" + f.read()
        print(content)

    loader = YamlExtendedLoader(content,
                                _root=path.dirname(base_name),
                                preprocessor=loader.preprocessor)
    obj = loader.get_single_data()
    loader.dispose()
    # Insert a "_root" property to allow the usage of relative paths.
    # ex:
    #      c_test: !include project1/cves/cve-xx-yy.yaml
    # and in project1/cves/cve-xx-yy.yaml:
    #      yocto_sdk: /opt/seb-dev/2.6.2/environment-setup-aarch64-poky-linux
    #      MyTest:
    #        sources: [cve-xx-yy.c]
    # The "_root" property can be used by the c_test parser to find the actual
    # path to cve-xx-yy.c file.
    if not "_root" in obj:
        if not path.isabs(base_name):
            obj["_root"] = path.relpath(path.dirname(path.normpath(base_name)))
        else:
            obj["_root"] = path.dirname(path.normpath(base_name))
    return obj


yaml.add_constructor('!include', construct_include, YamlExtendedLoader)

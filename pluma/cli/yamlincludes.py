import inspect
import yaml
import os
from os import path
from typing import Any, IO
from .includepaths import IncludePaths
from .configpreprocessor import ConfigPreprocessor


class YamlIncludesLoader(yaml.FullLoader):
    def __init__(self, content: str, _root: str, preprocessor: ConfigPreprocessor = None) -> None:
        self.preprocessor = preprocessor
        self._root = _root
        if self.preprocessor:
            content = self.preprocessor.preprocess(content)
        super().__init__(content)


def construct_include(loader: YamlIncludesLoader, node: yaml.Node) -> Any:
    filename = IncludePaths.locate(
        current_dir=loader._root, filename=loader.construct_scalar(node))
    with open(filename, 'r') as f:
        loader = YamlIncludesLoader(content=f.read(),
                                    _root=path.dirname(filename),
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
            obj["_root"] = path.dirname(path.normpath(filename))
    return obj


yaml.add_constructor('!include', construct_include, YamlIncludesLoader)

from os import path


class IncludePaths():
    '''class holding the list of directories to be searched when looking for a file'''
    paths = []

    @staticmethod
    def add(path: str):
        IncludePaths.paths.append(path)

    @staticmethod
    def locate(filename: str, current_dir: str = None) -> str:
        if path.isabs(filename):
            return filename
        l = [current_dir] if current_dir else []
        if IncludePaths.paths:
            l.extend(IncludePaths.paths)
        for d in l:
            p = path.join(d, filename)
            if path.exists(p):
                return p
        return None

    @staticmethod
    def locateall(filename: str, current_dir: str = None) -> str:
        result = []
        if path.isabs(filename):
            return filename
        l = [current_dir] if current_dir else []
        if IncludePaths.paths:
            l.extend(IncludePaths.paths)
        for d in l:
            p = path.join(d, filename)
            if path.exists(p):
                result.append(p)
        return result

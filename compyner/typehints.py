# TYPE HINTS for comPYner specific functions


class Module(dict):
    """
    Represents a comPYned module.
    """

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class ComPYnerBuildTools:
    """
    Tools to substitute code at compile time
    """

    @staticmethod
    def get_modules_path_glob(glob: str, /) -> list[Module]:
        """
        Return all modules whose path matches the given glob.
        """

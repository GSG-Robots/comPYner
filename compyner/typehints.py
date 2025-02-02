class ComPYnerBuildTools:
    """
    Tools to substitute code at compile time
    """

    @staticmethod
    def get_modules_path_glob(glob: str, /) -> list[dict]:
        """
        Return all modules whose path matches the given glob.
        """

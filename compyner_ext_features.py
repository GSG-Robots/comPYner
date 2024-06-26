class __EnterExit:
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...


__EnterExit_ = __EnterExit()


def wrp(func):
    return __EnterExit_


combine = None


def ingore_exception(exception):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception as e:
                print(f"Caught {exception.__name__}: {e}")

        return wrapper

    return decorator


def __main__(func):
    if func.__module__ == "__main__":
        return func()

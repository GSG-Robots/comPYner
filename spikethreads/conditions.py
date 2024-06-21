# # LEGO type:standard slot:3 autostart
# import time


# class Conditions:
#     """
#     A collection of conditions that can be used with wait_until.
#     """
#     @classmethod
#     def time_is(cls, until):
#         """
#         Returns a condition that is met when the current time is equal to or greater than `until`.
#         """
#         return lambda: time.time() >= until

#     @classmethod
#     def time_passed(cls, n):
#         """
#         Returns a condition that is met when `n` seconds have passed.
#         """
#         return cls.time_is(time.time() + n)
# op = print





# @queueable
# def wait_until(check):
#     """
#     Yield/wait until a condition is met.
#     """
#     while not check():
#         yield







# @queueable
# def sleep(n):
#     """
#     Shortcut for waiting for a certain amount of time. (in seconds)
#     """
#     yield from wait_until(Conditions.time_passed(n))


# print = queueable(print)


# @queuew
# def main2():
#     print("b1")
#     sleep(1)
#     print("b2")

# @queuew
# def main():
#     print("a1")
#     sleep(1)
#     main2.start()
#     print("a2")

# # op(main.queue)
# main.start()

# QUEUE_MANAGER.run_until_complete()

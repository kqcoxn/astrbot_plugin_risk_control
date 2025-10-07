import time


class Timer:
    def __init__(self):
        self.start_time = time.time()

    def end(self):
        """
        :return: 运行时间
        """
        return time.time() - self.start_time

import time


class ProfileLog:
    def __init__(self, logger, name=""):
        self.name = name
        self.logger = logger

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, type, value, traceback):
        self.t = time.time() - self.start
        self.logger.info(self.name + " time: %f" % self.t)

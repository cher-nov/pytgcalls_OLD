#!/usr/bin/env python3

import _libtgvoip

from .libtgvoip import *


class AudioDataCallback(AudioDataDirectorSWIG):
    def __init__(self, read_callable, write_callable):
        self.read_callable = read_callable
        self.write_callable = write_callable
        super().__init__()

    def read(self, size):
        # TODO: Does this leaks memory? Or use-after-free? Should we INCREF?
        return self.read_callable(size)

    def write(self, buffer):
        self.write_callable(buffer)

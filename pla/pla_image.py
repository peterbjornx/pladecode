from collections import namedtuple
from enum import Enum
import numpy
import cv2 as cv

class ChannelMode(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    LUMINOSITY = 3

class pla_image:

    def __init__( self, pixels, bgr=False):
        if not bgr:
            self.pixels = cv.cvtColor(pixels,cv.COLOR_RGB2BGR)
        else:
            self.pixels = pixels
        self.select_channel(ChannelMode.LUMINOSITY)

    def select_channel( self, mode ):
        self.channel_mode = mode
        if self.channel_mode == ChannelMode.LUMINOSITY:
            self.mono = cv.cvtColor( self.pixels, cv.COLOR_BGR2GRAY )
        elif self.channel_mode == ChannelMode.RED:
            self.mono = self.pixels[::,::,2]
        elif self.channel_mode == ChannelMode.GREEN:
            self.mono = self.pixels[::,::,1]
        elif self.channel_mode == ChannelMode.BLUE:
            self.mono = self.pixels[::,::,0]
        else:
            raise IndexError

    def getvalue(self, coord):
        return self.pixels[coord.x,coord.y]

    def to_rgb(self):
        return cv.cvtColor( self.pixels, cv.COLOR_BGR2RGB )

    def mono_to_bgr(self):
        return cv.cvtColor( self.mono, cv.COLOR_GRAY2BGR )

    def width(self):
        return numpy.shape(self.pixels)[1]

    def height(self):
        return numpy.shape(self.pixels)[0]
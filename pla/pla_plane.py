import numpy
import cv2 as  cv

from pla import pla_image, pla_config, pla
from pla.pla_group import pla_group

class pla_plane:
    pla = ... #type pla.pla
    image = ...  # type: pla_image.pla_image

    def __init__(self, pla, name):
        self.pla = pla
        self.name = name
        self.rows = 0
        self.cols = 0
        self.cells = numpy.zeros( (self.rows,self.cols) )
        self.groups = []
        self.region_base = numpy.array([0,0])
        self.region_size = numpy.array([10,10])

    def set_region(self, base, size):
        self.region_base = base
        self.region_size = size

    def set_region_base(self, base):
        self.region_base = base

    def set_region_size(self, size):
        self.region_size = size

    def set_size(self, rows, cols):
        oldcells = self.cells
        if self.rows <= rows and self.cols <= cols:
            self.cells = numpy.zeros( (rows, cols) )
            self.cells[0:self.rows,0:self.cols] = oldcells
        else:
            self.cells = oldcells[0:rows,0:cols]
        self.rows = rows
        self.cols = cols

    def add_group(self):
        g = pla_group(self, "Group %i"%len(self.groups))
        self.groups.append(g)
        return g

    def compute(self):
        for g in self.groups:
            g.compute()

    def overlay(self, target, highlight=None,**kwargs):
        if highlight == self:
            col = pla_config.sel_colour
        else:
            col = pla_config.grp_colour
        tl = self.region_base
        br = tl + self.region_size
        cv.rectangle(target,tuple(tl),tuple(br),col)

    def render(self, mono=False, highlight=None, **kwargs ):
        target = None
        if mono:
            target = self.pla.image.mono_to_bgr()
        else:
            target = self.pla.image.pixels
        ishl = highlight == self
        region_end = self.region_base + self.region_size
        target = numpy.copy(target[self.region_base[1]:region_end[1], self.region_base[0]:region_end[0]])
        for g in self.groups:
            g.render(target, offset=-self.region_base, highlight=highlight, **kwargs)
        return pla_image.pla_image(target, bgr=True)

    def base_coord(self):
        return self.region_base

    def children(self):
        return self.groups

    def parent(self):
        return self.pla

    def serialize(self):
        dict = {}
        dict["name"] = self.name
        dict["rows"] = self.rows
        dict["cols"] = self.cols
        dict["cells"] = self.cells.tolist()
        groups = []
        for v in self.groups:
            groups.append(v.serialize())
        dict["groups"] = groups
        dict["region_base"] = self.region_base.tolist()
        dict["region_size"] = self.region_size.tolist()
        return dict

    def _deserialize(self, dict):
        self.rows = dict["rows"]
        self.cols = dict["cols"]
        self.cells = numpy.array(dict["cells"])
        groups = dict["groups"]
        for v in groups:
            self.groups.append(pla_group.deserialize(self,v))
        self.region_base = numpy.array(dict["region_base"])
        self.region_size = numpy.array(dict["region_size"])

    @classmethod
    def deserialize(cls, pla, dict):
        o = pla_plane(pla, dict["name"])
        o._deserialize(dict)
        return o
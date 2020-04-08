import cv2 as cv
import numpy

from pla import pla_plane
from pla.pla_image import pla_image


class pla:
    image = ...  # type: pla_image
    planes = []

    def __init__(self, name, path):
        self.name = name
        self.img_path = path
        self.load_img()
        self.serialize_path = None

    def load_img(self):
        self.image = pla_image( cv.imread(str(self.img_path), cv.IMREAD_COLOR), bgr=True )

    def render(self, mono=False, highlight=None, **kwargs ):
        target = None
        if mono:
            target = self.image.mono_to_bgr()
        else:
            target = self.image.pixels
        target = numpy.copy(target)
        for p in self.planes:
            p.overlay(target, highlight=highlight, **kwargs)
        return pla_image(target, bgr=True)

    def children(self):
        return self.planes

    def add_plane(self):
        g = pla_plane.pla_plane(self, "Plane %i"%len(self.planes))
        self.planes.append(g)
        return g

    def parent(self):
        return None

    def base_coord(self):
        return numpy.array([0,0])

    def serialize(self):
        dict = {}
        dict["name"] = self.name
        dict["image"] = self.img_path
        p = []
        for v in self.planes:
            p.append(v.serialize())
        dict["planes"] = p
        return dict

    def _deserialize(self,dict):
        self.planes = []
        p = dict["planes"]
        for v in p:
            self.planes.append(pla_plane.pla_plane.deserialize(self,v))

    @classmethod
    def deserialize(cls, dict):
        p = pla(dict["name"],dict["image"])
        p._deserialize(dict)
        return p

    def get_render_item(self):
        return self

    def plane_report(self):
        out = "Plane report for "+self.name+"\n\n"
        for p in self.planes:
            out += p.cell_report()
        return out
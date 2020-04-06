import numpy
import cv2 as cv
import matplotlib.pyplot as plt
from pla import pla_config, pla_plane


class pla_group:

    plane = ...  # type: pla_plane

    def __init__(self, plane, name):
        self.name = name
        self.plane = plane
        self.horizontal = False
        self.row_start   = 0
        self.row_count   = 1
        self.row_height  = 5.0
        self.col_start   = 0
        self.col_count   = 1
        self.col_width   = 5.0
        self.crop_top    = 0
        self.crop_bottom = 0
        self.crop_left   = 0
        self.crop_right  = 0
        self.region_base = numpy.array([0, 0])
        self.update_cell_boxes()

    def base_coord(self):
        return self.region_base

    def set_region_base(self, base):
        self.region_base = base
        self.update_cell_boxes()

    def set_crop(self, l, t, r, b):
        self.crop_top = t
        self.crop_left = l
        self.crop_bottom = b
        self.crop_right = r
        self.update_cell_boxes()

    def set_size(self, rows, cols):
        self.row_count = rows
        self.col_count = cols
        self.update_cell_boxes()

    def set_start(self, rows, cols):
        self.row_start = rows
        self.col_start = cols

    def set_cell_size(self, width, height):
        self.row_height = height
        self.col_width = width
        self.update_cell_boxes()

    def set_orientation(self,val):
        self.horizontal = val
        self.do_classify()

    def update_cell_boxes(self):
        self.img_cells = numpy.zeros((self.row_count,self.col_count))
        self.row_top     = numpy.floor(self.region_base[1] + numpy.arange( 0, self.row_count ) * self.row_height).astype("int")
        self.row_bottom  = numpy.ceil(self.row_top + self.row_height).astype("int")
        self.cell_top    = self.row_top + self.crop_top
        self.cell_bottom = self.row_bottom - self.crop_bottom
        self.col_left    = numpy.floor(self.region_base[0] + numpy.arange( 0, self.col_count ) * self.col_width).astype("int")
        self.col_right   = numpy.ceil(self.col_left + numpy.ceil(self.col_width)).astype("int")
        self.cell_left   = self.col_left + self.crop_left
        self.cell_right  = self.col_right - self.crop_right
        self.cell_x  = ((self.cell_left + self.cell_right) / 2).astype("int")
        self.cell_y  = ((self.cell_top + self.cell_bottom) / 2).astype("int")
        self.region_size = numpy.array([int(self.col_width * self.col_count), int(self.row_height * self.row_count)])
        self.do_classify()

    def render(self, target, offset, highlight, boxes=True, values=True, **kwargs):
        if highlight == self:
            col = pla_config.sel_colour
        else:
            col = pla_config.grp_colour
        tl = self.region_base + offset
        br = tl + self.region_size
        cv.rectangle(target,tuple(tl),tuple(br),col)
        cv.circle(target,tuple(tl), 4, pla_config.grp_colour)
        if boxes:
            for i in range(0, self.row_count):
                for j in range(0, self.col_count):
                    tl = (self.cell_left[j] + offset[0], self.cell_top[i] + offset[1])
                    br = (self.cell_right[j] + offset[0], self.cell_bottom[i] + offset[1])
                    cv.rectangle(target, tuple(tl), tuple(br), pla_config.box_colour)
        if values:
            for i in range(0, self.row_count):
                for j in range(0, self.col_count):
                    tl = (self.cell_left[j] + offset[0], self.cell_bottom[i] + offset[1])
                    text="%i"%self.img_cells[i,j]
                    cv.putText( target, text, tl, cv.FONT_HERSHEY_SIMPLEX, pla_config.font_sz, pla_config.dat_colour, thickness=1)

    def get_cell_coord(self,x,y):
        x -= self.region_base[0]
        y -= self.region_base[1]
        x //= self.col_width
        y //= self.row_height
        if x <0 or x >= self.col_count or y < 0 or y >= self.row_count:
            return None
        return (int(x),int(y))

    def get_cell(self, r, c):
        return self.plane.pla.image.mono[self.cell_top[r]:self.cell_bottom[r],self.cell_left[c]:self.cell_right[c]]

    def do_classify(self):
        for i in range(0, self.row_count):
            for j in range(0, self.col_count):
                self.img_cells[i,j] = self.classify_a(self.get_cell(i,j))

    def classify_dbg(self, r, c, ax):
        c = self.get_cell(r,c)
        if self.horizontal:
            c = numpy.mean(c, axis=0)
        else:
            c = numpy.mean(c, axis=1)

        n = c / numpy.max(c)
        ax.set_ylim(0,1.)
        ax.plot(numpy.arange(0,len(n)),n)

    def classify_a(self,c):
        if self.horizontal:
            c = numpy.mean(c, axis=0)
        else:
            c = numpy.mean(c, axis=1)
        n = c / numpy.max(c)
        lm = numpy.argmin(n[:len(n) // 2])
        rm = len(n) - numpy.argmin(n[:len(n) // 2:-1]) - 1
        la = n[lm]
        ra = n[rm]
        # print lm, la, rm, ra, rm-lm
        if la > 0.75:
            lm = None
        else:
            lm /= len(n) * 1.
        if ra > 0.75:
            rm = None
        else:
            rm /= len(n) * 1.
        if lm is not None and lm > 0.35: lm = None
        if rm is not None and rm < 0.65: rm = None
        if (lm is None) and (rm is None):
            return 3
        if lm is None:
            return 2
        if rm is None:
            return 1
        return 0

    def children(self):
        return None

    def parent(self):
        return self.plane

    def serialize(self):
        dict = {}
        dict["name"] = self.name
        dict["row_start"] = self.row_start
        dict["row_count"] = self.row_count
        dict["row_height"] = self.row_height
        dict["col_start"] = self.col_start
        dict["col_count"] = self.col_count
        dict["col_width"] = self.col_width
        dict["crop"] = [self.crop_left, self.crop_top, self.crop_right, self.crop_bottom]
        dict["base"] = self.region_base.tolist()
        dict["horiz"] = self.horizontal
        return dict

    def _deserialize(self, dict):
        self.region_base = numpy.array(dict["base"])
        self.row_start = dict["row_start"]
        self.row_count = dict["row_count"]
        self.row_height = dict["row_height"]
        self.col_start = dict["col_start"]
        self.col_count = dict["col_count"]
        self.col_width = dict["col_width"]
        if "horiz" in dict:
            self.horizontal = dict["horiz"]
        self.crop_left,self.crop_top,self.crop_right,self.crop_bottom = dict["crop"]
        self.update_cell_boxes()

    @classmethod
    def deserialize(cls, plane, dict):
        o = pla_group(plane, dict["name"])
        o._deserialize(dict)
        return o
import numpy
import cv2 as cv
import matplotlib.pyplot as plt
from pla import pla_config, pla_plane
import time

class pla_group:

    plane = ...  # type: pla_plane

    def __init__(self, plane, name):
        self.name = name
        self.plane = plane
        self.horizontal = False
        self.bit_horiz = False
        self.bit_rows = 0
        self.bit_cols = 0
        self.class_count = 4
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
        self.bittrim_start = 0
        self.bittrim_end = 0
        self.class_refs = None
        self.region_base = numpy.array([0, 0])
        self.man_cells   = None
        self.templated_refs = False
        self.trimmed_bits = None
        self.cell_grid_valid = False
        self.cell_pos_valid = False
        self.cell_value_valid = False
        self.bit_grid_valid = False
        self.bit_value_valid = False
        self.reference_valid = False

    def base_coord(self):
        return self.region_base

    def set_region_base(self, base):
        self.region_base = base
        self.invalidate_cell_pos()

    def get_region_base(self):
        return self.region_base

    def get_region_size(self):
        self.ensure_cell_pos()
        return self.region_size

    def set_crop(self, l, t, r, b):
        self.crop_top = t
        self.crop_left = l
        self.crop_bottom = b
        self.crop_right = r
        self.invalidate_cell_pos()

    def set_size(self, rows, cols):
        self.row_count = rows
        self.col_count = cols
        self.invalidate_cell_grid()
        self.invalidate_bit_grid()

    def set_start(self, rows, cols):
        self.row_start = rows
        self.col_start = cols #TODO: Invalidate PLA plane?

    def set_cell_size(self, width, height):
        self.row_height = height
        self.col_width = width
        self.invalidate_cell_pos()

    def set_orientation(self,val):
        self.horizontal = val
        self.invalidate_cell_values()

    def set_bit_orientation(self,val):
        self.bit_horiz = val
        self.invalidate_bit_grid()

    def set_bit_trim(self,start,end):
        self.bittrim_start = start
        self.bittrim_end = end
        self.invalidate_bit_grid()

    def set_class_count(self,value):
        self.class_count = value
        self.invalidate_cell_values()

    def get_class_bits(self):
        return int(numpy.round(numpy.log2(self.class_count)))

    def get_bit_size(self):
        self.ensure_bit_grid()
        return (self.bit_rows, self.bit_cols)

    def get_data_bits(self):
        self.ensure_bit_values()
        return self.trimmed_bits

    def ensure_cell_grid(self):
        if self.cell_grid_valid:
            return
        self.auto_cells  = numpy.zeros((self.row_count, self.col_count),dtype="int")
        if self.man_cells is None or numpy.shape(self.man_cells) != (self.row_count, self.col_count): #TODO: Lossless resize
            self.man_cells  = numpy.zeros((self.row_count, self.col_count),dtype="int")- 1
            self.exc_cells  = numpy.zeros((self.row_count, self.col_count),dtype="int")
        self.cell_grid_valid = True

    def ensure_cell_pos(self):
        if self.cell_pos_valid:
            return
        self.row_top     = numpy.floor(self.region_base[1] + numpy.arange( 0, self.row_count ) * self.row_height).astype("int")
        self.col_left    = numpy.floor(self.region_base[0] + numpy.arange( 0, self.col_count ) * self.col_width).astype("int")
        self.row_bottom  = numpy.ceil(self.row_top  + self.row_height).astype("int")
        self.col_right   = numpy.ceil(self.col_left + numpy.ceil(self.col_width)).astype("int")
        self.cell_left   = self.col_left   + self.crop_left
        self.cell_top    = self.row_top    + self.crop_top
        self.cell_right  = self.col_right  - self.crop_right
        self.cell_bottom = self.row_bottom - self.crop_bottom
        self.cell_x      = ((self.cell_left + self.cell_right ) / 2).astype("int")
        self.cell_y      = ((self.cell_top  + self.cell_bottom) / 2).astype("int")
        self.cell_width  = self.cell_right[0] - self.cell_left[0]
        self.cell_height = self.cell_bottom[0] - self.cell_top[0]
        self.region_size = numpy.array([int(self.col_width * self.col_count), int(self.row_height * self.row_count)])
        self.cell_pos_valid = True

    def ensure_bit_grid(self):
        if self.bit_grid_valid:
            return
        self.bit_rows = self.row_count
        self.bit_cols = self.col_count
        if self.bit_horiz:
            self.bit_cols *= self.get_class_bits()
        else:
            self.bit_rows *= self.get_class_bits()
        self.auto_bits = numpy.zeros((self.bit_rows,self.bit_cols),dtype="int")
        self.bit_grid_valid  = True
        self.bit_value_valid = True

    def invalidate_cell_grid(self):
        self.cell_grid_valid = False
        self.invalidate_cell_pos()
        self.invalidate_bit_grid()
        self.invalidate_cell_values()

    def invalidate_cell_pos(self):
        self.cell_grid_pos = False
        self.invalidate_cell_values()

    def invalidate_cell_values(self):
        self.cell_value_valid = False
        self.invalidate_bit_values()

    def invalidate_bit_grid(self):
        self.bit_grid_valid = False
        self.invalidate_bit_values()

    def invalidate_bit_values(self):
        self.bit_value_valid = False
        self.plane.invalidate_cells()

    def invalidate_reference(self):
        self.reference_valid = False
        if not self.templated_refs:
            self.invalidate_cell_values()

    def is_cell_ref(self, r, c):
        return self.is_cell_man(r,c) and not self.is_cell_exc(r,c)

    def is_cell_man(self, r, c):
        self.ensure_cell_grid()
        v = self.man_cells[r,c]
        return v != -1

    def is_cell_exc(self, r, c):
        self.ensure_cell_grid()
        v = self.exc_cells[r,c]
        return v != 0

    def get_cell_class(self, r, c):
        self.ensure_cell_grid()
        v = self.man_cells[r,c]
        if v == -1:
            self.ensure_cell_values()
            v = self.auto_cells[r,c]
        return v

    def reset_cell_class(self, r, c):
        if self.is_cell_ref(r,c):
            self.invalidate_reference()
        self.man_cells[r,c] = -1
        self.invalidate_bit_values()

    def set_cell_class(self, r, c, v):
        self.man_cells[r, c] = v
        if (v != self.man_cells[r, c]) and not self.is_cell_exc(r,c):
            self.invalidate_reference()
        self.invalidate_bit_values()

    def toggle_cell_exc(self, r, c):
        self.exc_cells[r, c] = 1 - self.exc_cells[r, c]
        if self.is_cell_man(r,c):
            self.invalidate_reference()

    # Image utility methods

    def get_cell_dim(self):
        self.ensure_cell_pos()
        if self.horizontal:
            return self.cell_width
        else:
            return self.cell_height

    def get_cell_coord(self,x,y):
        self.ensure_cell_pos()
        x -= self.region_base[0]
        y -= self.region_base[1]
        x //= self.col_width
        y //= self.row_height
        if x <0 or x >= self.col_count or y < 0 or y >= self.row_count:
            return None
        return (int(x),int(y))

    def get_cell(self, r, c):
        self.ensure_cell_pos()
        return self.plane.pla.image.mono[self.cell_top[r]:self.cell_bottom[r],self.cell_left[c]:self.cell_right[c]]

    def get_cell_flattened(self, r, c):
        c = self.get_cell(r,c)
        if self.horizontal:
            c = numpy.mean(c, axis=0)
        else:
            c = numpy.mean(c, axis=1)
        n = c / numpy.max(c)
        return n

    # Reference generator methods

    def ensure_reference(self):
        if self.reference_valid:
            return
        if not self.templated_refs:
            self.ensure_cell_grid()
            n = [0]*self.class_count
            a = numpy.zeros((self.class_count,self.get_cell_dim()))
            for r in range(0, self.row_count):
                for c in range(0, self.col_count):
                    if not self.is_cell_ref(r,c):
                        continue
                    v = self.man_cells[r,c]
                    n[v] += 1
                    a[v, ::] += self.get_cell_flattened(r,c)
            if numpy.any(n == 0):
                return
            for v in range(0, self.class_count):
                a[v] /= n[v]
            self.class_refs = a
        self.reference_valid = True

    # Classifier methods

    def score(self, a, b):
        """

        :type a: numpy.ndarray
        :type b: numpy.ndarray
        """
        return numpy.sum((a-b)**2.0)


    def score_class(self,r,c,i):
        self.ensure_reference()
        a = self.get_cell_flattened(r,c)
        b = self.class_refs[i]
        return self.score(a,b)

    def classify_chisq(self,r,c):
        return numpy.argmin(numpy.array([self.score_class(r,c,i) for i in range(0,self.class_count)]))

    def ensure_cell_values(self):
        if self.cell_value_valid:
            return
        if self.class_refs is None:
            return #TODO: Warn/error?
        print(self.name+" classify start")
        ts = time.time()
        try:
            for i in range(0, self.row_count):
                for j in range(0, self.col_count):
                    self.auto_cells[i, j] = self.classify_chisq(i, j)
        except:
            print("FOO!")
        print(self.name+" classify done: %f"%(time.time()-ts))
        self.cell_value_valid = True

    def ensure_bit_values(self):
        if self.bit_value_valid:
            return
        self.ensure_bit_grid()
        print(self.name+" do_binary")
        ts = time.time()
        bits = self.get_class_bits()
        for i in range(0, self.row_count):
            for j in range(0, self.col_count):
                v = self.get_cell_class(i,j)
                for k in range(0, bits):
                    b = ((v >> k) & 1) != 0
                    if self.bit_horiz:
                        self.auto_bits[i,j*bits+k] = b
                    else:
                        self.auto_bits[i*bits+k,j] = b
        if self.bit_horiz:
            bs = self.auto_bits[::,self.bittrim_start:self.bit_cols-self.bittrim_end]
        else:
            bs = self.auto_bits[self.bittrim_start:self.bit_rows-self.bittrim_end,::]
        self.trimmed_bits = bs
        print(self.name+" do_binary done: %f"%(time.time()-ts))
        self.bit_value_valid = True
    # Tree methods

    def children(self):
        return None

    def parent(self):
        return self.plane

    def get_render_item(self):
        return self.plane

    # IO methods

    def serialize(self, template_only=False):
        dict = {}
        if template_only:
            dict["template"] = True
        if not template_only:
            dict["name"] = self.name
        dict["row_start"] = self.row_start
        dict["row_count"] = self.row_count
        dict["row_height"] = self.row_height
        dict["col_start"] = self.col_start
        dict["col_count"] = self.col_count
        dict["col_width"] = self.col_width
        dict["crop"] = [self.crop_left, self.crop_top, self.crop_right, self.crop_bottom]
        if not template_only:
            dict["base"] = self.region_base.tolist()

        dict["bit_horiz"] = self.bit_horiz
        dict["bittrim_start"] = self.bittrim_start
        dict["bittrim_end"] = self.bittrim_end

        dict["horiz"] = self.horizontal
        dict["class_count"] = self.class_count
        dict["templated_refs"] = self.templated_refs

        # Reference
        self.ensure_reference()
        dict["class_refs"] = self.class_refs.tolist()
        # Cell grid
        self.ensure_cell_grid()
        if not template_only:
            dict["man_cells"] = self.man_cells.tolist()
            dict["exc_cells"] = self.exc_cells.tolist()
        return dict

    def _deserialize(self, dict,only_refs=False):
        template_only = "template" in dict
        if not template_only:
            self.name = dict["name"]
            self.region_base = numpy.array(dict["base"])
        self.row_start = dict["row_start"]
        self.row_count = dict["row_count"]
        self.row_height = dict["row_height"]
        self.col_start = dict["col_start"]
        self.col_count = dict["col_count"]
        self.col_width = dict["col_width"]
        if "bittrim_start" in dict:
            self.bittrim_start = dict["bittrim_start"]
            self.bittrim_end = dict["bittrim_end"]
        if "bit_horiz" in dict:
            self.bit_horiz = dict["bit_horiz"]
        if "horiz" in dict:
            self.horizontal = dict["horiz"]
        if "class_count" in dict:
            self.class_count = dict["class_count"]
        if "man_cells" in dict and not template_only:
            self.man_cells = numpy.array(dict["man_cells"])
        if "exc_cells" in dict and not template_only:
            self.exc_cells = numpy.array(dict["exc_cells"])
        if "templated_refs" in dict and not template_only:
            self.templated_refs = dict["templated_refs"]
        else:
            self.templated_refs = template_only
        if "class_refs" in dict:
            self.class_refs = numpy.array(dict["class_refs"])
        self.crop_left,self.crop_top,self.crop_right,self.crop_bottom = dict["crop"]

    @classmethod
    def deserialize(cls, plane, dict):
        o = pla_group(plane, dict["name"])
        o._deserialize(dict)
        return o

    # Template methods

    def to_template(self,name):
        dict =  self.serialize(template_only=True)
        dict["name"] = name
        return dict

    def load_template(self,tmp):
        self.man_cells = None
        self._deserialize(tmp)

    def load_template_refs(self,dict):
        if "class_refs" in dict:
            self.templated_refs = True
            self.class_refs = numpy.array(dict["class_refs"])
            self.class_count = dict["class_count"]
            self.invalidate_cell_values()
            return True
        return False

    # UI Methods

    def render(self, target, offset, highlight, boxes=True, values=True, **kwargs):
        self.ensure_cell_pos()
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
                    text="%i"%self.get_cell_class(i, j)
                    if not self.is_cell_man(i,j):
                        col = pla_config.dat_colour
                    elif self.is_cell_exc(i,j):
                        col = pla_config.exc_colour
                    else:
                        col = pla_config.man_colour
                    cv.putText( target, text, tl, cv.FONT_HERSHEY_SIMPLEX, pla_config.font_sz, col , thickness=1)

    def plot_ref(self, ax):
        self.ensure_reference()
        ax.set_ylim(0,1.)
        for v in range(0, self.class_count):
            ax.plot(numpy.arange(0,len(self.class_refs[v])),self.class_refs[v],label="Class %i"%v)
        ax.legend(loc="lower right")

    def class_score_info(self,r,c):
        n = ""
        for i in range(0,self.class_count):
            n += " %f"%self.score_class(r,c,i)
        return n

    def classify_dbg(self, r, c, ax):
        n = self.get_cell_flattened(r,c)
        ax.set_ylim(0,1.)
        ax.plot(numpy.arange(0,len(n)),n,label="Row %i Col %i %s"%(r,c,self.class_score_info(r,c)))
        ax.legend(loc="lower right")
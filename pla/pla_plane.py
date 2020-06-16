import numpy
import cv2 as  cv

from pla import pla_image, pla_config, pla
from pla.pla_group import pla_group

class pla_plane:
    pla = ... #type pla.pla
    image = ...  # type: pla_image.pla_image

    MINTERM_NOCARE = 0
    MINTERM_LOW    = 1
    MINTERM_HIGH   = 2

    def __init__(self, pla, name):
        self.pla = pla
        self.name = name
        self.rows = 0
        self.cols = 0
        self.cells = numpy.zeros( (self.rows,self.cols) )
        self.groups = []
        self.region_base = numpy.array([0,0])
        self.region_size = numpy.array([10,10])
        self.cells_overlap = False
        self.cells_unset = True
        self.unset_cells = self.cells
        self.input_count = 0
        self.output_count = 0
        self.minterms = None
        self.minterms_conflict = False
        self.is_and = False
        self.horiz_inputs = False
        self.input_pol = False
        self.minterms_valid = False
        self.cell_values_valid = False
        self.outputs_valid = False
        self.int_offset = 0

    def invalidate_cells(self):
        self.cell_values_valid = False
        self.invalidate_minterms()
        self.invalidate_outputs()

    def invalidate_minterms(self):
        self.minterms_valid = False

    def invalidate_outputs(self):
        self.outputs_valid = False

    def ensure_minterms(self):
        if not self.is_and:
            return
        if self.minterms_valid:
            return
        self.ensure_cells()
        c = self.cells
        if self.horiz_inputs:
            c = c.transpose()
        s = numpy.shape(c)
        self.input_count  = s[0] // 2
        self.output_count = s[1]
        self.minterms = numpy.zeros((self.output_count, self.input_count), dtype="int")
        if self.input_pol:
            r1 = pla_plane.MINTERM_LOW
            r0 = pla_plane.MINTERM_HIGH
        else:
            r0 = pla_plane.MINTERM_LOW
            r1 = pla_plane.MINTERM_HIGH
        for i in range(0, self.input_count):
            self.minterms[::,i] = r0 * c[i*2,::] + r1 * c[i*2+1,::]
        self.minterms_conflict = numpy.amax(self.minterms,axis=(0,1)) > pla_plane.MINTERM_HIGH
        self.minterms_valid = True
        #print("enum")
        #self.enumerate_inputs()
        #print("strip")
        #self.strip_underspecified()
        #print("done")

    def ensure_outputs(self):
        if self.is_and:
            return
        if self.outputs_valid:
            return
        self.ensure_cells()
        c = self.cells
        if self.horiz_inputs:
            c = c.transpose()
        self.outputs = c
        self.input_count = numpy.shape(c)[0]
        self.output_count = numpy.shape(c)[1]
        self.outputs_valid = True

    def generate_c_orplane(self):
        res = ""
        name = self.pla.name+"_"+self.name
        self.ensure_outputs()
        grsz = 32
        grc = (self.output_count + grsz - 1) // grsz
        arr = "uint32_t %s[%2i][%2i] = "%(name, self.input_count, grc)
        arrb = []
        for i in self.outputs:
            arra = []
            for j in range(0, grc):
                gnp = i[j*grsz:(j+1)*grsz]
                gi = pla_plane.np_to_int(gnp)
                arra.append("0x%08X"%gi)
            arra = "{ "+", ".join(arra) + " }"
            arrb.append(arra)
        arrb = "{\n\t" +",\n\t".join(arrb) +" };\n"
        res = """
%s
#define %s_size    (%i)
#define %s_bits    (%i)
#define %s_offset  (%i)
#define %s_groups  (%i)
        """%( arr+arrb,
              name, self.input_count,
              name, self.output_count,
              name, self.int_offset,
              name, grc)
        return res

    def generate_c_andplane(self):
        res = ""
        name = self.pla.name+"_"+self.name
        self.ensure_minterms()
        if self.input_count > 31:
            return "Not supported for input size > int32"
        mask = ""
        val = ""
        j = 0
        for ii,i in enumerate(self.minterms):
            mask += "0x%08X"%pla_plane.int_minterm(i,[1,2])
            val  += "0x%08X"%pla_plane.int_minterm(i,[2])
            if ii == self.output_count - 1:
                pass
            elif (ii % 8) == 7:
                mask += ",\n\t"
                val  += ",\n\t"
            else:
                mask += ", "
                val  += ", "
        res = """
#define  %s_offset       (%i)
#define  %s_size         (%i)
uint32_t %s_mask[%2i] = {%s};
uint32_t %s_val [%2i] = {%s};
#define  %s_test(v,i)    ((v & %s_mask[i]) == %s_val[i]) 
        """%(name,self.int_offset,
             name,self.output_count,
             name,self.output_count,mask,
             name,self.output_count,val,
             name,name,name)
        return res

    def generate_c(self):
        if self.is_and:
            return self.generate_c_andplane()
        else:
            return self.generate_c_orplane()

    def set_input_orientation(self, val):
        self.horiz_inputs = val
        self.invalidate_minterms()
        self.invalidate_outputs()

    def set_and_plane(self,val):
        self.is_and = val
        self.invalidate_minterms()

    def set_input_pol(self,val):
        self.input_pol = val
        self.invalidate_minterms()

    def set_region(self, base, size):
        self.region_base = base
        self.region_size = size

    def set_region_base(self, base):
        self.region_base = base

    def set_region_size(self, size):
        self.region_size = size

    def get_region_base(self):
        return self.region_base

    def get_region_size(self):
        return self.region_size

    def base_coord(self):
        return self.region_base

    def set_size(self, rows, cols):
        oldcells = self.cells
        if self.rows <= rows and self.cols <= cols:
            self.cells = numpy.zeros( (rows, cols) )
            self.cells[0:self.rows,0:self.cols] = oldcells
        else:
            self.cells = oldcells[0:rows,0:cols]
        self.rows = rows
        self.cols = cols
        self.invalidate_cells()

    def add_group(self):
        g = pla_group(self, "Group %i"%len(self.groups))
        self.groups.append(g)
        return g

    def overlay(self, target, highlight=None,**kwargs):
        if highlight == self:
            col = pla_config.sel_colour
        else:
            col = pla_config.grp_colour
        tl = self.region_base
        br = tl + self.region_size
        cv.rectangle(target,tuple(tl),tuple(br),col)

    def ensure_cells(self):
        if self.cell_values_valid or self.rows <= 0 or self.cols <= 0:
            return
        c = numpy.zeros_like(self.cells)
        for g in self.groups:
            rs = g.row_start
            cs = g.col_start
            b  = g.get_data_bits()
            if b is None:
                continue
            bs = numpy.shape(b)
            re = rs + bs[0]
            ce = cs + bs[1]
            try:
                self.cells[rs:re,cs:ce] = b
                c[rs:re,cs:ce] += 1
            except:
                pass
        self.unset_cells = c
        self.cells_overlap = numpy.amax(c,axis=(0,1)) >= 2
        self.cells_unset   = numpy.amin(c,axis=(0,1)) < 1
        self.cell_values_valid = True

    @classmethod
    def np_to_int(cls, a):
        i = 0
        for j,v in enumerate(a):
            if v:
                i |= 1 << j
        return i

    @classmethod
    def int_minterm(cls, mt, vm1):
        i = 0
        for j,v in enumerate(mt[::-1]):
            if v in vm1:
                i |= 1 << j
        return i

    @classmethod
    def str_minterm(cls, mt):
        s = ""
        for i in mt:
            if i == pla_plane.MINTERM_NOCARE:
                s+=" "
            elif i == pla_plane.MINTERM_HIGH:
                s+="1"
            elif i == pla_plane.MINTERM_LOW:
                s+="0"
            else:
                s+="X"
        i = 0
        for j,v in enumerate(mt[::-1]):
            if v==2:
                i |= 1 << j
        bl = int(numpy.ceil(len(mt) /4))
        s+=(" 0x%%0%ix"%bl)%i
        return s

    @classmethod
    def is_compat(cls,a,b):
        return numpy.all((a|b) < 3)

    def enumerate_inputs(self, w = None, m = None):
        if w is None:
            w = numpy.zeros(self.input_count,dtype="int")
            self.input_list = set()
        if m is None:
            m = numpy.zeros(self.input_count,dtype="int")
        if not pla_plane.is_compat(w,m):
            return
        w = w | m
        if tuple(w.tolist()) in self.input_list:
            return
        self.input_list.add(tuple(w.tolist()))
        for i in range(0, self.output_count):
            self.enumerate_inputs(w,self.minterms[i,::])

    @classmethod
    def is_subset(cls, a, b):
        return pla_plane.is_compat(a,b) and numpy.all((a-b) <= 0)

    def strip_underspecified(self):
        print("strip underspec")
        f = True
        us = set()
        while f:
            f = False
            l = []
            print(len(self.input_list))
            for ii in self.input_list:
                ia = numpy.array(ii)
                for j in self.input_list:
                    if ii == j:
                        continue
                    ja = numpy.array(j)
                    if pla_plane.is_subset(ia,ja):
                        f = True
                        l.append((ia,ja,ii))
                        break
            for t in l:
                ia = t[0]
                ja = t[1]
                ii = t[2]
                self.input_list.remove(ii)
                us.add(ii)
                da = ja - ia
                m = da == pla_plane.MINTERM_HIGH
                ml = len(m[m])
                print(ml,ia)
                for i in range(0, ml):
                    va = numpy.copy(ia)
                    (va[m])[i] |= pla_plane.MINTERM_LOW
                    t = tuple(va.tolist())
                    if t not in us:
                        self.input_list.add(t)
                m = da == pla_plane.MINTERM_LOW
                ml = len(m[m])
                for i in range(0, ml):
                    va = numpy.copy(ia)
                    (va[m])[i] |= pla_plane.MINTERM_HIGH
                    t = tuple(va.tolist())
                    if t not in us:
                        self.input_list.add(t)

        pass

    def cell_report(self):
        self.ensure_cells()
        rep = self.name
        rep += "rows: %3i columns:%3i overlap:%i incomplete: %i\n"%\
              (self.rows,self.cols,int(self.cells_overlap),int(self.cells_unset))
        rep += "     "
        for j in range(0, self.cols):
            rep += "%i "%(j%10)
        rep+="\n"
        for i in range(0, self.rows):
            r = "%3i: "%i
            for j in range(0, self.cols):
                if self.cells[i,j]:
                    r += "1 "
                else:
                    r += "  "
            rep += r.rstrip() + "\n"
        rep+="\n"
        if self.is_and:
            self.ensure_minterms()
            rep+="minterms conflict:%i\n"%int(self.minterms_conflict)
            for i in range(0,self.output_count):
                rep+="%3i: %s\n"%(i,pla_plane.str_minterm(self.minterms[i,::]))
        rep += self.generate_c()
            #for i in self.input_list:
            #    rep+="ENN: %s\n"%(pla_plane.str_minterm(i))
        return rep

    def cell_dump(self):
        self.ensure_cells()
        rep = "#name:%s rows: %3i columns:%3i overlap:%i incomplete: %i\n"%\
              (self.name, self.rows,self.cols,int(self.cells_overlap),int(self.cells_unset))
        for i in range(0, self.rows):
            r = ""
            for j in range(0, self.cols):
                if self.cells[i,j]:
                    r += "1 "
                else:
                    r += "0 "
            rep += r.rstrip() + "\n"
        rep+="\n"
        return rep

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

    def children(self):
        return self.groups

    def parent(self):
        return self.pla

    def serialize(self):
        dict = {}
        dict["name"] = self.name
        dict["rows"] = self.rows
        dict["cols"] = self.cols
        self.ensure_cells()
        dict["cells"] = self.cells.tolist()
        groups = []
        for v in self.groups:
            groups.append(v.serialize())
        dict["groups"] = groups
        dict["region_base"] = self.region_base.tolist()
        dict["region_size"] = self.region_size.tolist()
        dict["is_and"] = self.is_and
        dict["horiz_inputs"] = self.horiz_inputs
        dict["input_pol"] = self.input_pol
        dict["int_offset"] = self.int_offset

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
        if "is_and" in dict:
            self.is_and = dict["is_and"]
            self.horiz_inputs = dict["horiz_inputs"]
            self.input_pol = dict["input_pol"]
        if "int_offset" in dict:
            self.int_offset = dict["int_offset"]

    @classmethod
    def deserialize(cls, pla, dict):
        o = pla_plane(pla, dict["name"])
        o._deserialize(dict)
        return o

    def get_render_item(self):
        return self
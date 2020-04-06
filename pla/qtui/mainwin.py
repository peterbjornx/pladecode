#! /usr/bin/env python3
import traceback
import pathlib
import json
import cv2 as cv
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
#from .about import RomparAboutDialog
#from .findhexdialog import FindHexDialog

# Parse the ui file once.
import sys, os.path
from PyQt5 import uic
from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import numpy
from PyQt5.QtWidgets import QLineEdit, QInputDialog, QAction, QMenu, QFileDialog, QVBoxLayout

from pla.pla import pla
from pla.pla_group import pla_group
from pla.pla_image import pla_image
from pla.pla_plane import pla_plane

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(thisdir) # Needed to load ui
MainUi, MainUiBase = uic.loadUiType(os.path.join(thisdir, 'main.ui'))
del sys.path[-1] # Remove the now unnecessary path entry

MODE_IDLE           = 0
MODE_CREATE_PLANE_1 = 1
MODE_CREATE_PLANE_2 = 2
MODE_CREATE_GROUP   = 3
MODE_PROBE_CELL     = 4
MODE_SET_CELL       = 5
MODE_RESET_CELL     = 6
MODE_EXC_CELL       = 7

class PlaDecMainWin(QtWidgets.QMainWindow):
    def __init__(self):
        super(PlaDecMainWin, self).__init__()
        self.ui = MainUi()
        self.ui.setupUi(self)

        # Create buffers to show Rompar image in UI.
        self.pixmapitem = QtWidgets.QGraphicsPixmapItem()
        self.scene = QtWidgets.QGraphicsScene()
        self.scene.addItem(self.pixmapitem)
        self.renderingItem = None
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)
        self.templateListModel = QStandardItemModel()
        self.ui.groupTemplateList.setModel(self.templateListModel)
        self.ui.groupTemplateList.selectionModel().selectionChanged.connect(self.on_groupTemplateList_selectionChanged)
        self.templateListModel.itemChanged.connect(self.on_groupTemplateList_itemChanged)
        self.model = QStandardItemModel()
        self.ui.projectTree.setModel(self.model)
        self.ui.projectTree.selectionModel().selectionChanged.connect(self.on_projectTree_selectionChanged)
        self.model.itemChanged.connect(self.on_projectTree_itemChanged)
        self.plalist = []
        self.load("entrypt.pla")
        self.mode = MODE_IDLE
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.ui.plotWidget)
        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.ui.plotWidget.setLayout(layout)
        self.group_templates = [{"name":"None","dontuse":True}]
        self.populateGroupTemplateList()
        self.currentGroupTemplate = None

    def populateTree(self, list=None, parent=None):
        if list is None:
            list = self.plalist
        if parent is None:
            self.model.clear()
            parent = self.model.invisibleRootItem()
        for i in list:
            item = QStandardItem(i.name)
            parent.appendRow(item)
            item.setData(i.name+"foo")
            ch = i.children()
            if ch is not None:
                self.populateTree(ch,item)
        self.ui.projectTree.expandAll()

    def populateGroupTemplateList(self):
        self.templateListModel.clear()
        parent = self.templateListModel.invisibleRootItem()
        for i in self.group_templates:
            item = QStandardItem(i["name"])
            parent.appendRow(item)

    def createGroupTemplate(self):
        if not isinstance(self.selectedItem,pla_group):
            self.showTempStatus("Error: To create a group template, select a group!")
            return
        self.group_templates.append(self.currentGroup.to_template("Template %i"%len(self.group_templates)))
        self.populateGroupTemplateList()

    def deleteGroupTemplate(self):
        if self.currentGroupTemplate is None:
            self.showTempStatus("Error: No template selected")
            return
        self.group_templates.remove(self.currentGroupTemplate)

    @QtCore.pyqtSlot()
    def on_createGroupTmplBtn_clicked(self):
        self.createGroupTemplate()

    @QtCore.pyqtSlot()
    def on_deleteGroupTmplBtn_clicked(self):
        self.deleteGroupTemplate()

    @QtCore.pyqtSlot("QItemSelection")
    def on_groupTemplateList_selectionChanged(self, selected):
        """

        :type selected: QItemSelection
        """
        a = selected.indexes()[0]  # type: QModelIndex
        item = self.group_templates[a.row()]
        print("select",item["name"])
        if "dontuse" in item:
            item = None
        self.currentGroupTemplate = item

    @QtCore.pyqtSlot("QStandardItem*")
    def on_groupTemplateList_itemChanged(self, item):
        pitem = self.group_templates[item.index().row()]
        nt = item["name"]
        if nt == pitem.name:
            return
        print("changed: "+pitem["name"]+" to "+nt)
        pitem["name"] = nt
        print("done")

    def view_plaimage(self, img):
        # Do initial draw
        self.qImg = QtGui.QImage( img.to_rgb(),
                                  img.width(),
                                  img.height(),
                                  3 * img.width(),
                                  QtGui.QImage.Format_RGB888)
        self.pixmapitem.setPixmap(QtGui.QPixmap(self.qImg))
        self.scene.setSceneRect(self.scene.itemsBoundingRect())

    def selectProjectItem(self,item):
        self.selectedItem = item
        if item is None:
            return
        if isinstance(item, pla):
            self.setCurrentPLA( item )
            self.setRenderingItem( item )
        elif isinstance(item, pla_plane):
            self.setCurrentPlane( item )
        elif isinstance(item, pla_group):
            self.setCurrentGroup( item )
        self.updateItemEdit()
        self.renderItem()

    def updateItemEdit(self):
        item = self.selectedItem
        self.ui.itemNameText.setText(item.name)
        region = False
        if isinstance(item, pla_plane):
            self.ui.planeGroupBox.setDisabled(False)
            self.ui.planeColsSpin.setValue(item.cols)
            self.ui.planeRowsSpin.setValue(item.rows)
            region = True
        else:
            self.ui.planeGroupBox.setDisabled(True)

        if isinstance(item, pla_group):
            self.ui.groupGroupBox.setDisabled(False)
            self.ui.regionSizeSpinW.setDisabled(True)
            self.ui.regionSizeSpinH.setDisabled(True)
            self.ui.groupStartColSpin.setValue(item.col_start)
            self.ui.groupStartRowSpin.setValue(item.row_start)
            self.ui.groupSizeColSpin.setValue(item.col_count)
            self.ui.groupSizeRowSpin.setValue(item.row_count)
            self.ui.cellSizeSpinW.setValue(item.col_width)
            self.ui.cellSizeSpinH.setValue(item.row_height)
            self.ui.cellCropSpinT.setValue(item.crop_top)
            self.ui.cellCropSpinB.setValue(item.crop_bottom)
            self.ui.cellCropSpinL.setValue(item.crop_left)
            self.ui.cellCropSpinR.setValue(item.crop_right)
            if item.horizontal:
                self.ui.cellOrientationCombo.setCurrentIndex(1)
            else:
                self.ui.cellOrientationCombo.setCurrentIndex(0)
            self.ui.classCountSpin.setValue(item.class_count)
            region = True
        else:
            self.ui.regionSizeSpinW.setDisabled(False)
            self.ui.regionSizeSpinH.setDisabled(False)
            self.ui.groupGroupBox.setDisabled(True)

        if region:
            self.ui.regionGroupBox.setEnabled(True)
            self.ui.regionBaseSpinX.setValue(item.region_base[0])
            self.ui.regionBaseSpinY.setValue(item.region_base[1])
            self.ui.regionSizeSpinW.setValue(item.region_size[0])
            self.ui.regionSizeSpinH.setValue(item.region_size[1])
        else:
            self.ui.regionGroupBox.setDisabled(True)

    def on_cellCropSpin_changed(self, l,t,r,b):
        if l == self.selectedItem.crop_left and t == self.selectedItem.crop_top and \
           r == self.selectedItem.crop_right and b == self.selectedItem.crop_bottom:
            return
        self.selectedItem.set_crop(l,t,r,b)
        self.updateItemEdit()
        self.renderItem()

    def on_cellSizeSpin_changed(self, w, h):
        if w == self.selectedItem.col_width and h == self.selectedItem.row_height:
            return
        self.selectedItem.set_cell_size(w, h)
        self.updateItemEdit()
        self.renderItem()

    def on_groupStartSpin_changed(self,rows,cols):
        if rows == self.selectedItem.row_start and cols == self.selectedItem.col_start:
            return
        self.selectedItem.set_start(rows,cols)
        self.updateItemEdit()
        self.renderItem()

    def on_groupSizeSpin_changed(self,rows,cols):
        if rows == self.selectedItem.row_count and cols == self.selectedItem.col_count:
            return
        self.selectedItem.set_size(rows,cols)
        self.updateItemEdit()
        self.renderItem()

    def on_planeSizeSpin_changed(self,rows,cols):
        if rows == self.selectedItem.rows and cols == self.selectedItem.cols:
            return
        self.selectedItem.set_size(rows,cols)
        self.updateItemEdit()
        self.renderItem()

    def on_regionBaseSpin_changed(self,val):
        if numpy.all(val == self.selectedItem.region_base):
            return
        self.selectedItem.set_region_base(val)
        self.updateItemEdit()
        self.renderItem()

    def on_regionSizeSpin_changed(self, val):
        if numpy.all(val == self.selectedItem.region_size):
            return
        self.selectedItem.set_region_size(val)
        self.updateItemEdit()
        self.renderItem()

    @QtCore.pyqtSlot("int")
    def on_regionBaseSpinX_valueChanged(self, value):
        val = numpy.array([
            value,
            self.selectedItem.region_base[1]
        ])
        self.on_regionBaseSpin_changed(val)

    @QtCore.pyqtSlot("int")
    def on_regionBaseSpinY_valueChanged(self, value):
        val = numpy.array([
            self.selectedItem.region_base[0],
            value
        ])
        self.on_regionBaseSpin_changed(val)

    @QtCore.pyqtSlot("int")
    def on_regionSizeSpinW_valueChanged(self, value):
        val = numpy.array([
            value,
            self.selectedItem.region_size[1]
        ])
        self.on_regionSizeSpin_changed(val)

    @QtCore.pyqtSlot("int")
    def on_regionSizeSpinH_valueChanged(self, value):
        val = numpy.array([
            self.selectedItem.region_size[0],
            value
        ])
        self.on_regionSizeSpin_changed(val)

    @QtCore.pyqtSlot("int")
    def on_regionSizeSpinW_valueChanged(self, value):
        val = numpy.array([
            value,
            self.selectedItem.region_size[1]
        ])
        self.on_regionSizeSpin_changed(val)

    @QtCore.pyqtSlot("int")
    def on_planeRowsSpin_valueChanged(self, value):
        self.on_planeSizeSpin_changed(value,self.selectedItem.cols)

    @QtCore.pyqtSlot("int")
    def on_planeColsSpin_valueChanged(self, value):
        self.on_planeSizeSpin_changed(self.selectedItem.rows,value)

    @QtCore.pyqtSlot("int")
    def on_groupSizeRowSpin_valueChanged(self, value):
        self.on_groupSizeSpin_changed(value,self.selectedItem.col_count)

    @QtCore.pyqtSlot("int")
    def on_groupSizeColSpin_valueChanged(self, value):
        self.on_groupSizeSpin_changed(self.selectedItem.row_count,value)

    @QtCore.pyqtSlot("int")
    def on_groupStartRowSpin_valueChanged(self, value):
        self.on_groupStartSpin_changed(value,self.selectedItem.col_start)

    @QtCore.pyqtSlot("int")
    def on_groupStartColSpin_valueChanged(self, value):
        self.on_groupStartSpin_changed(self.selectedItem.row_start,value)

    @QtCore.pyqtSlot("double")
    def on_cellSizeSpinW_valueChanged(self, value):
        self.on_cellSizeSpin_changed(value,self.selectedItem.row_height)

    @QtCore.pyqtSlot("double")
    def on_cellSizeSpinH_valueChanged(self, value):
        self.on_cellSizeSpin_changed(self.selectedItem.col_width,value)

    @QtCore.pyqtSlot("int")
    def on_cellCropSpinL_valueChanged(self, value):
        self.on_cellCropSpin_changed(value,self.selectedItem.crop_top,self.selectedItem.crop_right,self.selectedItem.crop_bottom)

    @QtCore.pyqtSlot("int")
    def on_cellCropSpinT_valueChanged(self, value):
        self.on_cellCropSpin_changed(self.selectedItem.crop_left,value,self.selectedItem.crop_right,self.selectedItem.crop_bottom)

    @QtCore.pyqtSlot("int")
    def on_cellCropSpinR_valueChanged(self, value):
        self.on_cellCropSpin_changed(self.selectedItem.crop_left,self.selectedItem.crop_top,value,self.selectedItem.crop_bottom)

    @QtCore.pyqtSlot("int")
    def on_cellCropSpinB_valueChanged(self, value):
        self.on_cellCropSpin_changed(self.selectedItem.crop_left,self.selectedItem.crop_top,self.selectedItem.crop_right,value)

    @QtCore.pyqtSlot("int")
    def on_classCountSpin_valueChanged(self, value):
        self.currentGroup.set_class_count( value )

    @QtCore.pyqtSlot("int")
    def on_cellOrientationCombo_currentIndexChanged(self,idx):
        self.currentGroup.set_orientation(idx == 1)
        self.renderItem()

    def setCurrentPLA(self,pla):
        self.currentPLA = pla
        self.currentPlane = None
        self.currentGroup = None

    def setCurrentPlane(self,plane):
        self.setCurrentPLA(plane.pla)
        self.currentPlane = plane
        self.currentGroup = None

    def setCurrentGroup(self, group):
        self.setCurrentPlane(group.plane)
        self.currentGroup = group

    def setRenderingItem(self,item):
        if item == self.renderingItem:
            return
        self.renderingItem = item
        self.renderItem()
        self.ui.graphicsView.zoomToFit()

    def renderItem(self):
        self.view_plaimage(self.renderingItem.render(highlight=self.selectedItem,boxes=self.ui.action_ShowCellBoxes.isChecked(),values=self.ui.action_ShowCellValues.isChecked()))
        if pla is not None:
            self.setWindowTitle("PLA decoder - %s"%self.getProjectItemName(self.renderingItem))
        else:
            self.setWindowTitle("PLA decoder")

    def showTempStatus(self, *msg):
        full_msg = " ".join((str(part) for part in msg))
        print("Status:", repr(full_msg))
        self.statusBar().showMessage(full_msg, 4000)

    def showModalStatus(self, *msg):
        full_msg = " ".join((str(part) for part in msg))
        print("Status:", repr(full_msg))
        self.statusBar().showMessage(full_msg)

    ############################################
    # Slots for Mouse Events from Graphicsview #
    ############################################

    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneLeftClicked(self, qimg_xy, keymods):
        if self.mode == MODE_IDLE:
            pass #TODO: Select item
        elif self.mode == MODE_CREATE_PLANE_1:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())])
            self.showModalStatus("Click bottom-right corner of plane")
            self.mode = MODE_CREATE_PLANE_2
        elif self.mode == MODE_CREATE_PLANE_2:
            self.modeParam2 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())])
            self.mode = MODE_IDLE
            self.showModalStatus("Idle")
            self.showTempStatus("Creating")
            self.currentPlane = self.currentPLA.add_plane()
            print(self.modeParam1)
            print(self.modeParam2)
            self.currentPlane.set_region( self.modeParam1, self.modeParam2 - self.modeParam1 )
            self.selectProjectItem(self.currentPlane)
            self.populateTree()
            self.renderItem()
        elif self.mode == MODE_CREATE_GROUP:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())]) + self.renderingItem.base_coord()
            self.mode = MODE_IDLE
            self.showModalStatus("Idle")
            self.showTempStatus("Creating")
            self.currentGroup = self.currentPlane.add_group()
            print(self.modeParam1)
            self.currentGroup.set_region_base( self.modeParam1 )
            if self.currentGroupTemplate is not None:
                self.currentGroup.load_template(self.currentGroupTemplate)
            self.selectProjectItem(self.currentGroup)
            self.populateTree()
            self.renderItem()
        elif self.mode == MODE_PROBE_CELL:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())]) + self.renderingItem.base_coord()
            t = self.currentGroup.get_cell_coord(self.modeParam1[0], self.modeParam1[1])
            if t:
                x,y = t
                self.showTempStatus("Probe %i %i"%t)
                ax = self.figure.add_subplot(111)
                self.currentGroup.classify_dbg(y,x,ax)
                self.canvas.draw()
        elif self.mode == MODE_SET_CELL:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())]) + self.renderingItem.base_coord()
            t = self.currentGroup.get_cell_coord(self.modeParam1[0], self.modeParam1[1])
            if t:
                x,y = t
                self.showTempStatus("Set cell %i %i"%t)
                self.currentGroup.set_cell_class(y,x,self.ui.classSetSpin.value())
                self.renderItem()
        elif self.mode == MODE_RESET_CELL:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())]) + self.renderingItem.base_coord()
            t = self.currentGroup.get_cell_coord(self.modeParam1[0], self.modeParam1[1])
            if t:
                x,y = t
                self.showTempStatus("Reset cell %i %i"%t)
                self.currentGroup.reset_cell_class(y,x)
                self.renderItem()
        elif self.mode == MODE_EXC_CELL:
            self.modeParam1 = numpy.array([int(qimg_xy.x()),int(qimg_xy.y())]) + self.renderingItem.base_coord()
            t = self.currentGroup.get_cell_coord(self.modeParam1[0], self.modeParam1[1])
            if t:
                x,y = t
                self.showTempStatus("Excluded cell %i %i"%t)
                self.currentGroup.toggle_cell_exc(y,x)
                self.renderItem()


    @QtCore.pyqtSlot(QtCore.QPointF, int)
    def on_graphicsView_sceneRightClicked(self, qimg_xy, keymods):
        pass

    @QtCore.pyqtSlot()
    def on_action_CreatePlane_triggered(self):
        self.startCreatePlane()

    @QtCore.pyqtSlot()
    def on_action_CreateGroup_triggered(self):
        self.startCreateGroup()

    @QtCore.pyqtSlot()
    def on_action_ProbeCell_triggered(self):
        self.startProbeCell()

    @QtCore.pyqtSlot()
    def on_action_SetCell_triggered(self):
        self.startSetCell()

    @QtCore.pyqtSlot()
    def on_action_ResetCell_triggered(self):
        self.startResetCell()

    @QtCore.pyqtSlot()
    def on_action_ExcCell_triggered(self):
        self.startExcludeCell()

    @QtCore.pyqtSlot()
    def on_action_IdleMode_triggered(self):
        self.mode = MODE_IDLE
        self.showModalStatus("Idle")

    def startCreatePlane(self):
        if not isinstance(self.selectedItem, pla):
            self.showTempStatus("Error: planes can only be added to a PLA")
            return
        self.showModalStatus("Click top-left corner of plane (Esc to cancel)")
        self.mode = MODE_CREATE_PLANE_1

    def startCreateGroup(self):
        if not isinstance(self.selectedItem, pla_plane):
            self.showTempStatus("Error: groups can only be added to a plane")
            return
        if not self.renderingItem == self.currentPlane:
            self.showTempStatus("Error: groups can only be added when the plane view is active")
            return
        self.showModalStatus("Click top-left corner of group (Esc to cancel)")
        self.mode = MODE_CREATE_GROUP

    def startProbeCell(self):
        if not isinstance(self.selectedItem, pla_group):
            self.showTempStatus("Error: cells can only be probed on a group")
            return
        if not self.renderingItem == self.currentPlane:
            self.showTempStatus("Error: groups can only be probed when the plane view is active")
            return
        self.showModalStatus("Click cell to probe (Esc to cancel)")
        self.mode = MODE_PROBE_CELL

    def startSetCell(self):
        if not isinstance(self.selectedItem, pla_group):
            self.showTempStatus("Error: cells can only be set on a group")
            return
        if not self.renderingItem == self.currentPlane:
            self.showTempStatus("Error: groups can only be set when the plane view is active")
            return
        self.showModalStatus("Click cells to set (Esc to cancel)")
        self.mode = MODE_SET_CELL

    def startResetCell(self):
        if not isinstance(self.selectedItem, pla_group):
            self.showTempStatus("Error: cells can only be reset on a group")
            return
        if not self.renderingItem == self.currentPlane:
            self.showTempStatus("Error: groups can only be reset when the plane view is active")
            return
        self.showModalStatus("Click cells to reset (Esc to cancel)")
        self.mode = MODE_RESET_CELL

    def startExcludeCell(self):
        if not isinstance(self.selectedItem, pla_group):
            self.showTempStatus("Error: cells can only be excluded on a group")
            return
        if not self.renderingItem == self.currentPlane:
            self.showTempStatus("Error: groups can only be excluded when the plane view is active")
            return
        self.showModalStatus("Click cells to exclude from reference (Esc to cancel)")
        self.mode = MODE_EXC_CELL

    def modelIndexToArray(self, mi):
        arr = []
        while mi.isValid():
            arr.append(mi.row())
            mi = mi.parent()
        return arr[::-1]

    def getProjectItem(self,mi):
        arr = self.modelIndexToArray(mi)
        item = self.plalist[arr[0]]
        for i in arr[1::]:
            item = item.children()[i]
        return item

    def getProjectItemName(self,i):
        arr = []
        while i is not None:
            arr.append(i.name)
            i = i.parent()
        return "::".join(arr[::-1])

    @QtCore.pyqtSlot("QItemSelection")
    def on_projectTree_selectionChanged(self, selected):
        """

        :type selected: QItemSelection
        """
        a = selected.indexes()[0]  # type: QModelIndex
        item = self.getProjectItem(a)
        print("select",item)
        self.selectProjectItem(item)

    @QtCore.pyqtSlot("QStandardItem*")
    def on_projectTree_itemChanged(self, item):
        pitem = self.getProjectItem(item.index())
        nt = item.text()
        if nt == pitem.name:
            return
        print("changed: "+pitem.name+" to "+nt)
        pitem.name = nt
        print("populate tree")
        #self.populateTree() #Caused segfault (concurrent modification)
        print("set current pla")
        if pitem == self.currentPLA:
            self.setCurrentPLA(pitem)
            self.setRenderingItem(pitem)
        print("done")

    @QtCore.pyqtSlot("QPoint")
    def on_projectTree_customContextMenuRequested(self,pt):
        idx = self.ui.projectTree.indexAt(pt)
        if not idx.isValid():
            return
        item = self.getProjectItem(idx)
        gpt = self.ui.projectTree.mapToGlobal( pt )
        ctx = QMenu(self)
        rename = ctx.addAction("&Rename")
        rename.triggered.connect(lambda : self.on_projectTreeMenu_rename(idx))
        ctx.addSeparator()
        ctx.addAction("&Cancel")
        QMenu.exec(ctx, gpt)

    def on_projectTreeMenu_rename(self, idx):
        self.ui.projectTree.edit(idx)

    @QtCore.pyqtSlot("QModelIndex")
    def on_projectTree_doubleClicked(self):
        if self.selectedItem is None or self.selectedItem == self.renderingItem:
            return
        self.setRenderingItem(self.selectedItem)

    def handleFileSelection(self,tupl):
        path = tupl[0]  # type: str
        filt = tupl[1]
        ext = filt.split(".")[1].split(")")[0] #TODO: Create a better version of this
        if ext == "*":
            ext = ""
        else:
            ext = "." + ext
        if path.endswith(ext):
            ext = ""
        return path+ext

    def load(self,path):
        fp = open(path, "r")
        _pla = pla.deserialize(json.load(fp))
        self.plalist.append(_pla)
        fp.close()
        _pla.serialize_path = path
        self.populateTree()
        self.selectProjectItem( _pla )

    @QtCore.pyqtSlot()
    def on_action_OpenFile_triggered(self):
        path = QFileDialog.getOpenFileName(None, 'Open file', '.', 'PLAdec files (*.pla);;All files (*.*)')
        if path == ('',''):
            return
        path = self.handleFileSelection(path)
        self.load(path)

    @QtCore.pyqtSlot()
    def on_action_SaveFileAs_triggered(self):
        if not self.currentPLA:
            self.showTempStatus("Nothing to save")
        path = QFileDialog.getSaveFileName(None, 'Save %s'%self.currentPLA.name, '.', 'PLAdec files (*.pla);;All files (*.*)')
        if path == ('',''):
            return
        path = self.handleFileSelection(path)
        print(path)
        fp = open(path,"w")
        json.dump(self.currentPLA.serialize(),fp, indent=4)
        fp.close()
        self.currentPLA.serialize_path = path

    @QtCore.pyqtSlot()
    def on_action_ShowCellBoxes_triggered(self):
        self.renderItem()
    @QtCore.pyqtSlot()
    def on_action_ShowCellValues_triggered(self):
        self.renderItem()

    @QtCore.pyqtSlot()
    def on_action_SaveFile_triggered(self):
        if not self.currentPLA:
            self.showTempStatus("Nothing to save")
        if not self.currentPLA.serialize_path:
            self.on_action_SaveFileAs_triggered()
            return
        fp = open(self.currentPLA.serialize_path,"w")
        json.dump(self.currentPLA.serialize(),fp, indent=4)
        fp.close()

    @QtCore.pyqtSlot()
    def on_action_ClearPlot_triggered(self):
        self.figure.clear()
        self.canvas.draw()

    @QtCore.pyqtSlot()
    def on_plotRefButton_clicked(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.currentGroup.plot_ref(ax)
        self.canvas.draw()


def run(app):
    import argparse
    parser = argparse.ArgumentParser(description='')
    window = PlaDecMainWin()
    window.show()

    return app.exec_() # Start the event loop.

def main():
    import sys

    # Initialize the QApplication object, and free it last.
    # Not having this in a different function than other QT
    # objects can cause segmentation faults as app is freed
    # before the QEidgets.
    app = QtWidgets.QApplication(sys.argv)

    # Allow Ctrl-C to interrupt QT by scheduling GIL unlocks.
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) # Let the interpreter run.

    sys.exit(run(app))

if __name__ == "__main__":
    main()

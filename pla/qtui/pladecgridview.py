from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5 import QtWidgets, QtCore


class PlaDecGridView(QtWidgets.QGraphicsView):
    """"""

    """Signal sends the QPointF(x,y) position of Left mouse clicks on the
    scene, as well as the keyboard modifiers."""
    sceneLeftClicked = pyqtSignal(QPointF, int, name='sceneLeftClicked')

    """Signal sends the QPointF(x,y) position of Right mouse clicks on the
    scene, as well as the keyboard modifiers."""
    sceneRightClicked = pyqtSignal(QPointF, int, name='sceneRightClicked')

    def mousePressEvent(self, event):
        """Dispatch a signal when right and left clicks occur in the display region"""
        if event.button() == Qt.LeftButton:
            qimg_xy = self.mapToScene(event.pos())
            if 0 <= qimg_xy.x() < self.scene().width() and\
               0 <= qimg_xy.y() < self.scene().height():
                self.sceneLeftClicked.emit(qimg_xy, event.modifiers())
                return
        elif event.button() == Qt.RightButton:
            qimg_xy = self.mapToScene(event.pos())
            if 0 <= qimg_xy.x() < self.scene().width() and\
               0 <= qimg_xy.y() < self.scene().height():
                self.sceneRightClicked.emit(qimg_xy, event.modifiers())
                return

        super(PlaDecGridView, self).mousePressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.scale(1.25, 1.25)
            else:
                self.scale(0.8, 0.8)
        else:
            super().wheelEvent(event)

    def zoomToFit(self):
        self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)

    def resizeEvent(self, QResizeEvent):
        super().resizeEvent(QResizeEvent)
        #self.zoomToFit()
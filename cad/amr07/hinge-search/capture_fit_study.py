"""Capture real FreeCAD windows for the rejected nominal mounting trial."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
NAME = 'AMR_Hinge_DirectFit_Study'
doc = App.listDocuments().get(NAME) or App.openDocument(str(HERE / (NAME+'.FCStd')))
App.setActiveDocument(doc.Name)
Gui.activateWorkbench('PartWorkbench')
Gui.Selection.clearSelection()
w = Gui.getMainWindow()
w.resize(1600, 1050)
for dock in w.findChildren(QtWidgets.QDockWidget):
    dock.hide()
view = Gui.activeDocument().activeView()
view.setCameraType('Orthographic')


def camera(direction, target, height):
    z = App.Vector(*direction); z.normalize()
    x = App.Vector(0, 0, 1).cross(z); x.normalize(); y = z.cross(x)
    view.setCameraOrientation(App.Rotation(x, y, z, 'ZXY').Q)
    c = view.getCameraNode(); p = App.Vector(*target) + z*1000
    c.position.setValue(p.x, p.y, p.z)
    c.focalDistance.setValue(1000); c.height.setValue(height)
    c.nearDistance.setValue(1); c.farDistance.setValue(3000)


def save(name):
    w.statusBar().showMessage('REJECTED FIT STUDY | HG-TP20 horizontal leaf clashes with 3030 | seat Z224 vs lid top Z233: 9 mm | NOT production CAD', 0)
    doc.recompute(); view.redraw(); Gui.updateGui(); QtWidgets.QApplication.processEvents()
    assert w.grab().save(str(HERE/name))


def configure(kind):
    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            obj.ViewObject.DiffuseColor = [obj.ViewObject.ShapeColor]
    doc.getObject('Frame').ViewObject.Transparency = 80
    doc.getObject('Plate').ViewObject.Transparency = 65
    doc.getObject('MovingLeaf').ViewObject.Transparency = 45
    if kind == 'iso':
        view.viewAxonometric()
    else:
        view.viewRight()
    view.fitAll()
    view.redraw(); Gui.updateGui()
    doc.recompute()
    doc.save()


# Configure and capture in separate GUI calls, allowing Qt to finish painting
# the actual application window between calls.
if __name__ == '__main__':
    configure('iso')
    print('View configured. Call save() in the following GUI call after paint.')

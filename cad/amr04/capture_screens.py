"""Capture actual FreeCAD window and viewport; no composited illustrations."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
NAME = 'AMR01_DDSM115_A3'
if NAME not in App.listDocuments():
    App.openDocument(str(HERE / (NAME + '.FCStd')))
App.setActiveDocument(NAME)
doc = App.activeDocument()
window = Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console', 'Report view', 'Tasks'):
        dock.hide()
Gui.Selection.clearSelection()
view = Gui.activeDocument().activeView()
view.viewAxonometric()
orientation = view.getCameraOrientation()

def save(suffix):
    view.fitAll()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE / ('viewport-' + suffix + '.png')), 1600, 1100, 'White')
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE / ('cad-screen-' + suffix + '.png')))

save('isometric')
view.setCameraOrientation(orientation.multiply(App.Rotation(App.Vector(1, 0, 0), 180)).Q)
save('underside')
view.viewFront()
save('side')
view.viewTop()
save('top')
# Isolate the left module to expose the fixed side and fasteners for review.
features = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature']
visibility = {o.Name: o.ViewObject.Visibility for o in features}
for o in features:
    o.ViewObject.Visibility = o.Name.endswith('L')
view.setCameraOrientation(orientation.multiply(App.Rotation(App.Vector(1, 0, 0), 180)).Q)
save('drive-module')
for o in features:
    o.ViewObject.Visibility = visibility[o.Name]
view.setCameraOrientation(orientation.Q)
view.fitAll()
Gui.updateGui()
doc.save()
print('Saved A3 actual FreeCAD screens: isometric, underside, side, top, drive-module')

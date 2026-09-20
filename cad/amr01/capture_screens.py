"""Save real FreeCAD window captures and unmodified viewport PNGs."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
name = 'AMR01_FirstDesign_A'
if name not in App.listDocuments():
    App.openDocument(str(HERE / (name + '.FCStd')))
App.setActiveDocument(name)
Gui.activeDocument().activeView().viewAxonometric()
window = Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console', 'Report view', 'Tasks'):
        dock.hide()
Gui.Selection.clearSelection()
view = Gui.activeDocument().activeView()
q = view.getCameraOrientation()


def save(suffix):
    view.fitAll()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE / ('viewport-' + suffix + '.png')), 1600, 1100, 'White')
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    if not window.grab().save(str(HERE / ('cad-screen-' + suffix + '.png'))):
        raise RuntimeError('Failed to capture FreeCAD window')


save('isometric')
view.setCameraOrientation(q.multiply(App.Rotation(App.Vector(1, 0, 0), 180)).Q)
save('underside')
view.viewTop()
save('top')
view.setCameraOrientation(q.Q)
view.fitAll()
Gui.updateGui()
App.activeDocument().save()
print('Saved actual FreeCAD window screenshots: isometric, underside, top')

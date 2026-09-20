"""Capture the actual FreeCAD GUI after the A3 electrical study is generated.

This is deliberately separate from geometry generation and is run by the GUI owner.
"""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / 'electrical_layout_parameters.json').read_text())
name = cfg['layout_document']
if name not in App.listDocuments():
    App.openDocument(str(HERE / (name + '.FCStd')))
App.setActiveDocument(name)
doc = App.getDocument(name)
window = Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console', 'Report view', 'Tasks'):
        dock.hide()
Gui.Selection.clearSelection()
view = Gui.activeDocument().activeView()
view.viewAxonometric()
orientation = view.getCameraOrientation()
names = ['BatteryUpperRemoval', 'Route_BatteryToFuse', 'TireRemovalOutboardL', 'TireRemovalOutboardR']
previous = {n: doc.getObject(n).ViewObject.Visibility for n in names}


def save(suffix):
    view.fitAll()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE / ('viewport-electrical-' + suffix + '.png')), 1600, 1100, 'White')
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    if not window.grab().save(str(HERE / ('cad-screen-electrical-' + suffix + '.png'))):
        raise RuntimeError('Could not save the actual FreeCAD window: ' + suffix)


try:
    for n in cfg['hidden_services']:
        doc.getObject(n).ViewObject.Visibility = False
    doc.getObject('Route_BatteryToFuse').ViewObject.Visibility = True
    save('isometric')
    view.viewTop()
    save('top')
    view.setCameraOrientation(orientation.Q)
    doc.getObject('BatteryUpperRemoval').ViewObject.Visibility = True
    doc.getObject('Route_BatteryToFuse').ViewObject.Visibility = False
    save('battery-removal')
    doc.getObject('BatteryUpperRemoval').ViewObject.Visibility = False
    doc.getObject('Route_BatteryToFuse').ViewObject.Visibility = True
    for n in ('TireRemovalOutboardL', 'TireRemovalOutboardR'):
        doc.getObject(n).ViewObject.Visibility = True
    save('tire-service')
finally:
    for n, visible in previous.items():
        doc.getObject(n).ViewObject.Visibility = visible
    view.setCameraOrientation(orientation.Q)
    view.fitAll()
    Gui.updateGui()
    doc.save()

print('Saved actual FreeCAD A3 electrical-study screens: isometric/top/battery-removal/tire-service.')

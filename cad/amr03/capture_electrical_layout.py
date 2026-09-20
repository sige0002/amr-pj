"""Capture native FreeCAD window for the reference electrical packaging study."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent
name='AMR01_ElectricalLayout_A2'
if name not in App.listDocuments():App.openDocument(str(HERE/(name+'.FCStd')))
App.setActiveDocument(name)
doc=App.getDocument(name)
window=Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
Gui.Selection.clearSelection()
view=Gui.activeDocument().activeView()

def save(suffix):
    view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-electrical-'+suffix+'.png')),1600,1100,'White')
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-electrical-'+suffix+'.png')))

view.viewAxonometric();save('isometric')
view.viewTop();save('top')
view.viewAxonometric()
doc.getObject('BatteryUpperRemoval').ViewObject.Visibility=True
doc.getObject('Route_BatteryToFuse').ViewObject.Visibility=False
save('battery-removal')
doc.getObject('BatteryUpperRemoval').ViewObject.Visibility=False
doc.getObject('Route_BatteryToFuse').ViewObject.Visibility=True
view.fitAll();Gui.updateGui();doc.save()
print('Saved actual FreeCAD electrical study screens; added geometry is reference only.')

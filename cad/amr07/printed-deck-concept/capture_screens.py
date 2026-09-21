"""Capture the actual FreeCAD window for the separate PLA concept."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE=Path(__file__).resolve().parent
NAME='AMR01_PrintedDeck_P0'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
Gui.activateWorkbench('PartWorkbench')
App.setActiveDocument(NAME)
Gui.Selection.clearSelection()
window=Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
colors=[(.22,.65,.72),(.28,.72,.77),(.30,.62,.73),(.38,.72,.78)]
for o in doc.Objects:
    o.ViewObject.Visibility=o.MaterialBasis!='reference'
    o.ViewObject.DisplayMode='Flat Lines'
    o.ViewObject.LineColor=(.12,.17,.20)
    o.ViewObject.ShapeColor={'aluminum':(.74,.78,.82),'steel':(.48,.52,.57),'PLA':(.22,.57,.65)}.get(o.MaterialBasis,(.15,.17,.19))
    if o.Name.startswith('PrintedDeckPanel'):o.ViewObject.ShapeColor=colors[int(o.Name[-1])-1]
    if o.Name.startswith(('ExtraSupport','CompressionSleeve')):o.ViewObject.ShapeColor=(.93,.58,.19)
    if o.Name.startswith('CustomMotorMount'):o.ViewObject.ShapeColor=(.89,.54,.18)
    if o.Name.startswith('CargoStop'):o.ViewObject.ShapeColor=(.34,.43,.52)
view=Gui.activeDocument().activeView()


def save(name):
    view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+name+'.png')),1600,1100,'White')
    assert window.grab().save(str(HERE/('cad-screen-'+name+'.png')))


view.viewAxonometric();iso=view.getCameraOrientation();save('isometric')
view.viewTop();save('top')
view.setCameraOrientation(iso.multiply(App.Rotation(App.Vector(1,0,0),180)).Q);save('underside')
view.viewAxonometric();view.fitAll();doc.recompute();doc.save()
print('Captured actual FreeCAD window, P0 only.')

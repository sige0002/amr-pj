"""Save actual FreeCAD window screenshots of A6, with native assembly colors."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE=Path(__file__).resolve().parent
NAME='AMR01_M0601C_A6'
V=App.Vector
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
old=App.getDocument('AMR01_M0601C_A4') if 'AMR01_M0601C_A4' in App.listDocuments() else None
Gui.activateWorkbench('PartWorkbench'); App.setActiveDocument(NAME)
window=Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'): dock.hide()
Gui.Selection.clearSelection()
features=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature']
for o in features:
    source=old.getObject(o.Name) if old else None
    o.ViewObject.ShapeColor=getattr(source.ViewObject,'ShapeColor',(.7,.75,.8)) if source else {'aluminum':(.74,.78,.82),'steel':(.45,.49,.54),'reference':(.85,.48,.12)}.get(o.MaterialBasis,(.1,.15,.17))
    o.ViewObject.DisplayMode='Flat Lines'; o.ViewObject.LineColor=(.13,.16,.19)
    o.ViewObject.Transparency=75 if o.MaterialBasis=='reference' else 0
    o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name=='BatteryReservedSpace'
    if o.Name.startswith('CustomMotorMount'): o.ViewObject.ShapeColor=(.94,.57,.16)
    if o.Name.startswith('CargoStop'): o.ViewObject.ShapeColor=(.26,.45,.6)
    if 'Strap' in o.Name: o.ViewObject.ShapeColor=(.13,.17,.2)
    if o.Name.startswith('Reserved_'): o.ViewObject.ShapeColor=(.3,.64,.87)
for o in doc.Objects:
    if o.TypeId=='App::DocumentObjectGroup':
        o.Label=o.Label.replace('A4 / M0601C_111 / CNC quote candidate / tire axial stack provisional','A6 / cargo10kg, slope8kg / structure15kg SF2 target')


def capture(suffix):
    view=Gui.activeDocument().activeView(); view.fitAll(); Gui.updateGui(); QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+suffix+'.png')),1600,1100,'White')
    assert window.grab().save(str(HERE/('cad-screen-'+suffix+'.png')))


view=Gui.activeDocument().activeView(); view.viewAxonometric(); iso=view.getCameraOrientation()
capture('isometric')
view.setCameraOrientation(iso.multiply(App.Rotation(V(1,0,0),180)).Q)
capture('underside')
for o in features:
    o.ViewObject.Visibility=o.Name.endswith('L') or (o.Name.startswith('Rail400_4'))
view.setCameraOrientation(App.Rotation(V(0,0,1),V(-1,-2,-.7)).Q); capture('drive-module')
for o in features:
    o.ViewObject.Visibility=True
    if o.Name=='CargoDeckPlate': o.ViewObject.Transparency=70
view.setCameraOrientation(iso.Q); capture('cargo-and-electrical')
for o in features:
    o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name=='BatteryReservedSpace'
    if o.Name=='CargoDeckPlate': o.ViewObject.Transparency=0
view.setCameraOrientation(iso.Q); view.fitAll(); doc.recompute(); doc.save()
print('A6 actual GUI screens saved')

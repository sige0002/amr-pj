"""Save actual FreeCAD window screenshots of A6, with native assembly colors."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets, QtCore

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
    o.ViewObject.ShapeColor=getattr(source.ViewObject,'ShapeColor',(.7,.75,.8)) if source else {'aluminum':(.74,.78,.82),'steel':(.45,.49,.54),'PLA':(.18,.62,.58),'reference':(.85,.48,.12)}.get(o.MaterialBasis,(.1,.15,.17))
    o.ViewObject.DisplayMode='Flat Lines'; o.ViewObject.LineColor=(.13,.16,.19)
    o.ViewObject.Transparency=75 if o.MaterialBasis=='reference' else 0
    o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name=='BatteryReservedSpace'
    if o.Name.startswith('CustomMotorMount'): o.ViewObject.ShapeColor=(.94,.57,.16)
    if o.Name.startswith('CargoStop'): o.ViewObject.ShapeColor=(.26,.45,.6)
    if 'Strap' in o.Name: o.ViewObject.ShapeColor=(.13,.17,.2)
    if o.Name.startswith('Reserved_'): o.ViewObject.ShapeColor=(.3,.64,.87)
    if o.Name.startswith('FixtureCable'): o.ViewObject.ShapeColor=(.3,.64,.87)
for o in doc.Objects:
    if o.TypeId=='App::DocumentObjectGroup':
        for old_label in ('A4 / M0601C_111 / CNC quote candidate / tire axial stack provisional',
                          'A6 / cargo10kg, slope8kg / structure15kg SF2 target'):
            o.Label=o.Label.replace(old_label,'A6 / flat-floor cargo10kg / no added brake / structure15kg SF2 target')


def capture(suffix):
    view=Gui.activeDocument().activeView(); view.fitAll(); Gui.updateGui(); QtWidgets.QApplication.processEvents()
    loop=QtCore.QEventLoop();QtCore.QTimer.singleShot(500,loop.quit);loop.exec_()
    view.saveImage(str(HERE/('viewport-'+suffix+'.png')),1600,1100,'White')
    assert window.grab().save(str(HERE/('cad-screen-'+suffix+'.png')))


view=Gui.activeDocument().activeView()
iso=App.Rotation(.4247082003,.1759198966,.3398511429,.8204732386)
view.setCameraOrientation(iso.Q)
capture('isometric')
view.setCameraOrientation(iso.multiply(App.Rotation(V(1,0,0),180)).Q)
capture('underside')
for o in features:
    o.ViewObject.Visibility=o.Name.startswith(('CargoDeck','CargoStop','SlotNut_CargoDeck','Printed','Fixture'))
view.setCameraOrientation(iso.multiply(App.Rotation(V(1,0,0),180)).Q)
capture('grid-and-fixtures')
view.viewTop();capture('grid-top')
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

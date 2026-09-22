"""Actual FreeCAD GUI views; battery/adapter displayed as catalog envelopes."""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from pivy import coin
HERE=Path(__file__).resolve().parent
NAME='AMR01_MakitaPower_D5'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
window=Gui.getMainWindow();window.resize(1600,1100)
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
features=[o for o in doc.Objects if hasattr(o,'MaterialBasis')]
view=Gui.activeDocument().activeView()
r=json.loads((HERE/'validation.json').read_text())
original={o.Name:App.Placement(o.Placement) for o in features}

def normal():
    for o in features:
        o.Placement=original[o.Name]
        o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name.startswith(('Battery','Reserved_','LowElectronics'))
        o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines'
        o.ViewObject.LineColor=(.13,.16,.18)
        o.ViewObject.ShapeColor={'aluminum':(.74,.78,.81),'steel':(.42,.46,.50),'PLA':(.22,.52,.58)}.get(o.MaterialBasis,(.18,.20,.22))
        if o.Name=='BatteryBL1860B':o.ViewObject.ShapeColor=(.12,.17,.19)
        if o.Name=='BatteryAdapter03':o.ViewObject.ShapeColor=(.06,.55,.60)
        if 'Pad' in o.Name:o.ViewObject.ShapeColor=(.45,.46,.49)
        if ('Belt' in o.Name and 'Pad' not in o.Name) or 'Buckle' in o.Name:o.ViewObject.ShapeColor=(.85,.40,.13)
        if o.Name.startswith('Reserved_'):
            o.ViewObject.ShapeColor=(.50,.61,.74);o.ViewObject.Transparency=35
        if o.Name=='Reserved_EmergencyStop':o.ViewObject.ShapeColor=(.84,.18,.16)
    doc.getObject('CargoEnvelopeD3').ViewObject.Visibility=False

def rear_iso():
    z=App.Vector(-1.2,1.0,.9);z.normalize()
    x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
    view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q)

def save(name,zoom=1):
    doc.recompute();view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+name+'.png')),1600,1100,'White')
    if zoom!=1:
        view.getCameraNode().height.setValue(view.getCameraNode().height.getValue()*zoom)
        Gui.updateGui();QtWidgets.QApplication.processEvents()
    window.statusBar().showMessage('D5: BL1860B6Ah + adapter = catalog envelopes | tray and mounting modeled | deck103mm',0)
    QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-'+name+'.png')))

normal();rear_iso();save('assembled',.88)
normal();view.viewTop();save('top-layout',.92)
normal();view.viewFront();save('side-layout',.90)
normal()
for name in r['moving_parts']:
    p=App.Placement(original[name]);p.Base+=App.Vector(0,0,140);doc.getObject(name).Placement=p
for name in r['released_before_service']:doc.getObject(name).ViewObject.Visibility=False
cargo=doc.getObject('CargoEnvelopeD3');cargo.ViewObject.Visibility=True
cargo.ViewObject.ShapeColor=(.58,.62,.65);cargo.ViewObject.Transparency=70
for name in ['StrapRouteX','StrapRouteY']:doc.getObject(name).ViewObject.Visibility=True
rear_iso();save('battery-exchange',.90)
normal()
for o in features:
    o.ViewObject.Visibility=(o.Name.startswith(('Battery','RearBattery','ElectronicsBolt','LargeWasher_Electronics','SlotNut_Electronics')))
rear_iso();save('battery-retention')
normal()
for o in features:
    if o.Name.startswith(('AluminumDeck','PrintedStop','DeckBolt','Stop','StrapRoute')):o.ViewObject.Visibility=False
view.viewBottom();save('low-electronics')
normal();rear_iso();view.fitAll();doc.recompute();doc.save()
print('D5: six actual FreeCAD GUI screenshots saved.')

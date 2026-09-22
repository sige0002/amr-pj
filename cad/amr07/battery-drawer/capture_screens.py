"""Actual FreeCAD GUI screenshots of assembled, service and mounting states."""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from pivy import coin

HERE=Path(__file__).resolve().parent
NAME='AMR01_BatteryDrawer_D4'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
window=Gui.getMainWindow();window.resize(1600,1100)
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
features=[o for o in doc.Objects if hasattr(o,'MaterialBasis')]
view=Gui.activeDocument().activeView()
validation=json.loads((HERE/'validation.json').read_text())
original={o.Name:App.Placement(o.Placement) for o in features}

def normal():
    for o in features:
        o.Placement=original[o.Name]
        o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name.startswith('Battery')
        o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines'
        o.ViewObject.LineColor=(.14,.17,.19)
        o.ViewObject.ShapeColor={'aluminum':(.72,.76,.81),'steel':(.42,.46,.50),'PLA':(.25,.50,.57)}.get(o.MaterialBasis,(.14,.16,.18))
        if o.Name=='BatteryDrawerPLA':o.ViewObject.ShapeColor=(.10,.54,.64)
        if o.Name.startswith('BatteryGuide'):o.ViewObject.ShapeColor=(.34,.43,.49)
        if o.Name=='BatteryCandidate':o.ViewObject.ShapeColor=(.95,.58,.16)
        if o.Name.startswith('BatteryPad'):o.ViewObject.ShapeColor=(.25,.29,.32)
        if o.Name.startswith('BatteryBelt'):o.ViewObject.ShapeColor=(.64,.16,.13)
        if o.Name in ('BatteryLeadRoute','BatteryServiceConnector'):o.ViewObject.ShapeColor=(.17,.18,.21)
        if o.Name.startswith('DrawerScrew'):o.ViewObject.ShapeColor=(.88,.68,.18)
    doc.getObject('CargoEnvelopeD3').ViewObject.Visibility=False

def service_view():
    z=App.Vector(1,1,.8);z.normalize()
    x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
    view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q)

def save(name,zoom=1):
    doc.recompute();view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+name+'.png')),1600,1100,'White')
    if zoom!=1:
        view.getCameraNode().height.setValue(view.getCameraNode().height.getValue()*zoom)
        Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-'+name+'.png')))

normal();service_view();save('assembled',.85)
# Open service state keeps the aluminum plate AND the illustrated cargo.
for name in validation['moving_parts']:
    p=App.Placement(original[name]);p.Base=p.Base+App.Vector(0,220,0);doc.getObject(name).Placement=p
for name in validation['released_before_service']:doc.getObject(name).ViewObject.Visibility=False
cargo=doc.getObject('CargoEnvelopeD3');cargo.ViewObject.Visibility=True
cargo.ViewObject.ShapeColor=(.57,.61,.64);cargo.ViewObject.Transparency=70
for name in ['StrapRouteX','StrapRouteY']:doc.getObject(name).ViewObject.Visibility=True
service_view();save('battery-exchange',.85)
view.viewRear();save('service-side')
# Isolated removable module, in its actual assembled relation: belt loops,
# soft liners and lead storage are visible. No arbitrary explode offsets.
normal()
for o in features:o.ViewObject.Visibility=o.Name in validation['moving_parts']
view.viewAxonometric();save('pack-retention')
# Underside view shows the same original four M6 mount sets and two release
# screws; aluminum frame retained as context.
normal()
for o in features:
    if o.Name.startswith(('AluminumDeck','PrintedStop','DeckBolt','Stop','StrapRoute')):o.ViewObject.Visibility=False
view.viewBottom();save('guide-mounting')
normal();service_view();view.fitAll();doc.recompute();doc.save()
print('Saved actual FreeCAD GUI: D4 assembled, battery exchange, side, retention and guide mounting.')

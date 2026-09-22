"""Actual FreeCAD GUI screenshots of D6, with explicit maintenance positions."""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from pivy import coin
HERE=Path(__file__).resolve().parent
NAME='AMR01_TwoStorey_D6'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
window=Gui.getMainWindow();window.resize(1600,1100)
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
features=[o for o in doc.Objects if hasattr(o,'MaterialBasis')]
view=Gui.activeDocument().activeView();r=json.loads((HERE/'validation.json').read_text())
original={o.Name:App.Placement(o.Placement) for o in features}

def normal():
    for o in features:
        o.Placement=original[o.Name]
        o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name.startswith(('Battery','Reserved_','Computer','Supervisor'))
        o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines';o.ViewObject.LineColor=(.14,.16,.18)
        o.ViewObject.ShapeColor={'aluminum':(.73,.77,.80),'steel':(.43,.47,.51),'PLA':(.23,.55,.59)}.get(o.MaterialBasis,(.20,.22,.24))
        if o.Name.startswith('Upright'):o.ViewObject.ShapeColor=(.20,.23,.26)
        if o.Name=='BatteryBL1860B':o.ViewObject.ShapeColor=(.13,.17,.19)
        if o.Name=='BatteryAdapter03':o.ViewObject.ShapeColor=(.06,.56,.61)
        if 'Pad' in o.Name:o.ViewObject.ShapeColor=(.45,.47,.49)
        if ('Belt' in o.Name and 'Pad' not in o.Name) or 'Buckle' in o.Name:o.ViewObject.ShapeColor=(.88,.42,.15)
        if o.Name.startswith('Reserved_'):
            o.ViewObject.ShapeColor=(.49,.62,.76);o.ViewObject.Transparency=22
        if o.Name=='Reserved_EmergencyStop':o.ViewObject.ShapeColor=(.85,.15,.14)
    doc.getObject('CargoEnvelopeD3').ViewObject.Visibility=False

def iso(rear=True,high=.9,longitudinal=1.25):
    z=App.Vector(-longitudinal if rear else longitudinal,1.0,high);z.normalize()
    x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
    view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q)

def save(name,zoom=.9):
    doc.recompute();view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+name+'.png')),1600,1100,'White')
    if zoom!=1:view.getCameraNode().height.setValue(view.getCameraNode().height.getValue()*zoom)
    window.statusBar().showMessage('D6.1 | double brackets at four post bases | 1F: electronics | 2F: cargo233mm',0)
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-'+name+'.png')))

normal();iso(high=.55);save('assembled')
normal();view.viewFront();save('side-layout')
normal()
for n in r['translated_parts']:doc.getObject(n).ViewObject.Visibility=False
iso(high=1.3);save('first-floor')
view.viewTop();save('first-floor-top')
normal()
for n in r['moving_parts']:
    p=App.Placement(original[n]);p.Base+=App.Vector(-220,0,8);doc.getObject(n).Placement=p
for n in r['released_before_service']:doc.getObject(n).ViewObject.Visibility=False
cargo=doc.getObject('CargoEnvelopeD3');cargo.ViewObject.Visibility=True;cargo.ViewObject.Transparency=75
for n in ['StrapRouteX','StrapRouteY']:doc.getObject(n).ViewObject.Visibility=True
iso(high=.8);save('battery-exchange')
normal()
for n in ['Reserved_Computer','ComputerTopPad']:
    p=App.Placement(original[n]);p.Base+=App.Vector(0,-230,8);doc.getObject(n).Placement=p
doc.getObject('ComputerRetentionBelt').ViewObject.Visibility=False
iso(rear=False,high=.8);save('computer-exchange')
normal()
for o in features:
    o.ViewObject.Visibility=o.Name in ['Rail400_4','Upright3030_3','UpperRail3030_1'] or o.Name.startswith(('LevelBracket_3','LevelBolt_3','LevelNut_3'))
iso(rear=False,high=.65);save('frame-joint',1)
for end,rear,target in [('Lower',True,(105,135,111)),('Upper',False,(124,135,187))]:
    normal()
    for o in features:
        o.ViewObject.Visibility=o.Name in ['Upright3030_3','Rail400_4' if end=='Lower' else 'UpperRail3030_1'] or o.Name.startswith(tuple(p+'3_'+end for p in ['LevelBracket_','LevelBolt_','LevelNut_']))
    high=.55 if end=='Lower' else -.5
    longitudinal=0 if end=='Lower' else 1.25
    iso(rear=rear,high=high,longitudinal=longitudinal);doc.recompute();view.fitAll()
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    cam=view.getCameraNode();z=App.Vector(-longitudinal if rear else longitudinal,1.0,high);z.normalize()
    q=App.Vector(*target)+z*600
    cam.position.setValue(q.x,q.y,q.z);cam.focalDistance.setValue(600);cam.height.setValue(125 if end=='Lower' else 110)
    cam.nearDistance.setValue(1);cam.farDistance.setValue(2000)
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    label='2xHBLFSN6 + 4xM6x12' if end=='Lower' else 'HBLFSN6 + 2xM6x12'
    window.statusBar().showMessage('D6.1 '+end+' joint | '+label+' | direct metal end bearing',0)
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-frame-joint-'+end.lower()+'.png')))
normal();iso(high=.55);view.fitAll();doc.recompute();doc.save()
print('D6: nine actual FreeCAD GUI screenshots saved.')

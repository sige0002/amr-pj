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
    window.statusBar().showMessage('D6.4 | 4 fixings per floor panel | anchored seam beam | cargo233mm',0)
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
    window.statusBar().showMessage('D6.4 '+end+' joint | '+label+' | direct metal end bearing',0)
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-frame-joint-'+end.lower()+'.png')))

# Hide the upper storey/electronics so ALL16 shelf fixings are visible.
normal()
floor_bolts={f['bolt'] for f in r['floor_fixings']}
floor_hardware=('CradleBolt_','ElectronicsBolt_','FrontDeckBolt_','LargeWasher_Cradle',
                'LargeWasher_Electronics','LargeWasher_Front','SlotNut_Cradle_',
                'SlotNut_Electronics_','SlotNut_FrontDeck_','FloorSeam','SeamBeam','Gusset_','GussetBolt_','Washer_Gusset','SlotNut_Gusset_')
colors=[(.28,.65,.69),(.43,.68,.83),(.81,.70,.39),(.66,.53,.79)]
for o in features:
    o.ViewObject.Visibility=o.Name.startswith(('Cross300_','Rail300_','Rail400_','Bracket_','FloorPLA_')+floor_hardware)
    if o.Name.startswith('FloorPLA_'):
        ix,iy=map(int,o.Name.split('_')[1:]);o.ViewObject.ShapeColor=colors[2*ix+iy]
    if o.Name in floor_bolts or o.Name.startswith('LargeWasher_'):
        o.ViewObject.ShapeColor=(.95,.32,.06)
    if o.Name=='SeamBeamPLA':o.ViewObject.ShapeColor=(.9,.53,.12)
    if o.Name.startswith('Gusset_'):o.ViewObject.ShapeColor=(.25,.48,.80)
view.viewTop();save('floor-fixings-top')
# The lower view makes the four beam anchors and seam ribs inspectable.
iso(rear=False,high=-1.2);save('floor-support-under')
# Isolate the beam with both supporting inner rails and four ordinary M4 sets.
normal()
for o in features:
    b=o.Shape.BoundBox
    inner_rail=o.Name.startswith('Rail400_') and abs(abs((b.YMin+b.YMax)/2)-65)<.01
    o.ViewObject.Visibility=inner_rail or o.Name.startswith(('SeamBeam','FloorSeam'))
    if o.Name=='SeamBeamPLA':o.ViewObject.ShapeColor=(.90,.53,.12)
view.viewBottom();save('seam-beam-anchors',.55)
normal()
for o in features:
    o.ViewObject.Visibility=o.Name in ['Rail400_4','Cross300_2','Bracket_P120','JointA_P120','JointB_P120','SlotNut_JointA_P120','SlotNut_JointB_P120','FloorPLA_1_1','FrontDeckBolt_1','LargeWasher_Front1','SlotNut_FrontDeck_1'] or o.Name.startswith(('Gusset_11','GussetBolt_11','Washer_Gusset11','SlotNut_Gusset_11'))
    if o.Name=='FloorPLA_1_1':o.ViewObject.Transparency=50
    if o.Name=='Bracket_P120':o.ViewObject.ShapeColor=(.25,.48,.80);o.ViewObject.DiffuseColor=[(.25,.48,.80)]
    if o.Name=='FrontDeckBolt_1' or o.Name=='LargeWasher_Front1':o.ViewObject.ShapeColor=(.95,.32,.06)
    if o.Name=='Gusset_11':o.ViewObject.ShapeColor=(.25,.48,.80)
z=App.Vector(-1.25,-1,.9);z.normalize();x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q);doc.recompute();view.fitAll()
cam=view.getCameraNode();q=App.Vector(196,119,96)+z*600
cam.position.setValue(q.x,q.y,q.z);cam.focalDistance.setValue(600);cam.height.setValue(155)
cam.nearDistance.setValue(1);cam.farDistance.setValue(2000)
window.statusBar().showMessage('D6.4 | flat plate removed | existing internal HBLFSN6 | independent floor fixing above',0)
Gui.updateGui();QtWidgets.QApplication.processEvents()
view.saveImage(str(HERE/'viewport-corner-joint.png'),1600,1100,'White')
assert window.grab().save(str(HERE/'cad-screen-corner-joint.png'))
normal()
for o in features:
    o.ViewObject.Visibility=o.Name.startswith(('FloorPLA_','FloorSeam','SeamBeam','ComputerPad_'))
    if o.Name.startswith('FloorPLA_'):o.ViewObject.ShapeColor=(.23,.55,.59)
    if o.Name.startswith(('FloorSeamBolt','FloorSeamTopWasher')):o.ViewObject.ShapeColor=(.96,.38,.06)
    if o.Name.startswith('ComputerPad_'):o.ViewObject.ShapeColor=(.18,.22,.25)
iso(rear=False,high=1.25);doc.recompute();view.fitAll()
z=App.Vector(1.25,1,1.25);z.normalize();cam=view.getCameraNode();q=App.Vector(0,0,101)+z*600
cam.position.setValue(q.x,q.y,q.z);cam.focalDistance.setValue(600);cam.height.setValue(170)
cam.nearDistance.setValue(1);cam.farDistance.setValue(2000)
window.statusBar().showMessage('D6.4 | 4x M4 socket screws + OD12 washers | full2.4mm web | 4 integral PC supports +1mm liners',0)
Gui.updateGui();QtWidgets.QApplication.processEvents()
view.saveImage(str(HERE/'viewport-floor-seam-joint.png'),1600,1100,'White')
assert window.grab().save(str(HERE/'cad-screen-floor-seam-joint.png'))
normal();doc.getObject('Bracket_P120').ViewObject.DiffuseColor=[doc.getObject('Bracket_P120').ViewObject.ShapeColor]
iso(high=.55);view.fitAll();doc.recompute();doc.save()
print('D6.4: fourteen actual FreeCAD GUI screenshots saved.')

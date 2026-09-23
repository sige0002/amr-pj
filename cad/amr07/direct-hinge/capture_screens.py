"""Actual FreeCAD GUI windows, closed/open and fixedcamera opening frames."""
from pathlib import Path
import json
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent;NAME='AMR01_DirectHinge_D68'
if NAME in App.listDocuments():App.closeDocument(NAME)
doc=App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
w=Gui.getMainWindow();w.resize(1600,1100)
for dock in w.findChildren(QtWidgets.QDockWidget):
 dock.hide()
view=Gui.activeDocument().activeView();r=json.loads((HERE/'validation.json').read_text());objects=[o for o in doc.Objects if hasattr(o,'MaterialBasis')]
original={o.Name:App.Placement(o.Placement) for o in objects}
def normal():
 for o in objects:
  o.Placement=original[o.Name];o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name.startswith(('Battery','Reserved_','Computer','Supervisor','EStop_X','ARM_','MainPower_'))
  o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines';o.ViewObject.LineColor=(.12,.14,.16)
  color={'aluminum':(.74,.78,.82),'steel':(.43,.47,.51),'PLA':(.23,.55,.59),'rubber':(.16,.17,.19)}.get(o.MaterialBasis,(.28,.40,.52))
  if o.Name.startswith('RearStop') and o.MaterialBasis=='PLA':color=(.97,.77,.10)
  if o.Name.startswith('RearPower') and o.MaterialBasis=='PLA':color=(.23,.29,.34)
  if o.Name.startswith(('HatchMovingAdapter','HatchFixedAdapter')):color=(.20,.49,.78)
  if o.Name.startswith('HatchLockWing'):color=(.91,.53,.13)
  if o.Name=='EStop_XA1E_BV302R':color=(.91,.07,.06)
  if o.Name.startswith(('ARM_','MainPower_')):color=(.10,.11,.12)
  if o.Name.startswith('Reserved_'):o.ViewObject.Transparency=20
  if o.Name=='BatteryBL1860B':color=(.12,.16,.17)
  if o.Name=='BatteryAdapter03':color=(.04,.55,.58)
  if o.Name=='ComputerBarrierPLA':color=(.94,.85,.61)
  if 'Belt' in o.Name or 'Buckle' in o.Name:color=(.84,.41,.12)
  o.ViewObject.ShapeColor=color;o.ViewObject.DiffuseColor=[color]
 doc.getObject('CargoEnvelopeD3').ViewObject.Visibility=False

def open_lid(angle):
 axis=App.Vector(0,156,230);rot=App.Rotation(App.Vector(1,0,0),-angle)
 p=App.Placement(axis-rot.multVec(axis),rot)
 for n in r['moving_parts']:doc.getObject(n).Placement=p.multiply(original[n])
 for n in r['released_before_open']:doc.getObject(n).ViewObject.Visibility=False

def camera(direction=(-1.4,-1,1.1),target=None,height=None):
 z=App.Vector(*direction);z.normalize();x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
 view.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q);view.fitAll()
 if target:
  c=view.getCameraNode();p=App.Vector(*target)+z*1000;c.position.setValue(p.x,p.y,p.z);c.focalDistance.setValue(1000);c.height.setValue(height);c.nearDistance.setValue(1);c.farDistance.setValue(3000)

def save(name,status):
 doc.recompute();w.statusBar().showMessage(status,0);Gui.updateGui();QtWidgets.QApplication.processEvents()
 assert w.grab().save(str(HERE/('cad-screen-'+name+'.png')))

normal();camera();save('closed','D6.8 closed | frame-mounted steel hinges | metal lid angles | floor-supported rear controls')
normal();open_lid(90);camera();save('open-90','D6.8 open90 | torque hinge holding only; no opening stop | remove cargo and locks before opening')
normal();open_lid(45);camera();save('open-45','D6.8 open45 | empty-lid moment from validated CG | minimum initial holding torque3.0Nm')
normal()
for o in objects:
 o.ViewObject.Visibility=o.Name in ['AluminumDeckD3','UpperRail3030_1','LidAngle_1'] or (o.Name.startswith(('HGTP20_','Hinge','AngleDeck')) and ('_1' in o.Name))
camera((1.2,1.5,.85),(106,144,234),172);save('hinge-detail','D6.8 hinge | fixed leaf DIRECT on3030 | 2xM4 per leaf | simple4mm metal angle; no opening stop')
normal()
for o in objects:
 o.ViewObject.Visibility=o.Name in ['AluminumDeckD3','UpperRail3030_1','LidAngle_1'] or (o.Name.startswith(('HGTP20_','Hinge','AngleDeck')) and ('_1' in o.Name))
open_lid(90);camera((1.2,1.5,.8),(106,150,243),180);save('hinge-open-detail','D6.8 hinge open90 | metal hinge on3030 and simple lid angle | unloaded service only')
normal();camera((-1.5,-.45,.95),(-178,0,138),400);save('rear-controls','D6.8 rear controls | E-STOP + ARM and main power | boxes bear on PLA above rear3030')
normal()
for o in objects:
 o.ViewObject.Visibility=(o.Name in ['FloorPLA_0_0','FloorPLA_0_1'] or o.Name.startswith(('RearStop','RearPower','ElectronicsBolt','LargeWasher_Electronics','SlotNut_Electronics')) or (hasattr(o,'ModelNote') and o.MaterialBasis=='aluminum' and o.Shape.BoundBox.XMin<-200))
for o in objects:
 if o.Name.startswith('RearStopLid'):o.Placement.Base+=App.Vector(0,0,50)
 if o.Name=='RearStopCasePLA':o.ViewObject.Transparency=55
camera((-1.4,-.9,1.3),(-192,-65,147),260);save('case-assembly','D6.8 assembly | four downward M4 screws per box | side-loaded captive nuts | lid and switches removed for access')
normal();open_lid(90)
b=json.loads((HERE.parent/'two-story/validation.json').read_text())
for n in b['moving_parts']:
 p=App.Placement(original[n]);p.Base+=App.Vector(-220,0,8);doc.getObject(n).Placement=p
for n in b['released_before_service']:doc.getObject(n).ViewObject.Visibility=False
camera();save('battery-service','D6.8 battery service | disconnect and release belt | lift8mm then withdraw rearward220mm')
frame_dir=Path('/tmp/amr-d68-cad-frames');frame_dir.mkdir(exist_ok=True)
normal();open_lid(90);camera((-1.4,-1,1.1),(0,5,250),700)
for i,angle in enumerate(list(range(0,91,10))):
 normal();open_lid(angle);doc.recompute();w.statusBar().showMessage(f'D6.8 CAD opening | {angle}deg | unloaded / locks removed | NOT a physics simulation',0);Gui.updateGui();QtWidgets.QApplication.processEvents();assert w.grab().save(str(frame_dir/f'{i:02d}.png'))
normal();camera();doc.recompute();doc.save()
print('Actual FreeCAD GUI captures saved; final assembly restored closed.')

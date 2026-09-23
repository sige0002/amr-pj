"""Actual FreeCAD GUI windows, closed/open and fixedcamera opening frames."""
from pathlib import Path
import json
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent;NAME='AMR01_HingedDeck_D67'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
w=Gui.getMainWindow();w.resize(1600,1100)
for dock in w.findChildren(QtWidgets.QDockWidget):
 if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
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
 axis=App.Vector(0,172.5,249.5);rot=App.Rotation(App.Vector(1,0,0),-angle)
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

normal();camera();save('closed','D6.7 CLOSED | 2 metal hand locks | emptycargo area200x200 | REAR E-STOP / ARM / MAIN')
normal();open_lid(90);camera();save('open-90','D6.7 OPEN90deg | unload andremove belts/locks first | 2xHG-TS15 | printedpositive90degstops')
normal();open_lid(45);camera();save('open-45','D6.7 OPEN45deg | frictionhold cataloguecomparison | no physical strength/lifetimequalification')
normal()
for o in objects:
 o.ViewObject.Visibility=o.Name in ['AluminumDeckD3','UpperRail3030_1'] or o.Name.startswith(('HatchMovingAdapter_1','HatchFixedAdapter_1','HGTS15_')) or ('Hatch' in o.Name and '_1_' in o.Name)
camera((1,1,.85),(126,149,243),210);save('hinge-detail','Hinge detail | blue:printedadapters | 2xM6 frameanchors | existingM4 deckgrid | metalhinge1.5Nm')
normal()
for o in objects:o.ViewObject.Visibility=o.Name in ['AluminumDeckD3','UpperRail3030_0','DeckSlotNut0'] or o.Name.startswith(('HatchLockWingBolt_0','HatchLockWasher_0'))
camera((-1,-1,.8),(-105,-135,235),125);save('lock-detail','Lock detail | M6x15 butterflybolt +3x1mm STEEL washers | 4mmmetalplate | T-slotnut | no plasticclampstack')
normal()
for o in objects:
 if o.Name.startswith(('RearStop','RearPower')) and o.MaterialBasis=='PLA':o.ViewObject.Transparency=60
 if o.Name in ['RearStopSignalRoute','MainPowerInputRoute','MainPowerOutputRoute']:o.ViewObject.Visibility=True;o.ViewObject.ShapeColor=(.92,.55,.08)
camera((-1.6,-.5,.65),(-168,0,160),410);save('rear-controls','REAR controls | red E-STOP andblack ARM | mainpower besideconnector | batterywithdrawal opening')
normal();open_lid(90)
b=json.loads((HERE.parent/'two-story/validation.json').read_text())
for n in b['moving_parts']:
 p=App.Placement(original[n]);p.Base+=App.Vector(-220,0,8);doc.getObject(n).Placement=p
for n in b['released_before_service']:doc.getObject(n).ViewObject.Visibility=False
camera();save('battery-service','Batteryservice | unplug +releasebelt | lift8mm thenrear220mm | openingdeck isoptional for batteryexchange')
normal();open_lid(90)
for n in ['Reserved_Computer','ComputerTopPad']:
 p=App.Placement(original[n]);p.Base+=App.Vector(0,-230,8);doc.getObject(n).Placement=p
doc.getObject('ComputerRetentionBelt').ViewObject.Visibility=False
camera();save('computer-service','Computerservice | sidewithdrawal230mm after8mmlift | case/product remainsreserved')
# Actual GUI frames, constantcamera. No physics simulation claimed.
frame_dir=Path('/tmp/amr-hatch-cad-frames');frame_dir.mkdir(exist_ok=True)
normal();open_lid(90);camera((-1.4,-1,1.1),(0,5,270),770)
for i,angle in enumerate(range(0,91,10)):
 normal();open_lid(angle);doc.recompute();w.statusBar().showMessage(f'D6.7 CAD opening animation | {angle}deg | unloaded, locksremoved | NOT a physics test',0);Gui.updateGui();QtWidgets.QApplication.processEvents();assert w.grab().save(str(frame_dir/f'{i:02d}.png'))
normal();camera();doc.recompute();doc.save()
print('Saved8 actual FreeCAD GUI screenshots and10 openinganimationframes; restoredclosedassembly.')

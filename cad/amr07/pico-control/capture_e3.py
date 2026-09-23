from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent;NAME='AMR01_PicoControl_E3'
doc=App.listDocuments().get(NAME) or App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench')
w=Gui.getMainWindow();w.resize(1600,1050)
for dock in w.findChildren(QtWidgets.QDockWidget):dock.hide()
v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');Gui.Selection.clearSelection()
refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214']
status={'overall':'E3 | PICO + 2CH RS485 | DIRECT TWO-POLE E-STOP | MAIN POWER | NO ARM BUTTON',
'electronics':'E3 ELECTRONICS | deck hidden | HAT/Pico stack and PC supply are nominal envelopes; received-part fit pending',
'controls':'E3 REAR CONTROLS | RED: motor cutoff, one NC per motor | BLACK: all-load main | 4 floor fixings each',
'pico':'E3 PICO MOCK | 4 floor bolts clear both rails | removable cover | board retention/stack fit pending'}
def setup(kind):
 for o in doc.Objects:
  if not hasattr(o,'MaterialBasis'):continue
  o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name in refs
  o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines'
  c={'PLA':(.23,.55,.59),'aluminum':(.74,.78,.82),'steel':(.44,.48,.50),'rubber':(.12,.13,.14)}.get(o.MaterialBasis,(.3,.42,.60))
  if o.Name.startswith('RearStop') and o.MaterialBasis=='PLA':c=(.97,.77,.10)
  if o.Name=='EStop_HW1B_V402R':c=(.9,.07,.06)
  if o.Name.startswith('RearPower') or o.Name=='MainPower_3214':c=(.15,.18,.20)
  if o.Name.startswith(('PicoTray',)):c=(.24,.57,.80)
  if o.Name in ['PicoOwned','Pico_RS485_HAT']:c=(.05,.48,.22)
  if o.Name.startswith('Reserved_'):o.ViewObject.Transparency=40
  o.ViewObject.ShapeColor=c;o.ViewObject.LineColor=(.12,.14,.16)
  if kind in ['electronics','pico'] and o.Name.startswith(('AluminumDeck','DeckBolt','DeckSlotNut','PrintedStop','StopBolt','StopWasher','StopNut','Cargo','StrapRoute')):o.ViewObject.Visibility=False
  if kind=='electronics' and o.Name.startswith(('UpperRail','Post3030')):o.ViewObject.Transparency=70
  if kind=='pico':
   o.ViewObject.Visibility=o.Name.startswith('Pico')
   if o.Name=='PicoTrayLidPLA' or o.Name.startswith(('PicoLidBolt','PicoLidWasher','PicoLidNut')):o.ViewObject.Visibility=False
   if o.Name=='PicoTrayPLA':o.ViewObject.Transparency=65
  if kind=='controls':
   o.ViewObject.Visibility=o.Name.startswith(('RearStop','RearPower','EStop_','MainPower_')) and not o.Name.endswith('Route')
 z=App.Vector(-1.4,-1,1.1);z.normalize();x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
 v.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q);v.fitAll()
 w.statusBar().showMessage(status[kind],0);doc.recompute();v.redraw();Gui.updateGui()
def capture(kind):
 w.statusBar().showMessage(status[kind],0);QtWidgets.QApplication.processEvents();assert w.grab().save(str(HERE/('cad-screen-'+kind+'.png')))

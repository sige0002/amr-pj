from pathlib import Path
import importlib.util
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent;NAME='AMR01_OptionalMonitor_O1'
doc=App.listDocuments().get(NAME) or App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name);Gui.activateWorkbench('PartWorkbench')
w=Gui.getMainWindow();w.resize(1600,1050)
for dock in w.findChildren(QtWidgets.QDockWidget):dock.hide()
v=Gui.activeDocument().activeView();v.setCameraType('Orthographic');Gui.Selection.clearSelection()
refs=['BatteryBL1860B','BatteryAdapter03','Reserved_Computer','Reserved_ComputerSupply','PicoOwned','Pico_RS485_HAT','PicoHeaderEnvelope','EStop_HW1B_V402R','MainPower_3214','OptMonitorEnvelope']
def setup(kind='overall'):
 for o in doc.Objects:
  if not hasattr(o,'MaterialBasis'):continue
  o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name in refs
  o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines'
  c={'PLA':(.23,.55,.59),'aluminum':(.74,.78,.82),'steel':(.44,.48,.50),'rubber':(.12,.13,.14)}.get(o.MaterialBasis,(.3,.42,.60))
  if o.Name.startswith('RearStop') and o.MaterialBasis=='PLA':c=(.97,.77,.10)
  if o.Name=='EStop_HW1B_V402R':c=(.9,.07,.06)
  if o.Name.startswith('RearPower') or o.Name=='MainPower_3214':c=(.15,.18,.20)
  if o.Name.startswith('Reserved_'):o.ViewObject.Transparency=55
  if o.Name.startswith('Opt'):c=(.24,.46,.68) if o.MaterialBasis=='PLA' else (.62,.68,.73)
  if o.Name=='OptMonitorEnvelope':c=(.05,.10,.15)
  if kind=='mount':
   o.ViewObject.Visibility=o.Name.startswith(('Opt','UpperRail','Upright','EStop_','RearStop','RearPower','MainPower')) and o.Name!='OptCableRoute'
   if o.Name in ['OptMonitorEnvelope','OptMonitorBezelPLA']:o.ViewObject.Visibility=False
   if o.Name=='OptMonitorTrayPLA':o.ViewObject.Transparency=65
  o.ViewObject.ShapeColor=c;o.ViewObject.LineColor=(.10,.12,.14)
 z=App.Vector(-1.5,-1,1.0);z.normalize();x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x)
 v.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q);v.fitAll();doc.recompute();v.redraw();Gui.updateGui()
def capture(kind):
 w.statusBar().showMessage('OPTION O1 ONLY | 7-inch envelope / no monitor selected | standard BOM excludes this assembly',0)
 QtWidgets.QApplication.processEvents();assert w.grab().save(str(HERE/('cad-screen-'+kind+'.png')))

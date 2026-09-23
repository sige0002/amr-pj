from pathlib import Path
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtWidgets
HERE=Path(__file__).resolve().parent;NAME='AMR01_RearControls_D66'
d=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(d.Name);Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection()
w=Gui.getMainWindow();w.resize(1600,1100)
for dock in w.findChildren(QtWidgets.QDockWidget):
 if dock.objectName() in ('Python console','Report view','Tasks'):dock.hide()
v=Gui.activeDocument().activeView()
for o in d.Objects:
 if not hasattr(o,'MaterialBasis'):continue
 o.ViewObject.Visibility=o.MaterialBasis!='reference' or o.Name.startswith(('Battery','Reserved_','Computer','Supervisor','EStop_X','ARM_','MainPower_'))
 o.ViewObject.Transparency=0;o.ViewObject.DisplayMode='Flat Lines'
 o.ViewObject.ShapeColor={'aluminum':(.74,.78,.82),'steel':(.43,.47,.51),'PLA':(.23,.55,.59),'rubber':(.16,.17,.19)}.get(o.MaterialBasis,(.28,.40,.52))
 if o.Name.startswith('RearStop'):o.ViewObject.ShapeColor=(.97,.77,.10) if o.MaterialBasis=='PLA' else (.43,.47,.51)
 if o.Name.startswith('RearPower') and o.MaterialBasis=='PLA':o.ViewObject.ShapeColor=(.23,.29,.34)
 if o.Name=='EStop_XA1E_BV302R':o.ViewObject.ShapeColor=(.91,.07,.06)
 if o.Name.startswith(('ARM_','MainPower_')):o.ViewObject.ShapeColor=(.1,.11,.12)
 if o.Name.startswith('Reserved_'):o.ViewObject.Transparency=20
 if o.Name=='BatteryBL1860B':o.ViewObject.ShapeColor=(.12,.16,.17)
 if o.Name=='BatteryAdapter03':o.ViewObject.ShapeColor=(.04,.55,.58)
 if o.Name=='ComputerBarrierPLA':o.ViewObject.ShapeColor=(.94,.85,.61)
 if 'Belt' in o.Name or 'Buckle' in o.Name:o.ViewObject.ShapeColor=(.84,.41,.12)
z=App.Vector(-1.4,-.9,1.1);z.normalize();x=App.Vector(0,0,1).cross(z);x.normalize();y=z.cross(x);v.setCameraOrientation(App.Rotation(x,y,z,'ZXY').Q)
v.fitAll();d.recompute();Gui.updateGui();QtWidgets.QApplication.processEvents();w.statusBar().showMessage('D6.6 REAR controls | RED: E-STOP | BLACK: ARM / MAIN POWER | battery opening clear',0)
assert w.grab().save(str(HERE/'cad-screen-rear-controls.png'))
print('Rear controls GUI screenshot saved; source document not resaved')

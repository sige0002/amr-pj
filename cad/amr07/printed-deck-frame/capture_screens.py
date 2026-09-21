"""Actual FreeCAD GUI captures, with installed geometry rather than a render."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from pivy import coin

HERE=Path(__file__).resolve().parent
NAME='AMR01_PrintedDeck_P1'
doc=App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(HERE/(NAME+'.FCStd')))
App.setActiveDocument(doc.Name); Gui.activateWorkbench('PartWorkbench'); Gui.Selection.clearSelection()
window=Gui.getMainWindow(); window.resize(1600,1100)
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'): dock.hide()
features=[o for o in doc.Objects if hasattr(o,'MaterialBasis')]
for o in features:
    o.ViewObject.Visibility=o.MaterialBasis!='reference'
    o.ViewObject.DisplayMode='Flat Lines'; o.ViewObject.LineColor=(.16,.19,.22)
    o.ViewObject.ShapeColor={'aluminum':(.73,.77,.82),'steel':(.43,.47,.52),'PLA':(.20,.57,.66)}.get(o.MaterialBasis,(.15,.17,.19))
    if o.Name.startswith('PrintedDeck'):o.ViewObject.ShapeColor=(.25,.65,.73)
    if o.Name.startswith('Upper3030'):o.ViewObject.ShapeColor=(.30,.57,.85)
    if o.Name.startswith('UpperBracket'):o.ViewObject.ShapeColor=(.95,.60,.17)
    if o.Name.startswith('CustomMotorMount'):o.ViewObject.ShapeColor=(.78,.80,.84)
    if o.Name.startswith('PrintedStop'):o.ViewObject.ShapeColor=(.33,.40,.49)
view=Gui.activeDocument().activeView()
view.viewAxonometric()


def save(name,fit=True):
    if fit: view.fitAll()
    Gui.updateGui(); QtWidgets.QApplication.processEvents()
    # Offscreen export clips this manually zoomed camera on this FreeCAD build.
    # Its on-screen window capture remains valid; export fitted views only.
    if fit: view.saveImage(str(HERE/('viewport-'+name+'.png')),1600,1100,'White')
    assert window.grab().save(str(HERE/('cad-screen-'+name+'.png')))


save('isometric')
view.viewTop();view.fitAll()
# Keep all four grid panels and the complete vehicle in the top view.
view.getCameraNode().height.setValue(410)
save('grid-top',False)
view.viewAxonometric()
for o in features:
    if o.Name.startswith(('PrintedDeck','PrintedStop','Deck','Stop')):o.ViewObject.Visibility=False
save('frame-connections')
# Same installed geometry, zoomed at one complete cross connection.
for o in features:
    o.ViewObject.Visibility=(o.Name in ('Rail400_1','Upper3030_1') or
        (o.Name.startswith(('UpperBracket','UpperBolt','UpperNut')) and o.Name.endswith(('1_0','1_1'))))
for name in ('Rail400_1','Upper3030_1'):doc.getObject(name).ViewObject.Transparency=45
view.viewAxonometric()
target=App.Vector(75,-135,106)
camera=view.getCameraNode(); q=view.getCameraOrientation(); pos=target+q.multVec(App.Vector(0,0,600))
camera.position.setValue(pos.x,pos.y,pos.z); camera.focalDistance.setValue(600); camera.height.setValue(100)
save('joint-detail',False)
for o in features:
    o.ViewObject.Visibility=o.MaterialBasis!='reference'; o.ViewObject.Transparency=0
view.viewAxonometric();view.fitAll();doc.recompute();doc.save()
print('Saved actual GUI: isometric, grid-top, frame-connections, joint-detail.')

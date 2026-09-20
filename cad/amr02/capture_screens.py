"""Save actual FreeCAD screens. No generated or composited product images."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE=Path(__file__).resolve().parent
name='AMR01_SecondDesign_B'
if name not in App.listDocuments(): App.openDocument(str(HERE/(name+'.FCStd')))
App.setActiveDocument(name)
doc=App.activeDocument()
window=Gui.getMainWindow()
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console','Report view','Tasks'): dock.hide()
Gui.Selection.clearSelection()
view=Gui.activeDocument().activeView()
view.viewAxonometric()
q=view.getCameraOrientation()

def save(suffix):
    view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
    view.saveImage(str(HERE/('viewport-'+suffix+'.png')),1600,1100,'White')
    Gui.updateGui();QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(HERE/('cad-screen-'+suffix+'.png')))

save('isometric')
view.setCameraOrientation(q.multiply(App.Rotation(App.Vector(1,0,0),180)).Q)
save('underside')
view.viewTop();save('top')

# The second drive view exposes internals using native FreeCAD transparency.
view.setCameraOrientation(q.Q)
transparency={}
for o in doc.Objects:
    if o.Name.startswith(('ForkBridge','ForkInnerWall','ForkOuterWall','ForkWeb_')):
        transparency[o.Name]=o.ViewObject.Transparency
        o.ViewObject.Transparency=75
save('drive-visible')
for n,t in transparency.items(): doc.getObject(n).ViewObject.Transparency=t
view.setCameraOrientation(q.Q);view.fitAll();Gui.updateGui();doc.save()
print('Saved B FreeCAD screens: isometric, underside, top, drive-visible')

cname='AMR01_Option_C_TopMotor'
if (HERE/(cname+'.FCStd')).exists():
    if cname not in App.listDocuments(): App.openDocument(str(HERE/(cname+'.FCStd')))
    App.setActiveDocument(cname)
    for o in App.activeDocument().Objects:
        if 'DisplayColor' in o.PropertiesList:
            o.ViewObject.ShapeColor=o.DisplayColor
            o.ViewObject.Transparency=o.DisplayTransparency
            o.ViewObject.DisplayMode='Flat Lines'
    Gui.Selection.clearSelection()
    view=Gui.activeDocument().activeView();view.viewAxonometric()
    save('option-c-top-motor')
    App.activeDocument().save()
    App.setActiveDocument(name)
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
print('Active document restored to second design B')

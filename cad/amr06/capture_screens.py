"""Capture actual FreeCAD A5 assembly, mount comparison and PLA mock windows."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
V = App.Vector
window = Gui.getMainWindow()
Gui.activateWorkbench('PartWorkbench')
for dock in window.findChildren(QtWidgets.QDockWidget):
    if dock.objectName() in ('Python console', 'Report view', 'Tasks'):
        dock.hide()
Gui.Selection.clearSelection()


def activate(doc):
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewAxonometric()
    return Gui.activeDocument().activeView()


def save(doc, folder, suffix):
    view = Gui.activeDocument().activeView()
    view.fitAll()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    view.saveImage(str(folder / ('viewport-' + suffix + '.png')), 1600, 1000, 'White')
    for dock in window.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() in ('Python console', 'Report view', 'Tasks'):
            dock.hide()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    assert window.grab().save(str(folder / ('cad-screen-' + suffix + '.png')))


name = 'AMR01_M0601C_A5'
doc = App.getDocument(name) if name in App.listDocuments() else App.openDocument(str(HERE / (name + '.FCStd')))
old = App.getDocument('AMR01_M0601C_A4') if 'AMR01_M0601C_A4' in App.listDocuments() else None
features = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature']
for obj in features:
    source = old.getObject(obj.Name) if old else None
    if source:
        for prop in ('ShapeColor', 'LineColor', 'Transparency', 'DisplayMode', 'LineWidth', 'Visibility'):
            setattr(obj.ViewObject, prop, getattr(source.ViewObject, prop))
    else:
        obj.ViewObject.ShapeColor = {'steel':(.48,.53,.58), 'PLA':(.16,.57,.4), 'aluminum':(.77,.80,.84), 'reference':(.7,.35,.15)}.get(obj.MaterialBasis,(.25,.25,.25))
        obj.ViewObject.DisplayMode = 'Flat Lines'
        obj.ViewObject.Transparency = 75 if obj.MaterialBasis == 'reference' else 0
    if obj.Name.startswith('CustomMotorMount'):
        obj.ViewObject.ShapeColor = (.92,.56,.19)
view = activate(doc)
orientation = view.getCameraOrientation()
save(doc, HERE, 'isometric')
view.setCameraOrientation(orientation.multiply(App.Rotation(V(1,0,0),180)).Q)
save(doc, HERE, 'underside')
visibility = {o.Name:o.ViewObject.Visibility for o in features}
for obj in features:
    obj.ViewObject.Visibility = obj.Name.endswith('L')
view.setCameraOrientation(App.Rotation(V(0,0,1), V(-1,-2,-.5)).Q)
save(doc, HERE, 'drive-module')
for obj in features:
    obj.ViewObject.Visibility = visibility[obj.Name]
view.setCameraOrientation(orientation.Q)
view.fitAll()
doc.save()

comparison_name = 'M0601C_Mount_DFM_Comparison_A5'
if comparison_name in App.listDocuments():
    raise RuntimeError('Preserve open comparison edits before regenerating')
comparison = App.newDocument(comparison_name)
comparison.Label = 'Mount DFM | A4 cost reference / D4 / D5 study'
for object_name, label, file, offset, color in [
    ('A4_Baseline', 'A4 | seat R1.65 | sharp roots', HERE.parent/'amr05'/'M0601C_custom_mount_quote.step', 0, (.67,.70,.74)),
    ('D4_Comparison', 'D4 | seat R2 only | quote comparison', HERE/'candidates'/'M0601C_mount_D4_R2_NoRootFillet.step', 110, (.23,.59,.74)),
    ('D5_Study', 'D5 | W75 t6 R2 | fit mock only, not cost adoption', HERE/'candidates'/'M0601C_mount_D5_Compact_R2.step', 220, (.92,.56,.19)),
]:
    obj = comparison.addObject('PartDesign::Feature', object_name)
    obj.Label = label
    obj.Shape = Part.read(str(file))
    obj.Placement.Base = V(offset,0,0)
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = (.12,.14,.17)
    obj.ViewObject.DisplayMode = 'Flat Lines'
comparison.recompute()
view = activate(comparison)
view.setCameraOrientation(App.Rotation(V(0,0,1), V(0,2,-.8)).Q)
save(comparison, HERE, 'mount-comparison')
comparison.saveAs(str(HERE / (comparison_name + '.FCStd')))
for obj in comparison.Objects:
    obj.ViewObject.Visibility = obj.Name == 'D5_Study'
view.setCameraOrientation(App.Rotation(V(0,0,1), V(-.7,2,-.6)).Q)
save(comparison, HERE, 'mount-D5')
for obj in comparison.Objects:
    obj.ViewObject.Visibility = True
view.fitAll()
comparison.save()

mock_folder = HERE / 'print-mock'
mock_name = 'M0601C_PLA_Mock_A5'
mock = App.getDocument(mock_name) if mock_name in App.listDocuments() else App.openDocument(str(mock_folder / (mock_name + '.FCStd')))
for obj in mock.Objects:
    if obj.TypeId == 'PartDesign::Feature':
        obj.ViewObject.Visibility = True
        obj.ViewObject.ShapeColor = (.92,.56,.19) if obj.Name == 'FullMountMock' else (.18,.65,.74)
        obj.ViewObject.LineColor = (.15,.15,.15)
        obj.ViewObject.DisplayMode = 'Flat Lines'
activate(mock)
save(mock, mock_folder, 'mock')
# Finalize the mock separately with build_print_mock.finalize_gui_preview(),
# which saves GUI visibility and verifies geometry before refreshing the ZIP.
activate(doc).fitAll()
Gui.updateGui()
print('Saved actual A5 FreeCAD assembly / DFM / mock screens')

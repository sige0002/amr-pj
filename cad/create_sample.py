"""Run in FreeCAD (GUI or via the MCP execute_code tool). Units: mm."""
import math
import FreeCAD as App
import FreeCADGui as Gui
import Part

name = 'CenterHolePlate'
if name in App.listDocuments():
    raise RuntimeError('CenterHolePlate is already open; close it before recreating.')
doc = App.newDocument(name)
plate = doc.addObject('Part::Box', 'Plate')
plate.Length, plate.Width, plate.Height = 60, 40, 5
hole = doc.addObject('Part::Cylinder', 'Hole')
hole.Radius, hole.Height = 5, 5
hole.Placement.Base = App.Vector(30, 20, 0)
cut = doc.addObject('Part::Cut', 'CenterHolePlate')
cut.Base, cut.Tool = plate, hole
doc.recompute()
plate.Visibility = False
hole.Visibility = False
cut.ViewObject.ShapeColor = (0.78, 0.81, 0.85)
assert cut.Shape.isValid()
assert len(cut.Shape.Solids) == 1
assert abs(cut.Shape.Volume - (60 * 40 * 5 - math.pi * 25 * 5)) < 1e-6
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
doc.recompute()
doc.saveAs('/home/sadasue/amr-pj/cad/CenterHolePlate.FCStd')
Part.export([cut], '/home/sadasue/amr-pj/cad/CenterHolePlate.step')
Gui.activeDocument().activeView().saveImage('/home/sadasue/amr-pj/cad/CenterHolePlate.png', 1280, 960, 'White')
print('Validated plate: 60 x 40 x 5 mm, central hole diameter 10 mm')
print('Volume:', cut.Shape.Volume)

"""Place the native SolidWorks display mesh; this is NOT a STEP conversion."""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
import Mesh
import Part
from PySide import QtWidgets

HERE=Path(__file__).resolve().parent
V=App.Vector
NAME='AMR01_StockBracket_Fit_A4'
if NAME in App.listDocuments(): App.closeDocument(NAME)
doc=App.newDocument(NAME)
base=App.getDocument('AMR01_M0601C_A4')
source=Mesh.Mesh(str(HERE/'reference/DDT-M0601C-BRACKET-source-display-mm.stl'))
# A source display mesh is sufficient to reject a floor penetration or a
# gross rail intersection. It cannot certify exact mating/tolerance fit.
shape=Part.Shape();shape.makeShapeFromMesh(source.Topology,0.0001)
solid=Part.makeSolid(shape.Shells[0])
assert solid.isValid() and len(solid.Solids)==1
objects=[];rows=[]
for angle,tag in [(0,'Upright'),(90,'Sideways'),(180,'Inverted')]:
    rot=App.Rotation(V(1,0,0),V(0,0,1),V(0,-1,0),'ZXY')
    p=App.Placement(V(55,141,-39.65),rot)
    p=App.Placement(V(90,138,50.35),App.Rotation(V(0,1,0),angle)).multiply(
        App.Placement(V(-90,-138,-50.35),App.Rotation())).multiply(p)
    placed=solid.copy();placed.Placement=p
    obj=doc.addObject('Mesh::Feature','StockBracket_'+tag)
    obj.Mesh=source.copy();obj.Placement=p
    obj.addProperty('App::PropertyString','SourceMeaning','Evidence')
    obj.SourceMeaning='Native SLDPRT saved display mesh, not exact vendor B-rep/STEP.'
    obj.ViewObject.ShapeColor=(.82,.25,.17);obj.ViewObject.DisplayMode='Flat Lines'
    obj.ViewObject.Visibility=(angle==180);objects.append(obj)
    b=placed.optimalBoundingBox(False,False)
    overlap=placed.common(base.getObject('Rail400_4').Shape).Volume
    rows.append({'orientation':tag,'rotation_deg':angle,'min_z_mm':b.ZMin,'max_z_mm':b.ZMax,
                 'approx_overlap_with_original_outer_rail_mm3':overlap,
                 'meets_nominal_25mm_ground_clearance':b.ZMin>=25,
                 'fits_unchanged_frame':overlap<.01})
for name in ('Rail400_4','M0601MotorL','TireL'):
    obj=doc.addObject('PartDesign::Feature',name);obj.Shape=base.getObject(name).Shape
    obj.ViewObject.ShapeColor=(.65,.7,.75);obj.ViewObject.Transparency=65 if name!='Rail400_4' else 0
custom=doc.addObject('PartDesign::Feature','CustomMountComparison')
custom.Shape=base.getObject('CustomMotorMountL').Shape
custom.ViewObject.ShapeColor=(.2,.5,.75);custom.ViewObject.Visibility=False
floor=doc.addObject('PartDesign::Feature','FloorReference')
floor.Shape=Part.makePlane(450,120,V(-200,100,0));floor.ViewObject.ShapeColor=(.7,.7,.7);floor.ViewObject.Transparency=80
doc.recompute()
Gui.activateWorkbench('PartWorkbench')
view=Gui.activeDocument().activeView()
view.setCameraOrientation(App.Rotation(V(0,0,1),V(-1,-2,.6)).Q)
view.fitAll();Gui.updateGui();QtWidgets.QApplication.processEvents()
doc.saveAs(str(HERE/(NAME+'.FCStd')))
Gui.getMainWindow().grab().save(str(HERE/'cad-screen-stock-bracket-fit.png'))
result={'source_representation':'Native SLDPRT saved display mesh, 2726 triangles; approximate collision volumes only',
        'fixed_end_face_y_mm':138,'source_seat_depth_mm':3,'source_back_wall_mm':7,
        'stock_flat_back_y_mm':131,'original_frame_outer_face_y_mm':150,
        'outer_rail_inward_shift_needed_with_5mm_adapter_mm':24,
        'unchanged_frame_cases':rows,
        'decision':'Custom compact metal bracket is the A4 quote candidate. No unmodified stock orientation tested fits the unchanged frame. Moving rails inward also requires redesigning official frame joints.',
        'unproven':'No exact STEP conversion, load rating, tyre deformation or full continuous-angle fit proof.'}
(HERE/'stock_bracket_fit_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

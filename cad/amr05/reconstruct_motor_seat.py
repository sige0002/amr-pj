"""Reconstruct the published DDT seat floor from native curves, not a vendor STEP conversion.
FreeCAD headless compatible. Local X=horizontal, Y=up, Z=into bracket.
Motor fixed end seats at Z=pocket_depth; motor extends toward negative Z.
Native dimensions: plate 10, pocket depth 3, back wall 7 mm.
The native 0.5 mm entrance chamfer and wider upper cable transition are NOT recreated.
"""
from pathlib import Path
import json, math
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parent

def source_floor_wire(profile_path=None):
    spec=json.loads(Path(profile_path or ROOT/'motor-seat-profile-source.json').read_text())
    edges=[]
    for s in spec['segments']:
        a=App.Vector(*s['start_mm']);b=App.Vector(*s['end_mm'])
        if s['kind']=='line':edge=Part.makeLine(a,b)
        elif s['kind']=='circle':
            c=App.Vector(*s['center_mm']);aa=math.atan2(a.y-c.y,a.x-c.x);bb=math.atan2(b.y-c.y,b.x-c.x)
            delta=(bb-aa+math.pi)%(2*math.pi)-math.pi
            if abs(abs(delta)-math.pi)<1e-8:delta=math.copysign(math.pi,s['axis'][2])
            mid=c+App.Vector(s['radius_mm']*math.cos(aa+delta/2),s['radius_mm']*math.sin(aa+delta/2),0)
            edge=Part.Arc(a,mid,b).toShape()
        else:raise ValueError('Unsupported native floor curve '+s['kind'])
        edges.append(edge)
    wire=Part.Wire(edges)
    if not wire.isClosed() or not wire.isValid():raise ValueError('Source floor wire is not valid and closed')
    return wire,spec

def apply_motor_seat(blank,plate_thickness=10,pocket_depth=3,cable_exit_y=25,profile_path=None):
    """Cut source seat floor, 3 clearance holes, and a new straight open cable slot.
    blank must occupy Z=0..plate_thickness; local shaft centre=(0,0).
    cable_exit_y must reach the chosen new bracket top. This upper slot is a
    deliberate new design using the source's 5 mm throat, not source's wide top.
    Geometry only: no fit tolerance, alloy or bolt-engagement certification.
    """
    if not 0<pocket_depth<plate_thickness:raise ValueError('Pocket must leave a positive back wall')
    w,spec=source_floor_wire(profile_path)
    f=Part.Face(w)
    pocket=f.extrude(App.Vector(0,0,pocket_depth))
    part=blank.cut(pocket)
    over=0.05
    for x,y in spec['mount_holes_local_xy_mm']:
        part=part.cut(Part.makeCylinder(spec['mount_holes_diameter_mm']/2,plate_thickness+2*over,App.Vector(x,y,-over)))
    slot=Part.makeCylinder(2.5,plate_thickness+2*over,App.Vector(0,0,-over)).fuse(Part.makeBox(5,cable_exit_y+over,plate_thickness+2*over,App.Vector(-2.5,0,-over)))
    part=part.cut(slot).removeSplitter()
    if not part.isValid() or len(part.Solids)!=1:raise ValueError('Reconstructed seat must be one valid solid')
    return part

if __name__=='__main__':
    blank=Part.makeBox(32,40,10,App.Vector(-16,-15,0))
    s=apply_motor_seat(blank)
    w,spec=source_floor_wire()
    s.exportBrep(str(ROOT/'motor-seat-source-profile-demo.brep'))
    s.exportStep(str(ROOT/'motor-seat-source-profile-demo.step'))
    report={'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':s.Volume,'floor_wire_valid':w.isValid(),'floor_wire_closed':w.isClosed(),'floor_area_before_mounting_holes_mm2':Part.Face(w).Area,'bbox_mm':[s.BoundBox.XLength,s.BoundBox.YLength,s.BoundBox.ZLength],'source_floor_edges':len(w.Edges),'pocket_depth_mm':3,'back_wall_mm':7,'not_vendor_full_conversion':True,'omitted_source_features':['0.5 mm entrance chamfer','wider upper cable transition','all external bracket shape and unrelated holes']}
    (ROOT/'motor-seat-reconstruction-check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

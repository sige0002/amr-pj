"""Published NFSL6/HNTT6 interface dimensions, nominal reconstructed profiles.

Small radii, detailed hollow extrusion webs and thread lead-ins are omitted.
Use catalog rail mass, not the deliberately simplified rail solid volume.
"""
import FreeCAD as App
import Part

V = App.Vector


def profile(length):
    s = Part.makeBox(length,30,30,V(0,-15,-15))
    # Published slot: mouth8, lip2, maximum width16.5, total depth9.
    # Intermediate shoulder depth and bottom bevel are drawing reconstruction.
    yz = [(-4,16),(4,16),(4,13),(8.25,13),(8.25,9.5),
          (4.75,6),(-4.75,6),(-8.25,9.5),(-8.25,13),(-4,13)]
    pts = [V(-1,y,z) for y,z in yz]
    slot = Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(length+2,0,0))
    cutters = [Part.makeCylinder(3.4,length+2,V(-1,0,0),V(1,0,0))]
    for angle in (0,90,180,270):
        c = slot.copy(); c.rotate(V(0,0,0),V(1,0,0),angle); cutters.append(c)
    s = s.cut(Part.makeCompound(cutters)).removeSplitter()
    assert s.isValid() and len(s.Solids)==1
    return s


def slotnut_at(surface, inward, rail_axis=(1,0,0)):
    """The surface point lies on the frame external plane, at screw center."""
    # Full thickness6.3, nose.8, nose width7.8, shoulder width15, length14.
    # Rear width7.8 and straight tapered sides reconstructed from catalog view;
    # neither rear width nor corner radii is a separately toleranced dimension.
    yz=[(-3.9,1.2),(3.9,1.2),(3.9,2),(7.5,2),(3.9,7.5),
        (-3.9,7.5),(-7.5,2),(-3.9,2)]
    pts=[V(-7,y,z) for y,z in yz]
    s=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(14,0,0))
    s=s.cut(Part.makeCylinder(3.1,8,V(0,0,0))).removeSplitter()
    z=V(*inward); x=V(*rail_axis); y=z.cross(x)
    assert abs(z.dot(x))<1e-9
    rot=App.Rotation(x,y,z,'ZXY')
    s.Placement=App.Placement(V(*surface),rot)
    assert s.isValid() and len(s.Solids)==1
    return s


def deck_slotnut(x,y,z,inward):
    return slotnut_at((x,y,z),inward)


def screw_axis_and_head(shape, diameter=6):
    shaft=[f for f in shape.Faces if isinstance(f.Surface,Part.Cylinder) and abs(f.Surface.Radius-diameter/2)<1e-6]
    head=[f for f in shape.Faces if isinstance(f.Surface,Part.Cylinder) and abs(f.Surface.Radius-5)<1e-6]
    assert len(shaft)==1 and len(head)==1
    axis=shaft[0].CenterOfMass-head[0].CenterOfMass
    axis.normalize()
    return axis

"""Small removable PLA fixtures; never part of the main cargo support path.

The outer grid rows keep installed fixtures outside the central200mm cargo
footprint. Four ordinary0.8mm steel washers form each3.2mm compression stack.
Measure/sort stacks and fit printed thickness before tightening; no PLA preload
rating is inferred from nominal contact. Actual electronic devices remain open.
"""
from pathlib import Path
import math
import json

HERE=Path(__file__).resolve().parent


def build_accessory_specs():
    import FreeCAD as App
    import Part
    V=App.Vector
    rows=[]

    def cylinder(r,h,x,y,z): return Part.makeCylinder(r,h,V(x,y,z))
    def washer(ro,ri,h,x,y,z): return cylinder(ro,h,x,y,z).cut(cylinder(ri,h,x,y,z))
    def hexagon(x,y,z,af,h,bore):
        radius=af/math.sqrt(3)
        pts=[V(x+radius*math.cos(math.pi*i/3),y+radius*math.sin(math.pi*i/3),z) for i in range(6)]
        s=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,h))
        return s.cut(cylinder(bore/2,h,x,y,z)) if bore else s
    def add(name,shape,material,label,note='',hardware=None):
        assert shape.isValid() and len(shape.Solids)==1,name
        r={'name':name,'shape':shape,'material':material,'label':label,'note':note,
           'group':'11_PrintedFixtures' if material!='reference' else '12_FixtureReferences',
           'color':(.18,.62,.58) if material=='PLA' else (.45,.49,.54)}
        if hardware:r['hardware_spec']=hardware
        rows.append(r)

    for sign,side in [(1,'L'),(-1,'R')]:
        y=125*sign
        for kind,xc in [('Adapter',50),('Guide',-50)]:
            base=Part.makeBox(64,16,3.2,V(xc-32,y-8,110.8))
            bolts=[(xc-25,y),(xc+25,y)]
            for x,yy in bolts:
                base=base.cut(cylinder(4.7,5,x,yy,110))
            if kind=='Adapter':
                # M3 nut pockets open toward the metal plate. Install nuts
                # before the fixture; choose device bolts that end below114.
                for i,x in enumerate((40,60)):
                    base=base.cut(cylinder(1.7,5,x,y,110))
                    base=base.cut(hexagon(x,y,111.4,5.8,3,0))
                    add('FixtureM3Nut'+side+str(i),hexagon(x,y,111.6,5.5,2.4,3.1),'steel',
                        'M3 captured nut | adapter20mm pitch',
                        'Actual device, screw length and thermal mounting unselected. End of M3 bolt must remain below deck underside114.',
                        'M3 plain hex nut')
                note='64x16x3.2 PLA,50mm M4 mounting to20mm M3 nut pockets. Fit model for light electronics, no cargo/arm anchorage rating.'
            else:
                cy=116*sign
                saddle=Part.makeBox(16,12,9,V(-58,cy-6,102))
                bore=Part.makeCylinder(3.5,18,V(-59,cy,105.5),V(1,0,0))
                opening=Part.makeBox(18,7,4.5,V(-59,cy-3.5,101))
                saddle=saddle.cut(bore.fuse(opening))
                #3.2x1.2 tie window above the bundle, throughY. A2.5mm tie
                # retains the cable; its cut tail must remain out of the wheel.
                saddle=saddle.cut(Part.makeBox(3.2,14,1.2,V(-51.6,cy-7,109.3)))
                base=base.fuse(saddle).removeSplitter()
                wire=Part.makeCylinder(3,60,V(-80,cy,105.5),V(1,0,0))
                add('FixtureCableEnvelope'+side,wire,'reference','Cable bundle envelope D6 | local guide only',
                    'Local clearance gauge, not a routed or selected harness. Connector, bending radius, strain relief and final route remain unverified.')
                note='64x16x3.2 PLA plus open7mm cable saddle;2.5mm tie retained through3.2x1.2 window. No snap fit or unsupported adhesive.'
            add('Printed'+kind+side,base.removeSplitter(),'PLA',
                'PLA '+kind+' | outer grid row | removable',note)
            for i,(x,yy) in enumerate(bolts):
                suffix=kind+side+str(i)
                for k in range(4):
                    add('FixtureStackWasher'+suffix+'_'+str(k),washer(4.5,2.15,.8,x,yy,110.8+k*.8),'steel',
                        'M4 washer compression stack '+str(k+1)+'/4',
                        'Four washers nominal3.2; measure/sort to match printed thickness. Metal-to-metal clamp path.',
                        'M4 plain washer 9x4.3x0.8')
                add('FixtureTopWasher'+suffix,washer(4.5,2.15,.8,x,yy,118),'steel',
                    'M4 top washer',hardware='M4 plain washer 9x4.3x0.8')
                add('FixtureBottomWasher'+suffix,washer(6,2.15,1,x,yy,109.8),'steel',
                    'M4 large retention washer',hardware='M4 large washer 12x4.3x1')
                add('FixtureM4Nut'+suffix,hexagon(x,yy,106.6,7,3.2,4.2),'steel',
                    'M4 fixture nut',hardware='M4 plain hex nut')
                bolt=cylinder(2,16,x,yy,102.8).fuse(cylinder(3.5,4,x,yy,118.8))
                add('FixtureBolt'+suffix,bolt,'steel','M4x16 fixture bolt',
                    'Nominal tip102.8, above frame99 by3.8. Recheck stack tolerances and loaded deflection; fit fixtures on removed deck.',
                    'M4x16 socket screw')
    return rows


def export_print_files(specs,directory=None):
    import FreeCAD as App
    import MeshPart
    import Mesh
    target=Path(directory or HERE/'printed-accessories');target.mkdir(exist_ok=True)
    reports=[]
    for s in specs:
        if s['material']!='PLA':continue
        shape=s['shape'].copy()
        # Flat deck-contact face down on the bed. Pockets may bridge small
        # spans; slicer validation and a washer/nut coupon are still required.
        shape.rotate(App.Vector(0,0,0),App.Vector(1,0,0),180)
        b=shape.BoundBox;shape.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin))
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.08,AngularDeflection=.15,Relative=False)
        path=target/(s['name']+'.stl');mesh.write(str(path))
        restored=Mesh.Mesh(str(path));b=restored.BoundBox
        assert restored.isSolid() and max(b.XLength,b.YLength,b.ZLength)<256
        reports.append({'file':path.name,'quantity':1,'bed_dimensions_mm':[b.XLength,b.YLength,b.ZLength],
                        'watertight':True,'solid_CAD_mass_kg':s['shape'].Volume*1.24e-6,
                        'actual_slicing_done':False,'fit_and_load_qualified':False})
    (target/'manifest.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    return reports

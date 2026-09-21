"""A4: M0601C_111 vendor motor CAD and a compact one-piece CNC mount.
Run inside FreeCAD. Nominal concept assembly; received parts and joints unverified.
"""
from pathlib import Path
import json
import math
import FreeCAD as App
import Part
import MeshPart

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / 'design_parameters.json').read_text())
V = App.Vector
NAME = 'AMR01_M0601C_A4'
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = 'AMR-01 A4 | M0601C_111 | compact CNC mounts'
objects, groups = [], {}
AL, STEEL, BLUE = (.77,.8,.84), (.48,.53,.58), (.22,.43,.64)
BLACK, ORANGE, PLA = (.12,.14,.16), (.9,.48,.10), (.16,.57,.40)


def box(x,y,z,l,w,h):
    return Part.makeBox(l,w,h,V(x,y,z))


def cyl(r,h,p,axis=(0,0,1)):
    return Part.makeCylinder(r,h,V(*p),V(*axis))


def cut(s, cutters):
    return s.cut(Part.makeCompound(cutters)).removeSplitter() if cutters else s


def add(name,shape,group,color=AL,material='aluminum',label=None,source='',note=''):
    if group not in groups:
        groups[group]=doc.addObject('App::DocumentObjectGroup',group)
        groups[group].Label=group.replace('_',' ')
    o=doc.addObject('PartDesign::Feature',name)
    o.Label=label or name.replace('_',' ')
    o.Shape=shape
    for key,val in [('MaterialBasis',material),('SourceURL',source),('ModelNote',note or 'Nominal simplified part; not a fabrication release.')]:
        o.addProperty('App::PropertyString',key,'Design')
        setattr(o,key,val)
    groups[group].addObject(o)
    if App.GuiUp:
        o.ViewObject.ShapeColor=color
        o.ViewObject.LineColor=(.15,.18,.22)
        o.ViewObject.DisplayMode='Flat Lines'
        o.ViewObject.LineWidth=1
    objects.append(o)
    return o


def side_shape(s,side):
    if side == 'L':
        return s
    # Same purchased motor and same machined part: rotate, never mirror a motor.
    placed=s.copy()
    placed.rotate(V(CFG['geometry']['drive_axle_x_mm'],0,0),V(0,0,1),180)
    return placed


def side_add(name,s,side,group,color=AL,material='aluminum',**kw):
    return add(name+side,side_shape(s,side),group,color,material,**kw)


def hole_y(x,y,z,r,length):
    return cyl(r,length,(x,y,z),(0,1,0))


def hole_x(x,y,z,r,length):
    return cyl(r,length,(x,y,z),(1,0,0))


def slot_y(x,y,z,r,length,half_travel=1):
    a=hole_y(x-half_travel,y,z,r,length)
    b=hole_y(x+half_travel,y,z,r,length)
    return a.fuse(b).fuse(box(x-half_travel,y,z-r,2*half_travel,length,2*r))


def screw(name,p,d,diameter,length,side=None,nut=False,nut_stack=None,csk=False):
    p,d=V(*p),V(*d)
    r={2.5:2.25,3:2.75,4:3.5,6:5}[diameter]
    shape=Part.makeCylinder(diameter/2,length,p,d)
    head=Part.makeCone(diameter,diameter/2,diameter/2,p,d) if csk else Part.makeCylinder(r,diameter,p-d*diameter,d)
    shape=shape.fuse(head)
    if side:
        shape=side_shape(shape,side)
    bolt=add(name+(side or ''),shape,'07_Fasteners',STEEL,'steel',note='Unthreaded screw envelope; separate nuts/washers counted in fasteners.csv.')
    for field,value in [('NominalDiameter',diameter),('NominalLength',length)]:
        bolt.addProperty('App::PropertyFloat',field,'Hardware');setattr(bolt,field,value)
    bolt.addProperty('App::PropertyString','HardwareSpec','Hardware')
    bolt.HardwareSpec=f'M{diameter:g}x{length:g} '+('countersunk screw (overall length)' if csk else 'socket screw')
    if nut:
        # Plain hexagon nut seated on the stack, threads omitted.
        thick={3:2.4,4:3.2,6:5}[diameter]
        stack=nut_stack if nut_stack is not None else {3:6,4:7,6:6.5}[diameter]
        pos=p+d*stack
        radius={3:5.5,4:7,6:10}[diameter]/math.sqrt(3)
        pts=[V(radius*math.cos(math.radians(60*i)),radius*math.sin(math.radians(60*i)),0) for i in range(6)]
        ns=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,thick)).cut(cyl(diameter/2+.1,thick,(0,0,0)))
        ns.Placement=App.Placement(pos,App.Rotation(V(0,0,1),d))
        if side: ns=side_shape(ns,side)
        n=add('Nut_'+name+(side or ''),ns,'07_Fasteners',STEEL,'steel')
        n.addProperty('App::PropertyString','HardwareSpec','Hardware');n.HardwareSpec=f'M{diameter:g} plain hex nut'


def slotnut(name,p,axis,side=None):
    # HNTT6-6 nominal occupied volume, not a copy of its detailed thread/chamfers.
    s=box(-6.4,-6.4,-2,12.8,12.8,4).cut(cyl(3.1,5,(0,0,-2.5)))
    s.Placement=App.Placement(V(*p),App.Rotation(V(0,0,1),V(*axis)))
    if side: s=side_shape(s,side)
    n=add('SlotNut_'+name+(side or ''),s,'07_Fasteners',STEEL,'steel',label='MISUMI HNTT6-6 | nominal envelope',
        note='Series 6 nut specified; precise catalog profile not represented. Insert before closing frame.')
    n.addProperty('App::PropertyString','HardwareSpec','Hardware');n.HardwareSpec='HNTT6-6 slot nut'


def profile(length):
    s=box(0,-15,-15,length,30,30)
    cuts=[cyl(3.4,length+2,(-1,0,0),(1,0,0))]
    slot=box(-1,-4,12,length+2,8,4).fuse(box(-1,-6.5,7,length+2,13,6))
    for angle in (0,90,180,270):
        c=slot.copy();c.rotate(V(0,0,0),V(1,0,0),angle);cuts.append(c)
    return cut(s,cuts)


# The frame moves down6mm; purchased wheel axle/contact geometry is unchanged.
for i,y in enumerate((-135,-65,65,135),1):
    s=profile(400);s.translate(V(-200,y,84))
    add('Rail400_'+str(i),s,'01_Frame',label='NFSL6-3030-400 | stock, no cuts',source='https://www.amazon.co.jp/dp/B0DKF2CCW3')
for i,x in enumerate((-215,215),1):
    s=profile(300);s.rotate(V(0,0,0),V(0,0,1),90);s.translate(V(x,-150,84))
    add('Cross300_'+str(i),s,'01_Frame',label='NFSL6-3030-300 | stock, no cuts',source='https://www.amazon.co.jp/dp/B0DKDZ8G9G')
for end in (-1,1):
    for y in (-120,-50,50,120):
        fx,fy=end*200,y;dx,dy=-end,(-1 if y>0 else 1)
        s=box(min(fx,fx+dx*30),min(fy,fy+dy*4),74,30,4,20)
        s=s.fuse(box(min(fx,fx+dx*4),min(fy,fy+dy*30),74,4,30,20))
        for z in (74,91):
            pts=[V(fx+dx*4,fy+dy*4,z),V(fx+dx*27,fy+dy*4,z),V(fx+dx*4,fy+dy*27,z)]
            s=s.fuse(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,3)))
        s=cut(s,[hole_x(fx-1 if dx>0 else fx-6,fy+dy*18,84,3.15,7),hole_y(fx+dx*15,fy-1 if dy>0 else fy-6,84,3.15,7)])
        tag=('P' if end>0 else 'N')+str(y).replace('-','N')
        add('Bracket_'+tag,s,'01_Frame',label='MISUMI HBLFSN6-SET | series6',source=CFG['frame_joints']['source'],note='Official specified part, simplified nominal ribs/tabs. Personal purchasing path unconfirmed.')
        for letter,p,d in [('A',(fx+dx*4,fy+dy*18,84),(-dx,0,0)),('B',(fx+dx*15,fy+dy*4,84),(0,-dy,0))]:
            screw('Joint'+letter+'_'+tag,p,d,6,12)
            slotnut('Joint'+letter+'_'+tag,tuple(V(*p)+V(*d)*8),d)
    for sg in (-1,1):
        pts=[V(end*230,sg*150,99),V(end*170,sg*150,99),V(end*230,sg*90,99)]
        s=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,3))
        hs=[(end*185,sg*135),(end*215,sg*105)]
        s=cut(s,[cyl(3.3,5,(x,y,98)) for x,y in hs])
        tag=str(end).replace('-','N')+str(sg).replace('-','N')
        add('Gusset_'+tag,s,'01_Frame',BLUE,label='A5052 t3 corner gusset | retained')
        for i,(x,y) in enumerate(hs):
            add('Washer_Gusset'+tag+str(i),cyl(6.5,1.6,(x,y,102)).cut(cyl(3.3,1.6,(x,y,102))),'07_Fasteners',STEEL,'steel')
            screw('GussetBolt_'+tag+str(i),(x,y,103.6),(0,0,-1),6,12)
            slotnut('Gusset_'+tag+str(i),(x,y,95),(0,0,1))

# Source motor geometry and new custom bracket; flexible source harness is re-routed.
import sys
sys.path.insert(0, str(HERE))
from custom_mount import make_mount, report as mount_report
X, Z = CFG['geometry']['drive_axle_x_mm'], CFG['geometry']['wheel_axis_z_mm']
mount = make_mount()
(HERE/'custom_mount_dimensions.json').write_text(json.dumps(mount_report(mount), ensure_ascii=False, indent=2)+'\n')
quote_mount=mount.copy();quote_mount.translate(V(-45,-120,-35))
quote_mount.exportStep(str(HERE/'M0601C_custom_mount_quote.step'))
quote_file=HERE/'M0601C_custom_mount_quote.step'
quote_file.write_text('\n'.join(line.rstrip() for line in quote_file.read_text().splitlines())+'\n')
# Retain the whole source for provenance, remove only its stored flexible lead pose
# from the installed rigid model. The body/boss geometry is not replaced by a cylinder.
source_motor = Part.read(str(HERE/'vendor-cache/M0601C_111.STEP'))
rigid_motor = source_motor.cut(box(-50,0,-200,100,30,190)).removeSplitter()
rigid_motor.rotate(V(0,0,0),V(0,0,1),180)
rigid_motor.translate(V(X,148,Z))
# Nominal thread minor diameters would overlap screw major envelopes. Open only
# those six installed female thread holes to nominal clearance for collision checks.
# Original geometry remains in source_motor; this does not specify a drill size.
thread_tools=[]
for a in (90,210,330):
    x,z=X+7.6*math.cos(math.radians(a)),Z+7.6*math.sin(math.radians(a))
    thread_tools.append(hole_y(x,137.9,z,1.26,5.2))
rigid_motor=rigid_motor.cut(Part.makeCompound(thread_tools)).removeSplitter()
for side in ('L','R'):
    group='02_Drive_'+side
    side_add('CustomMotorMount',mount,side,group,BLUE,
        label='A6061-T6 one-piece mount | 9mm seat | quote model',
        note='New90x30x34 mount; source seat contour offset0.15mm; fit tolerances, quote and load tests pending.')
    for x in (52.5,127.5):
        screw('MountFrameBolt_'+str(x).replace('.','p'),(x,135,64),(0,0,1),6,12,side)
        slotnut('Mount_'+str(x).replace('.','p'),(x,135,73),(0,0,1),side)
    for i,a in enumerate((90,210,330)):
        x,z=X+7.6*math.cos(math.radians(a)),Z+7.6*math.sin(math.radians(a))
        screw('MotorFaceBolt_'+str(i),(x,130,z),(0,1,0),2.5,12,side)
    side_add('M0601Motor',rigid_motor,side,group,AL,'purchased',source=CFG['drive']['source'],
        label='M0601C_111 | vendor STEP rigid body | 485g catalog',
        note='Vendor STEP. Flexible stored lead pose clipped below its rigid exit; threaded bores opened locally for screw-envelope collision check. Original source retained separately; drawing thread-depth5mm governs.')
    tire=hole_y(X,153,Z,50.35,43).cut(hole_y(X,153,Z,33.6,43))
    groove=hole_y(X,173.9,Z,50.5,1.2).cut(hole_y(X,173.9,Z,49.65,1.2))
    side_add('Tire',tire.cut(groove),side,group,BLACK,'purchased',source='https://www.switch-science.com/products/9203',
        label='DDT-M0601C-TIRE | nominal100.7x43 | axial datum provisional',
        note='Catalog outer dimensions; bore/tread simplified. Axial stack is an assembly assumption pending kit drawing or physical measurement.')
    cap=hole_y(X,193.3,Z,33.5,2.7).fuse(hole_y(X,196,Z,18.5,7.3))
    # Clearance relief is a packaging assumption, not the unpublished actual cap geometry.
    cap=cap.cut(rigid_motor).removeSplitter()
    for a in (180,60,300):
        cap=cap.cut(hole_y(X+10.5*math.cos(math.radians(a)),193,Z+10.5*math.sin(math.radians(a)),1.4,11))
    side_add('TireCover',cap,side,group,BLACK,'purchased',source='https://www.switch-science.com/products/9203',
        label='Tire kit cover | nominal67x10 | included3 screws not dimensioned',
        note='Simplified cover envelope with assumed overlap/clearance against rotor. Kit includes3 screws per wheel, size/length unconfirmed; counted with kit, not standalone hardware.')

# Same caster at ground datum; its old6mm spacers disappear too.
ch=[(x,y) for x in (-173,-127) for y in (-17.5,17.5)]
fh=[(x,y) for x in (-180,-120) for y in (-65,65)]
plate=cut(box(-190,-85,65,80,170,4),[cyl(3.3,6,(x,y,64)) for x,y in ch+fh])
add('CasterAdapter',plate,'03_Caster',BLUE,label='A5052 t4 | direct to frame | no6mm spacers')
for i,(x,y) in enumerate(fh):
    add('Washer_CasterFrame'+str(i),cyl(6.5,1.6,(x,y,63.4)).cut(cyl(3.3,1.6,(x,y,63.4))),'07_Fasteners',STEEL,'steel')
    screw('CasterFrameBolt_'+str(i),(x,y,63.4),(0,0,1),6,12)
    slotnut('Caster_'+str(i),(x,y,73),(0,0,1))
ct=cut(box(-179.5,-23.5,62.5,59,47,2.5),[cyl(3.25,5,(x,y,61.5)) for x,y in ch])
add('CasterTop',ct,'03_Caster',STEEL,'purchased',label='Hammer420G-R50 | unchanged')
for i,(x,y) in enumerate(ch): screw('CasterBolt_'+str(i),(x,y,69),(0,0,-1),6,16,nut=True,nut_stack=6.5)
add('SwivelRace',cyl(19,9,(-150,0,53.5)),'03_Caster',STEEL,'purchased')
forks=[]
for y in (-14,11):
    pts=[V(-171,y,25),V(-157,y,25),V(-135,y,53.5),V(-159,y,53.5)]
    forks.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,3,0)))
add('CasterFork',Part.makeCompound(forks+[hole_y(-166,-16,25,3,32)]),'03_Caster',STEEL,'purchased')
add('CasterTire',hole_y(-166,-10,25,25,20).cut(hole_y(-166,-10,25,12,20)),'03_Caster',BLACK,'purchased')
add('CasterCore',hole_y(-166,-10,25,12,20).cut(hole_y(-166,-10,25,3,20)),'03_Caster',AL,'purchased')

# One-piece PLA U cradle within the100mm gap between the two inner rails.
tray=box(-95,-53,32,130,106,3)
for y in (-53,50): tray=tray.fuse(box(-95,y,35,130,3,30))
for y in (-80,50): tray=tray.fuse(box(-95,y,65,130,30,4))
# End lips retain the locating shell; straps must secure the battery to metal rails.
for x in (-95,32): tray=tray.fuse(box(x,-50,35,3,100,6))
for x in (-95,32):
    for y in (-63,53): tray=tray.fuse(box(x,y,50,3,10,15))
th=[(x,y) for x in (-80,20) for y in (-65,65)]
tray=cut(tray,[cyl(3.3,6,(x,y,64)) for x,y in th])
add('BatteryCradlePLA',tray,'04_Printed',PLA,'PLA',label='PLA low battery cradle130x160 | floor32..35',note='Temporary load-bearing PLA cradle for0.75kg battery budget; battery120x80x65 is unselected. Add straps anchored to3030. Straps do not eliminate floor/flange creep; check temperature, clamping and retention.')
for i,(x,y) in enumerate(th):
    add('LargeWasher_Cradle'+str(i),cyl(9,1.6,(x,y,63.4)).cut(cyl(3.3,1.6,(x,y,63.4))),'07_Fasteners',STEEL,'steel')
    screw('CradleBolt_'+str(i),(x,y,63.4),(0,0,1),6,12)
    slotnut('Cradle_'+str(i),(x,y,73),(0,0,1))
# Rear electronics deck avoids the battery's upward removal path.
eh=[(x,y) for x in (-178,-117) for y in (-65,65)]
deck=box(-190,-90,99,85,180,2.4)
for x in (-190,-108): deck=deck.fuse(box(x,-90,101.4,3,180,2))
for y in (-90,87): deck=deck.fuse(box(-190,y,101.4,85,3,2))
deck=cut(deck,[cyl(3.3,6,(x,y,98)) for x,y in eh])
add('ElectronicsTrayPLA',deck,'04_Printed',PLA,'PLA',label='PLA rear electronics deck85x180 | low battery access kept clear')
for i,(x,y) in enumerate(eh):
    add('LargeWasher_Electronics'+str(i),cyl(9,1.6,(x,y,101.4)).cut(cyl(3.3,1.6,(x,y,101.4))),'07_Fasteners',STEEL,'steel')
    screw('ElectronicsBolt_'+str(i),(x,y,103),(0,0,-1),6,10)
    slotnut('Electronics_'+str(i),(x,y,95),(0,0,1))

# Front electronics deck is now a real printed part, with frame screws in the BOM.
front=box(45,-85,99,145,170,2.4)
for x in (45,187): front=front.fuse(box(x,-85,101.4,3,170,2))
for y in (-85,82): front=front.fuse(box(45,y,101.4,145,3,2))
front=front.cut(box(44,-45,98,21,90,7))
fh=[(x,y) for x in (75,175) for y in (-65,65)]
front=cut(front,[cyl(3.3,6,(x,y,98)) for x,y in fh])
add('FrontElectronicsTrayPLA',front,'04_Printed',PLA,'PLA',label='PLA front deck145x170 |battery access notch')
for i,(x,y) in enumerate(fh):
    add('LargeWasher_Front'+str(i),cyl(9,1.6,(x,y,101.4)).cut(cyl(3.3,1.6,(x,y,101.4))),'07_Fasteners',STEEL,'steel')
    screw('FrontDeckBolt_'+str(i),(x,y,103),(0,0,-1),6,10)
    slotnut('FrontDeck_'+str(i),(x,y,95),(0,0,1))

# A visible reference volume makes the low-CG intention reviewable; NOT a product.
battery=add('BatteryReservedSpace',box(-90,-40,35,120,80,65),'05_Reference',(.86,.55,.12),'reference',label='BATTERY SPACE ONLY |120x80x65|0.75kg budget',note='Unselected pack and connector space. Exclude from hardware count/cost;0.75kg is an estimate for CG sensitivity, not a product specification.')
if App.GuiUp: battery.ViewObject.Transparency=65

for name in ('BatteryCradlePLA','ElectronicsTrayPLA','FrontElectronicsTrayPLA'):
    s=doc.getObject(name).Shape.copy();b=s.optimalBoundingBox(False,False)
    s.translate(V(-(b.XMin+b.XMax)/2,-(b.YMin+b.YMax)/2,-b.ZMin))
    MeshPart.meshFromShape(Shape=s,LinearDeflection=.1,AngularDeflection=.15,Relative=False).write(str(HERE/(name+'.stl')))
doc.recompute()
assert all(o.Shape.isValid() and not o.Shape.isNull() for o in objects)
doc.addObject('App::DocumentObjectGroup','00_ReadMe').Label='A4 / M0601C_111 / CNC quote candidate / tire axial stack provisional'
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE/(NAME+'.FCStd')))
exported=[o for o in objects if o.MaterialBasis!='reference']
Part.export(exported,str(HERE/(NAME+'.step')))
p=HERE/(NAME+'.step');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print(json.dumps({'document':NAME,'physical_objects':len(exported),'reference_objects':1}))

"""A3: DDSM115 integrated wheels, two stock-angle mounts and keyed steel retainers.
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
NAME = 'AMR01_DDSM115_A3'
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = 'AMR-01 A3 | DDSM115 | compact wheel modules'
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
    return s if side=='L' else s.mirror(V(0,0,0),V(0,1,0))


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

# DDSM115 nominal model, with a keyed load support and two bolted stock angles.
# Coordinates and naming distinguish the fixed boss from the rotating body.
X, Z = CFG['geometry']['drive_axle_x_mm'], CFG['geometry']['wheel_axis_z_mm']

def boss_profile(y,length,clearance=0):
    s=hole_y(X,y,Z,9.5+clearance,length)
    # Three flats have an8 mm perpendicular distance from the axis.
    for a in (30,150,270):
        cutter=box(X+8+clearance,y-1,Z-30,30,length+2,60)
        cutter.rotate(V(X,0,Z),V(0,1,0),-a)
        s=s.cut(cutter)
    return s.removeSplitter()

for side in ('L','R'):
    group='02_Drive_'+side
    # Upper angle sits directly against the inner side of the outer3030 rail.
    upper=box(50,80,69,80,40,5).fuse(box(50,115,69,80,5,30))
    upper=upper.fuse(box(50,110,74,80,5,5).cut(hole_x(50,110,79,5,80)))
    joint_holes=[(x,y) for x in (70,110) for y in (95,105)]
    upper=cut(upper,[hole_y(x,114,84,3.3,7) for x in (60,120)]+
              [cyl(2.25,7,(x,y,68)) for x,y in joint_holes])
    side_add('UpperMountAngle',upper,side,group,BLUE,label='40x30x5 angle L80 |3030 inner side face|no spacer')
    for x in (60,120):
        screw('UpperFrameBolt_'+str(x),(x,115,84),(0,1,0),6,12,side)
        slotnut('UpperMount_'+str(x),(x,124,84),(0,1,0),side)
    # From50x50x5 stock, cut the vertical leg to40; no custom bending needed.
    lower=box(60,88,64,60,50,5).fuse(box(60,133,29,60,5,40))
    lower=lower.fuse(box(60,128,59,60,5,5).cut(hole_x(60,128,59,5,60)))
    motor_holes=[(X+7.6*math.cos(math.radians(a)),Z+7.6*math.sin(math.radians(a))) for a in (90,210,330)]
    cable=hole_y(X,132,Z,5,7).fuse(box(X-3.5,132,28,7,7,Z-28))
    lower=cut(lower,[cable]+[hole_y(x,132,z,1.4,7) for x,z in motor_holes]+
              [hole_y(x,132,44,2.25,7) for x in (70,110)]+
              [cyl(2.25,7,(x,y,63)) for x,y in joint_holes])
    # Remove only the inside fillet behind the upper motor screw head; wall remains5 mm.
    lower=lower.cut(hole_y(X,127,Z+7.6,2.6,6)).removeSplitter()
    side_add('LowerMountAngle',lower,side,group,BLUE,label='50x40x5 angle L60 |slotted cable entry|DDSM face138')
    for x,y in joint_holes:
        washer=cyl(4.5,.8,(x,y,74)).cut(cyl(2.25,.8,(x,y,74)))
        side_add('Washer_AngleJoint'+str(x)+str(y),washer,side,'07_Fasteners',STEEL,'steel')
        screw('AngleJoint_'+str(x)+str(y),(x,y,74.8),(0,0,-1),4,16,side,nut=True,nut_stack=10.8)
    # Steel keyed plate supports the fixed boss; it never touches the rotating case.
    key=box(60,138,32,60,5,33).cut(boss_profile(137,7,.05))
    key=cut(key,[hole_y(x,137,44,2.25,7) for x in (70,110)])
    side_add('KeyedSteelSupport',key,side,group,STEEL,'steel',label='SS400 t5 keyed plate |nominal0.05 radial/flat clearance',
             note='Supports the fixed three-flat boss. Precise fit and received-part tolerances need checking; nominal clearance is not a guaranteed fit.')
    for x in (70,110):
        washer=hole_y(x,143,44,4.5,.8).cut(hole_y(x,143,44,2.25,.8))
        side_add('Washer_Key'+str(x),washer,side,'07_Fasteners',STEEL,'steel')
        screw('KeyPlateBolt_'+str(x),(x,143.8,44),(0,-1,0),4,16,side,nut=True,nut_stack=10.8)
    for i,(x,z) in enumerate(motor_holes):
        screw('DDSMFaceBolt_'+str(i),(x,133,z),(0,1,0),2.5,10,side)
    source=CFG['drive']['source']
    boss=boss_profile(138,15)
    boss=cut(boss,[hole_y(X,137,Z,5.8,15),box(X-3.25,137,Z-10,6.5,9,10)]+
             [hole_y(x,137,z,1.3,7) for x,z in motor_holes])
    side_add('DDSMFixedBoss',boss,side,group,STEEL,'purchased',source=source,
             note='Nominal fixed-boss envelope:19 dia,three flats8 from axis,central11.6 cable opening and lower relief. Internal motor components omitted.')
    rotor=hole_y(X,153,Z,34.25,43)
    rotor=cut(rotor,[hole_y(X+26*math.cos(math.radians(a)),191,Z+26*math.sin(math.radians(a)),2,6) for a in range(0,360,30)])
    side_add('DDSMRotatingBody',rotor,side,group,AL,'purchased',source=source,
             label='DDSM115 motor/encoder/driver | simplified rotating envelope')
    tire=hole_y(X,153,Z,50.35,43).cut(hole_y(X,153,Z,34.25,43))
    groove=hole_y(X,173.9,Z,50.5,1.2).cut(hole_y(X,173.9,Z,49.65,1.2))
    tire=tire.cut(groove)
    side_add('Tire',tire,side,group,BLACK,'purchased',source=source,label='DDSM115 tire100.7x43 |manufacturer nominal size')
    cap=hole_y(X,196,Z,18.625,7.5)
    cap=cut(cap,[hole_y(X+10.5*math.cos(math.radians(a)),201,Z+10.5*math.sin(math.radians(a)),2.3,3) for a in (0,120,240)])
    side_add('DDSMFrontCover',cap,side,group,BLACK,'purchased',source=source,label='DDSM115 front cover |total body width50.5')

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
doc.addObject('App::DocumentObjectGroup','00_ReadMe').Label='A3 / DDSM115 / keyed metal mounts / battery is reference only'
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE/(NAME+'.FCStd')))
exported=[o for o in objects if o.MaterialBasis!='reference']
Part.export(exported,str(HERE/(NAME+'.step')))
p=HERE/(NAME+'.step');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print(json.dumps({'document':NAME,'physical_objects':len(exported),'reference_objects':1}))

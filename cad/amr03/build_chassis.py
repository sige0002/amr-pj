"""First-design revision A2: inverted bearings, direct plate mounting, lowered battery cradle.
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
NAME = 'AMR01_Revision_A2'
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = 'AMR-01 A2 | no mounting spacers | direct drive'
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

for side in ('L','R'):
    group='02_Drive_'+side
    # Same small plate as A. Its top touches the frame; no posts or pillars.
    plate=box(48,50,65,84,108,4).cut(box(62,49,64,44,29,6))
    frame_holes=[(x,y) for x in (56,124) for y in (65,135)]
    bearing_holes=[(x,y) for x in (69,111) for y in (118,145)]
    motor_foot=[(65,86),(105,86)]
    plate=cut(plate,[cyl(3.3,6,(x,y,64)) for x,y in frame_holes]+[cyl(2.25,6,(x,y,64)) for x,y in bearing_holes+motor_foot])
    plate=cut(plate,[Part.makeCone(4.2,2.25,1.95,V(x,y,69),V(0,0,-1)) for x,y in bearing_holes+motor_foot])
    side_add('BearingPlate',plate,side,group,BLUE,label='A5052 t4 84x108 | direct to frame underside, no spacer')
    for x,y in frame_holes:
        w=cyl(6.5,1.6,(x,y,63.4)).cut(cyl(3.3,1.6,(x,y,63.4)))
        side_add('Washer_Plate'+str(x)+str(y),w,side,'07_Fasteners',STEEL,'steel')
        screw('PlateBolt_'+str(x)+str(y),(x,y,63.4),(0,0,1),6,12,side)
        slotnut('Plate_'+str(x)+str(y),(x,y,73),(0,0,1),side)
    for j,y in enumerate((118,145),1):
        # KP08 foot z60..65, axis z50: upside down from first design.
        s=box(62.5,y-6.5,60,55,13,5).fuse(hole_y(90,y-6.5,50,14,13)).fuse(hole_y(90,y-7.5,50,8,15))
        s=cut(s,[hole_y(90,y-8.5,50,4,17)]+[cyl(2.5,7,(x,y,59)) for x in (69,111)])
        side_add('KP08_'+str(j),s,side,group,STEEL,'purchased',label='KP08 | inverted | axis50, foot65',source='https://www.amazon.co.jp/dp/B0DSKB5QQN')
        for x in (69,111):
            screw('BearingBolt_'+str(j)+str(x),(x,y,69),(0,0,-1),4,16,side,nut=True,nut_stack=9,csk=True)
    # Inverted angle: horizontal leg underneath the support plate.
    mount=box(60,74,25,50,3,40).fuse(box(60,74,62,50,20,3))
    inside_radius=box(60,77,59,50,3,3).cut(hole_x(60,80,59,3,50))
    mount=mount.fuse(inside_radius)
    mx,mz=CFG['geometry']['motor_body_xz_mm']
    mh=[(mx+15.5*math.cos(math.radians(a)),mz+15.5*math.sin(math.radians(a))) for a in (15,135,255)]
    mount=cut(mount,[hole_y(90,73,50,6.3,5)]+[hole_y(x,73,z,1.7,5) for x,z in mh]+[cyl(2.25,5,(x,y,61)) for x,y in motor_foot])
    side_add('MotorAngle',mount,side,group,BLUE,label='40x20x3 angle L50 | inverted | clocked motor',note='Three of six PCD31 holes after45deg clocking; exact supplied motor phase and angle inside radius need checking.')
    for x,y in motor_foot:
        screw('MotorFootBolt_'+str(x),(x,y,69),(0,0,-1),4,12,side,nut=True,nut_stack=7,csk=True)
    for i,(x,z) in enumerate(mh):
        screw('MotorFaceBolt_'+str(i),(x,77,z),(0,-1,0),3,5,side)
    source='https://wiki.dfrobot.com/fit0185/'
    gearbox=cut(hole_y(mx,50,mz,18.5,24),[hole_y(x,71,z,1.5,4) for x,z in mh])
    for name,s,color in [('Gearbox',gearbox,AL),('MotorCan',hole_y(mx,21,mz,16.5,29),STEEL),('Encoder',hole_y(mx,9,mz,16.5,12),BLACK)]:
        side_add(name,s,side,group,color,'purchased',source=source)
    shaft=hole_y(90,80,50,3,15).cut(box(85,79,52.5,10,17,3))
    # Rotate D-flat with the actual motor about its unchanged output axis.
    shaft.rotate(V(90,0,50),V(0,1,0),-45)
    shaft=shaft.fuse(hole_y(90,74,50,6,6))
    side_add('MotorShaft',shaft,side,group,STEEL,'purchased')
    coupling=cut(hole_y(90,84,50,10,25),[hole_y(90,84,50,3,12.5),hole_y(90,96.5,50,4,12.5)])
    side_add('Coupler',coupling,side,group,ORANGE,'purchased',label='6-to-8 jaw coupling | direct drive, no belt')
    side_add('WheelShaft',hole_y(90,97,50,4,100),side,group,STEEL,'steel',label='8x100 stock shaft | first-design geometry retained')
    for j,y in enumerate((129.5,152.5),1):
        side_add('Collar_'+str(j),hole_y(90,y,50,12.5,8).cut(hole_y(90,y,50,4,8)),side,group,STEEL,'steel')
    wy=164.3
    wheel=hole_y(90,wy,50,46,3).fuse(hole_y(90,wy,50,46,25.4).cut(hole_y(90,wy,50,43,25.4)))
    hh=[(90+12*math.cos(math.radians(a)),50+12*math.sin(math.radians(a))) for a in (45,135,225,315)]
    wheel=cut(wheel,[hole_y(90,wy-1,50,4,5)]+[hole_y(x,wy-1,z,1.6,5) for x,z in hh]+[hole_y(90+26*math.cos(math.radians(a)),wy-1,50+26*math.sin(math.radians(a)),4.2,5) for a in range(0,360,60)])
    side_add('WheelMetal',wheel,side,group,AL,'purchased',label='First-design metal wheel100x25.4 | hub holes need machining')
    side_add('Tire',hole_y(90,wy,50,50,25.4).cut(hole_y(90,wy,50,46,25.4)),side,group,BLACK,'purchased')
    hub=hole_y(90,wy+3,50,16,3).fuse(hole_y(90,wy+6,50,8,10))
    hub=cut(hub,[hole_y(90,wy+2,50,4,15)]+[hole_y(x,wy+2,z,1.6,5) for x,z in hh])
    side_add('Hub',hub,side,group,STEEL,'steel')
    for i,(x,z) in enumerate(hh):
        screw('HubBolt_'+str(i),(x,wy,z),(0,1,0),3,10,side,nut=True,nut_stack=6)

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

# A visible reference volume makes the low-CG intention reviewable; NOT a product.
battery=add('BatteryReservedSpace',box(-90,-40,35,120,80,65),'05_Reference',(.86,.55,.12),'reference',label='BATTERY SPACE ONLY |120x80x65|0.75kg budget',note='Unselected pack and connector space. Exclude from hardware count/cost;0.75kg is an estimate for CG sensitivity, not a product specification.')
if App.GuiUp: battery.ViewObject.Transparency=65

for name in ('BatteryCradlePLA','ElectronicsTrayPLA'):
    s=doc.getObject(name).Shape.copy();b=s.optimalBoundingBox(False,False)
    s.translate(V(-(b.XMin+b.XMax)/2,-(b.YMin+b.YMax)/2,-b.ZMin))
    MeshPart.meshFromShape(Shape=s,LinearDeflection=.1,AngularDeflection=.15,Relative=False).write(str(HERE/(name+'.stl')))
doc.recompute()
assert all(o.Shape.isValid() and not o.Shape.isNull() for o in objects)
doc.addObject('App::DocumentObjectGroup','00_ReadMe').Label='A2 / no spacers or belt / battery volume is reference only'
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE/(NAME+'.FCStd')))
exported=[o for o in objects if o.MaterialBasis!='reference']
Part.export(exported,str(HERE/(NAME+'.step')))
p=HERE/(NAME+'.step');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print(json.dumps({'document':NAME,'physical_objects':len(exported),'reference_objects':1}))

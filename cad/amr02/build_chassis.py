"""Second design B: metal wheel fork, straddle bearings, direct-drive motor.
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
NAME = 'AMR01_SecondDesign_B'
if NAME in App.listDocuments():
    App.closeDocument(NAME)
doc = App.newDocument(NAME)
doc.Label = 'AMR-01 B | straddle support | 10 kg base limit'
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


def screw(name,p,d,diameter,length,side=None,nut=False,nut_stack=None):
    p,d=V(*p),V(*d)
    r={2.5:2.25,3:2.75,4:3.5,6:5}[diameter]
    shape=Part.makeCylinder(diameter/2,length,p,d).fuse(Part.makeCylinder(r,diameter,p-d*diameter,d))
    if side:
        shape=side_shape(shape,side)
    bolt=add(name+(side or ''),shape,'07_Fasteners',STEEL,'steel',note='Unthreaded screw envelope; separate nuts/washers counted in fasteners.csv.')
    for field,value in [('NominalDiameter',diameter),('NominalLength',length)]:
        bolt.addProperty('App::PropertyFloat',field,'Hardware');setattr(bolt,field,value)
    bolt.addProperty('App::PropertyString','HardwareSpec','Hardware')
    bolt.HardwareSpec=f'M{diameter:g}x{length:g} socket screw'
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


for i,y in enumerate((-135,-65,65,135),1):
    s=profile(400);s.translate(V(-200,y,90))
    add('Rail400_'+str(i),s,'01_Frame',label='NFSL6-3030-400 | uncut stock',source='https://www.amazon.co.jp/dp/B0DKF2CCW3',note='Illustrative slots. Mass and I use manufacturer data, not solid CAD volume.')
for i,x in enumerate((-215,215),1):
    s=profile(300);s.rotate(V(0,0,0),V(0,0,1),90);s.translate(V(x,-150,90))
    add('Cross300_'+str(i),s,'01_Frame',label='NFSL6-3030-300 | uncut stock',source='https://www.amazon.co.jp/dp/B0DKDZ8G9G')

# HBLFSN6: 30x30 legs, width20, holes at18/15, cast ribs/tabs simplified.
for end in (-1,1):
    for y in (-120,-50,50,120):
        fx,fy=end*200,y; dx,dy=-end,(-1 if y>0 else 1)
        s=box(min(fx,fx+dx*30),min(fy,fy+dy*4),80,30,4,20)
        s=s.fuse(box(min(fx,fx+dx*4),min(fy,fy+dy*30),80,4,30,20))
        for z in (80,97):
            points=[V(fx+dx*4,fy+dy*4,z),V(fx+dx*27,fy+dy*4,z),V(fx+dx*4,fy+dy*27,z)]
            s=s.fuse(Part.Face(Part.makePolygon(points+[points[0]])).extrude(V(0,0,3)))
        s=cut(s,[hole_x(fx-1 if dx>0 else fx-6,fy+dy*18,90,3.15,7),hole_y(fx+dx*15,fy-1 if dy>0 else fy-6,90,3.15,7)])
        tag=('P' if end>0 else 'N')+str(y).replace('-','N')
        add('Bracket_'+tag,s,'01_Frame',label='MISUMI HBLFSN6-SET | series 6',source=CFG['frame_joints']['source'],note='Dimensional simplified casting. Individual purchasing channel and delivered price still unconfirmed.')
        for letter,p,d in [('A',(fx+dx*4,fy+dy*18,90),(-dx,0,0)),('B',(fx+dx*15,fy+dy*4,90),(0,-dy,0))]:
            screw('Joint'+letter+'_'+tag,p,d,6,12)
            slotnut('Joint'+letter+'_'+tag,tuple(V(*p)+V(*d)*8),d)
    for sg in (-1,1):
        pts=[V(end*230,sg*150,105),V(end*170,sg*150,105),V(end*230,sg*90,105)]
        s=Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,3))
        hs=[(end*185,sg*135),(end*215,sg*105)]
        s=cut(s,[cyl(3.3,5,(x,y,104)) for x,y in hs])
        tag=str(end).replace('-','N')+str(sg).replace('-','N')
        add('Gusset_'+tag,s,'01_Frame',BLUE,label='Retained metal corner gusset t3')
        for i,(x,y) in enumerate(hs):
            add('GussetWasher_'+tag+str(i),cyl(6.5,1.6,(x,y,108)).cut(cyl(3.3,1.6,(x,y,108))),'07_Fasteners',STEEL,'steel')
            screw('GussetBolt_'+tag+str(i),(x,y,109.6),(0,0,-1),6,12)
            slotnut('Gusset_'+tag+str(i),(x,y,101),(0,0,1))

for side in ('L','R'):
    group='02_WheelFork_'+side
    # Rectangular plates and short joint angles form a removable box; no long pillars.
    # Top bridge spans BOTH the inner and outer 3030 rail.
    top=box(30,50,105,120,152,4)
    top_holes=[(x,y,3.3) for x in (42,138) for y in (65,135)]
    top_holes += [(x,y,2.25) for x in (47,133) for y in (94,178)]
    top_holes += [(x,162,2.25) for x in (42,138)]
    top=cut(top,[cyl(r,6,(x,y,104)) for x,y,r in top_holes])
    side_add('ForkBridge',top,side,group,BLUE,label='Metal bridge t4 | both rails | removable fork')
    for x in (42,138):
        for y in (65,135):
            screw('BridgeBolt_'+str(x)+'_'+str(y),(x,y,109),(0,0,-1),6,12,side)
            slotnut('Bridge_'+str(x)+'_'+str(y),(x,y,101),(0,0,1),side)
    # Fore/aft webs carry shear. Rail relief gives clearance; no rail drilling/cutting.
    for n,x in enumerate((30,146)):
        s=box(x,50,35,4,148,70)
        s=cut(s,[box(x-1,y,74.8,6,30.4,31) for y in (49.8,119.8)])
        hs=[(y,z) for y in (116,191) for z in (45,95)]+[(94,95),(178,95)]
        s=cut(s,[hole_x(x-1,y,z,2.25,6) for y,z in hs])
        side_add('ForkWeb_'+str(n),s,side,group,BLUE,label='Metal fore/aft web t4 | relieved around uncut rails')
    for which,y,central in [('Inner',105,11.2),('Outer',198,4.5)]:
        s=box(34,y,25,112,4,80)
        cuts=[hole_y(90,y-1,50,central,6)]
        cuts += [slot_y(x,y-1,50,2.25,6) for x in (71.5,108.5)]
        cuts += [hole_y(x,y-1,z,2.25,6) for x in (42,138) for z in (55,85)]
        if which=='Inner':
            cuts += [hole_y(x,y-1,z,2.25,6) for x in (70,110) for z in (38,68)]
        else:
            cuts += [hole_y(90,y-1,z,1.7,6) for z in (32,68)]
        s=cut(s,cuts)
        side_add('Fork'+which+'Wall',s,side,group,BLUE,label='Metal '+which.lower()+' bearing wall t4 | bolted, removable')
    # Corner joints are commercial angle stock with plain clearance holes.
    for ix,(xx,dx) in enumerate(((34,1),(146,-1))):
        for iy,(yy,dy) in enumerate(((105,-1),(109,1),(198,-1))):
            # Legs lie against web and corresponding wall. 15x15x3, length70.
            s=box(xx if dx>0 else xx-3,yy if dy>0 else yy-15,35,3,15,70)
            s=s.fuse(box(xx if dx>0 else xx-15,yy if dy>0 else yy-3,35,15,3,70))
            s=cut(s,[hole_x(xx-4 if dx<0 else xx-1,yy+dy*7,zz,2.25,6) for zz in (45,95)])
            s=cut(s,[hole_y(xx+dx*8,yy-4 if dy<0 else yy-1,zz,2.25,6) for zz in (55,85)])
            # Only outer corner and outboard face of inner wall are needed.
            if iy==0: continue
            if iy==1:
                s=cut(s,[box(25,119.8,74.8,130,32,31)])
            side_add('ForkCorner_'+str(ix)+str(iy),s,side,group,AL,label='15x15x3 angle stock | bolted box corner')
            for zz in (45,95):
                screw('WebJoint_'+str(ix)+str(iy)+str(zz),(xx-4 if dx>0 else xx+4,yy+dy*7,zz),(dx,0,0),4,12,side,nut=True)
            for zz in (55,85):
                screw('WallJoint_'+str(ix)+str(iy)+str(zz),(xx+dx*8,yy-4 if dy>0 else yy+4,zz),(0,dy,0),4,12,side,nut=True)
    # Short upper joining angles in rail-free bays, t3. No threaded plate edges.
    for i,(x,dx) in enumerate(((34,1),(146,-1))):
        for j,(y,width,center) in enumerate(((84,18,94),(171,12,178))):
            s=box(x if dx>0 else x-3,y,85,3,width,20).fuse(box(x if dx>0 else x-20,y,102,20,width,3))
            xx=x+dx*13
            s=cut(s,[cyl(2.25,5,(xx,center,101)),hole_x(x-4 if dx<0 else x-1,center,95,2.25,6)])
            side_add('UpperAngle_'+str(i)+str(j),s,side,group,AL,label='20x20x3 short bridge/web connecting angle')
            screw('TopJoint_'+str(i)+str(j),(xx,center,109),(0,0,-1),4,12,side,nut=True)
            screw('UpperWebJoint_'+str(i)+str(j),(x-4 if dx>0 else x+4,center,95),(dx,0,0),4,12,side,nut=True)
    # Outside face restraint avoids relying on one line of top slot bolts.
    side_angle=box(34,150,75,112,3,30).fuse(box(34,150,102,112,20,3))
    side_angle=cut(side_angle,[box(60,153,101,60,18,5)]+[hole_y(x,149,90,3.3,5) for x in (42,138)]+[cyl(2.25,5,(x,162,101)) for x in (42,138)])
    side_add('FrameSideAngle',side_angle,side,group,AL,label='30x20x3 side restraint | second frame mounting face')
    for x in (42,138):
        washer=hole_y(x,153,90,6.5,1.6).cut(hole_y(x,153,90,3.3,1.6))
        side_add('SideFrameWasher_'+str(x),washer,side,'07_Fasteners',STEEL,'steel')
        screw('SideFrameBolt_'+str(x),(x,154.6,90),(0,-1,0),6,12,side)
        slotnut('SideFrame_'+str(x),(x,146,90),(0,1,0),side)
        screw('SideTie_'+str(x),(x,162,109),(0,0,-1),4,12,side,nut=True)
    # KFL08 nominal flanges; actual vendor geometry/radial rating is a hold point.
    for tag,face,direction in [('Inner',109,1),('Outer',198,-1)]:
        y0=face if direction>0 else face-4
        flange=box(66,y0,44,48,4,12).fuse(hole_y(90,y0,50,13.5,4))
        body=hole_y(90,face if direction>0 else face-12,50,11.5,12)
        bs=flange.fuse(body)
        bs=cut(bs,[hole_y(90,face-13,50,4,27)]+[hole_y(x,face-13,50,2.5,27) for x in (72,108)])
        side_add('KFL08_'+tag,bs,side,'03_Drive_'+side,STEEL,'purchased',label='KFL08 8mm | nominal 48x27x12 | pitch36',source=CFG['bearing']['reference_source'])
        for x in (72,108):
            p=(x,105 if direction>0 else 202,50)
            screw('BearingBolt_'+tag+str(x),p,(0,direction,0),4,16,side,nut=True,nut_stack=8)
    # Motor saddle: front/rear cheeks and floor; assembled/bent metal, same unit as bearings.
    # U cross-section: 3 mm sheet, inner bend R3 / outer R6, floor z27..30.
    def yz(y,z): return V(65,y,z)
    q=math.sqrt(2)
    saddle_edges=[Part.makeLine(yz(74,75),yz(77,75)),Part.makeLine(yz(77,75),yz(77,33)),
        Part.Arc(yz(77,33),yz(80-3/q,33-3/q),yz(80,30)).toShape(),Part.makeLine(yz(80,30),yz(99,30)),
        Part.Arc(yz(99,30),yz(99+3/q,33-3/q),yz(102,33)).toShape(),Part.makeLine(yz(102,33),yz(102,75)),
        Part.makeLine(yz(102,75),yz(105,75)),Part.makeLine(yz(105,75),yz(105,33)),
        Part.Arc(yz(105,33),yz(99+6/q,33-6/q),yz(99,27)).toShape(),Part.makeLine(yz(99,27),yz(80,27)),
        Part.Arc(yz(80,27),yz(80-6/q,33-6/q),yz(74,33)).toShape(),Part.makeLine(yz(74,33),yz(74,75))]
    saddle=Part.Face(Part.Wire(saddle_edges)).extrude(V(50,0,0))
    face_holes=[(83+15.5*math.cos(math.radians(a)),50+15.5*math.sin(math.radians(a))) for a in (60,180,300)]
    saddle=cut(saddle,[hole_y(90,73,50,6.2,5),hole_y(90,101,50,11.2,5)]+[hole_y(x,101,50,3.75,5) for x in (72,108)]+[hole_y(x,73,z,1.7,5) for x,z in face_holes]+[hole_y(x,101,z,2.25,5) for x in (70,110) for z in (38,68)])
    side_add('MotorSaddle',saddle,side,group,BLUE,label='Metal U saddle t3 / inner R3 | fixed to bearing wall',note='Bend geometry included. Material temper, springback, flat length/K factor, forming tools and tolerance must be agreed with fabricator before manufacture.')
    for x in (70,110):
        for z in (38,68):
            screw('MotorSaddleBolt_'+str(x)+str(z),(x,102,z),(0,1,0),4,12,side,nut=True)
    for i,(x,z) in enumerate(face_holes):
        screw('MotorFaceBolt_'+str(i),(x,77,z),(0,-1,0),3,5,side)
    source='https://wiki.dfrobot.com/fit0185/'
    gearbox=cut(cyl(18.5,24,(83,50,50),(0,1,0)),[hole_y(x,71,z,1.5,4) for x,z in face_holes])
    for name,s,col in [('Gearbox',gearbox,AL),('MotorCan',cyl(16.5,29,(83,21,50),(0,1,0)),STEEL),('Encoder',cyl(16.5,12,(83,9,50),(0,1,0)),BLACK)]:
        side_add(name,s,side,'03_Drive_'+side,col,'purchased',source=source)
    ms=cyl(3,15,(90,80,50),(0,1,0)).cut(box(85,79,52.5,10,17,3)).fuse(cyl(6,6,(90,74,50),(0,1,0)))
    side_add('MotorShaft',ms,side,'03_Drive_'+side,STEEL,'purchased')
    cs=cyl(10,25,(90,83,50),(0,1,0))
    cs=cut(cs,[hole_y(90,82,50,3,13.5),hole_y(90,95.5,50,4,13.5)])
    side_add('Coupler',cs,side,'03_Drive_'+side,ORANGE,'purchased',label='6-to-8 coupling | gap to bearing flange1mm')
    side_add('WheelShaft',hole_y(90,98,50,4,100),side,'03_Drive_'+side,STEEL,'steel',label='8x100 stock shaft | supported around wheel')
    for i,y in enumerate((121.5,177.5)):
        s=hole_y(90,y,50,12.5,8).cut(hole_y(90,y,50,4,8))
        side_add('Collar_'+str(i),s,side,'03_Drive_'+side,STEEL,'steel',note='Backup axial stops with nominal0.5mm gap; do not preload housing. Lock screws not represented.')
    wy=157.3
    web=hole_y(90,wy,50,46,3).cut(hole_y(90,wy,50,4,3))
    rim=hole_y(90,wy,50,46,25.4).cut(hole_y(90,wy,50,43,25.4))
    wheel=web.fuse(rim)
    hh=[(90+12*math.cos(math.radians(a)),50+12*math.sin(math.radians(a))) for a in (45,135,225,315)]
    wheel=cut(wheel,[hole_y(x,wy-1,z,1.6,5) for x,z in hh]+[hole_y(90+26*math.cos(math.radians(a)),wy-1,50+26*math.sin(math.radians(a)),4.2,5) for a in range(0,360,60)])
    side_add('WheelMetal',wheel,side,'03_Drive_'+side,AL,'purchased',label='100x25.4 metal wheel | web/hub interfaces provisional')
    side_add('Tire',hole_y(90,wy,50,50,25.4).cut(hole_y(90,wy,50,46,25.4)),side,'03_Drive_'+side,BLACK,'purchased')
    hub=hole_y(90,wy+3,50,16,3).fuse(hole_y(90,wy+6,50,8,10))
    hub=cut(hub,[hole_y(90,wy+2,50,4,15)]+[hole_y(x,wy+2,z,1.6,5) for x,z in hh])
    side_add('Hub',hub,side,'03_Drive_'+side,STEEL,'steel')
    for i,(x,z) in enumerate(hh):
        screw('HubBolt_'+str(i),(x,wy,z),(0,1,0),3,10,side,nut=True)
    # Two screws retain the printed guard; no reliance on an unverified friction fit.
    cap=hole_y(90,202,50,10,2).fuse(box(84,202,32,12,2,36))
    for z in (32,68): cap=cap.fuse(hole_y(90,202,z,6,2))
    cap=cut(cap,[hole_y(90,201,z,1.7,4) for z in (32,68)])
    side_add('ShaftEndCap',cap,side,'06_Printed',PLA,'PLA',label='PLA shaft-end cover | two M3 screws | not structural')
    for z in (32,68):
        screw('CapBolt_'+str(z),(90,204,z),(0,-1,0),3,10,side,nut=True,nut_stack=6)

# Rear caster unchanged: use same geometry to isolate drive-support comparison.
ch=[(x,y) for x in (-173,-127) for y in (-17.5,17.5)]
mh=[(x,y) for x in (-180,-120) for y in (-65,65)]
p=cut(box(-190,-85,65,80,170,4),[cyl(3.3,6,(x,y,64)) for x,y in ch+mh])
add('CasterAdapter',p,'04_Caster',BLUE,label='Retained metal caster adapter 80x170x4')
for i,(x,y) in enumerate(mh):
    add('CasterSpacer_'+str(i),cyl(6,6,(x,y,69)).cut(cyl(3.5,6,(x,y,69))),'04_Caster')
    screw('CasterFrameBolt_'+str(i),(x,y,65),(0,0,1),6,16)
    slotnut('Caster_'+str(i),(x,y,79),(0,0,1))
ct=cut(box(-179.5,-23.5,62.5,59,47,2.5),[cyl(3.25,5,(x,y,61.5)) for x,y in ch])
add('CasterTop',ct,'04_Caster',STEEL,'purchased',label='Hammer420G-R50 | unchanged 50mm caster')
for i,(x,y) in enumerate(ch):
    screw('CasterBolt_'+str(i),(x,y,69),(0,0,-1),6,16,nut=True)
add('SwivelRace',cyl(19,9,(-150,0,53.5)),'04_Caster',STEEL,'purchased')
forks=[]
for y in (-14,11):
    pts=[V(-171,y,25),V(-157,y,25),V(-135,y,53.5),V(-159,y,53.5)]
    forks.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,3,0)))
add('CasterFork',Part.makeCompound(forks+[cyl(3,32,(-166,-16,25),(0,1,0))]),'04_Caster',STEEL,'purchased')
add('CasterTire',cyl(25,20,(-166,-10,25),(0,1,0)).cut(cyl(12,20,(-166,-10,25),(0,1,0))),'04_Caster',BLACK,'purchased')
add('CasterCore',cyl(12,20,(-166,-10,25),(0,1,0)).cut(cyl(3,20,(-166,-10,25),(0,1,0))),'04_Caster',AL,'purchased')

# 200x180 PLA tray, ribs face up: flat on build plate, no support beneath ribs.
tray=box(-190,-90,105,200,180,2.4)
for x in (-190,7): tray=tray.fuse(box(x,-90,107.4,3,180,8))
for y in (-90,87): tray=tray.fuse(box(-190,y,107.4,200,3,8))
for y in (-35,32): tray=tray.fuse(box(-187,y,107.4,194,3,8))
tray_holes=[(x,y) for x in (-170,-10) for y in (-65,65)]
tray=cut(tray,[cyl(6.2,5,(x,y,104)) for x,y in tray_holes])
add('EquipmentTrayPLA',tray,'06_Printed',PLA,'PLA',label='PLA equipment tray 200x180 | ribs up | P1S fits',note='Light electronics only. Battery restraint goes to metal frame; not a cargo deck or arm base. Use metal compression sleeves and large washers.')
for i,(x,y) in enumerate(tray_holes):
    add('TraySleeve_'+str(i),cyl(6,2.6,(x,y,105)).cut(cyl(3.5,2.6,(x,y,105))),'05_Mounting')
    washer=cyl(9,1.6,(x,y,107.6)).cut(cyl(3.3,1.6,(x,y,107.6)))
    add('TrayWasher_'+str(i),washer,'07_Fasteners',STEEL,'steel')
    screw('TrayBolt_'+str(i),(x,y,109.2),(0,0,-1),6,12)
    slotnut('Tray_'+str(i),(x,y,101),(0,0,1))

# Printing exports are placed flat at z=0 and centered, in millimeters.
for name in ('EquipmentTrayPLA','ShaftEndCapL'):
    s=doc.getObject(name).Shape.copy()
    if name.startswith('ShaftEnd'):
        s.rotate(V(0,0,0),V(1,0,0),90)
    bb=s.optimalBoundingBox(False,False)
    s.translate(V(-(bb.XMin+bb.XMax)/2,-(bb.YMin+bb.YMax)/2,-bb.ZMin))
    mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.1,AngularDeflection=.15,Relative=False)
    mesh.write(str(HERE/(name+'.stl')))

doc.recompute()
assert all(not o.Shape.isNull() and o.Shape.isValid() for o in objects)
readme=doc.addObject('App::DocumentObjectGroup','00_ReadMe')
readme.Label='B / nominal prototype / compare DESIGN_REVIEW / no production approval'
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE/(NAME+'.FCStd')))
Part.export(objects,str(HERE/(NAME+'.step')))
p=HERE/(NAME+'.step');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
print(json.dumps({'name':NAME,'part_objects':len(objects),'FCStd':str(HERE/(NAME+'.FCStd'))}))

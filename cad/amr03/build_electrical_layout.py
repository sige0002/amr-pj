"""FreeCAD packaging study over the validated A2 chassis; all additions are references.
Routes are geometric reservations with rounded bends, not an electrical harness release.
"""
from pathlib import Path
from itertools import combinations
import json
import math
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'electrical_layout_parameters.json').read_text())
V=App.Vector
base_name=cfg['base_document']
if base_name not in App.listDocuments(): App.openDocument(str(HERE/(base_name+'.FCStd')))
base=App.getDocument(base_name)
name='AMR01_ElectricalLayout_A2'
if name in App.listDocuments(): App.closeDocument(name)
doc=App.newDocument(name)
doc.Label='A2 electrical packaging STUDY | reference zones and routes'
groups={}

def add(name,shape,group,color,transparency=0,note=''):
    if group not in groups:
        groups[group]=doc.addObject('App::DocumentObjectGroup',group)
    o=doc.addObject('PartDesign::Feature',name)
    o.Shape=shape
    o.addProperty('App::PropertyString','DesignRole');o.DesignRole='reference_only' if group!='Chassis' else 'copied_validated_geometry'
    o.addProperty('App::PropertyString','DesignNote');o.DesignNote=note
    groups[group].addObject(o)
    if App.GuiUp:
        o.ViewObject.ShapeColor=color;o.ViewObject.LineColor=(.15,.18,.20)
        o.ViewObject.DisplayMode='Flat Lines';o.ViewObject.Transparency=transparency
    return o

parts=[]
for o in base.Objects:
    if o.TypeId!='PartDesign::Feature' or o.MaterialBasis=='reference': continue
    c=add(o.Name,o.Shape.copy(),'Chassis',o.ViewObject.ShapeColor if App.GuiUp else (.7,.7,.7),0)
    parts.append(c)

def box(values):
    x,y,z,l,w,h=values
    return Part.makeBox(l,w,h,V(x,y,z))

battery=add('BatteryBody_ONLY',box(cfg['battery_body_xyz_LWH_mm']),'Reservations',(.88,.58,.16),55,'Unselected battery BODY only. Connector clearance is separate. No battery mass/capacity certification.')
zones=[]
for n,dim in cfg['zones_xyz_LWH_mm'].items():
    col=(.35,.45,.75) if n=='ComputerAndControl' else ((.8,.14,.16) if n=='EmergencyStopAccess' else (.72,.47,.23))
    o=add(n+'_RESERVED',box(dim),'Reservations',col,65,'Packaging allowance only; actual selected part, connectors, cooling and mounting must fit. Not in mechanical BOM.')
    zones.append(o)
# Proposed support surface makes the unsupported front zones explicit. No bolts/material selection implied.
front=Part.makeBox(148,180,2.4,V(42,-90,99))
front=front.cut(Part.makeBox(25,90,5,V(41,-45,98)))
board=add('FrontDeck_PROPOSAL_ONLY',front,'Reservations',(.55,.6,.65),70,'Additional support required; provisional notched outline. No attachment/structural validation or cost included.')
services={n:add(n,box(dim),'ServiceClearances',(.30,.75,.95),85,'Temporary service envelope, keep permanent equipment and harnesses clear.') for n,dim in cfg['service_xyz_LWH_mm'].items()}
services['BatteryUpperRemoval'].ViewObject.Visibility=False

# Circular fillets on a 3D polyline, with a stated planning radius at each bend.
def route_shape(points,radius,bend):
    pts=[V(*p) for p in points]
    corners=[]
    for i in range(1,len(pts)-1):
        incoming=pts[i]-pts[i-1];incoming.normalize()
        outgoing=pts[i+1]-pts[i];outgoing.normalize()
        dot=max(-1.,min(1.,incoming.dot(outgoing)))
        angle=math.acos(dot)
        if angle<1e-7:
            corners.append(None);continue
        tangent=bend*math.tan(angle/2)
        if tangent>.49*min((pts[i]-pts[i-1]).Length,(pts[i+1]-pts[i]).Length):
            raise ValueError('Insufficient straight length for planning bend: '+str(points[i]))
        a=pts[i]-incoming*tangent;b=pts[i]+outgoing*tangent
        normal=outgoing-incoming*dot;normal.normalize()
        centre=a+normal*bend
        mid=(a-centre)+(b-centre);mid.normalize();mid=centre+mid*bend
        corners.append((a,mid,b))
    edges=[];current=pts[0]
    for i,corner in enumerate(corners,1):
        if corner is None: continue
        a,mid,b=corner
        if (a-current).Length>1e-8:edges.append(Part.makeLine(current,a))
        edges.append(Part.Arc(a,mid,b).toShape());current=b
    edges.append(Part.makeLine(current,pts[-1]))
    path=Part.Wire(edges)
    direction=pts[1]-pts[0];direction.normalize()
    profile=Part.Wire([Part.makeCircle(radius,pts[0],direction)])
    return path.makePipeShell([profile],True,False)

routes=[]
for entry in cfg['cable_routes']:
    shape=route_shape(entry['points_mm'],entry['radius_mm'],entry['bend_radius_mm'])
    color=(.88,.20,.07) if entry['kind']=='power' else (.1,.45,.88)
    o=add('Route_'+entry['name'],shape,'CableRouteReservations',color,0,
          'Reference bundle envelope; planned bend radius only. Wire gauge, connector, clamps, bend minimum and electrical topology not finalized.')
    o.addProperty('App::PropertyString','CableKind');o.CableKind=entry['kind']
    routes.append((o,entry))

bounds={o.Name:o.Shape.optimalBoundingBox(False,False) for o in doc.Objects if o.TypeId=='PartDesign::Feature'}

def overlaps(a,b):
    if not bounds[a.Name].intersect(bounds[b.Name]):return 0
    return a.Shape.common(b.Shape).Volume

base_hits=[]
for ref in [battery,*zones,board,*services.values()]+[o for o,_ in routes]:
    for p in parts:
        vol=overlaps(ref,p)
        if vol>.001:base_hits.append({'reference':ref.Name,'chassis':p.Name,'mm3':vol})
service_hits=[]
for n,service in services.items():
    for ref in [*zones,board]+[o for o,e in routes if n not in e['allowed_service']]:
        vol=overlaps(service,ref)
        if vol>.001:service_hits.append({'service':n,'reference':ref.Name,'mm3':vol})
zone_hits=[]
for a,b in combinations(zones+[battery],2):
    vol=overlaps(a,b)
    if vol>.001:zone_hits.append({'a':a.Name,'b':b.Name,'mm3':vol})
route_equipment_hits=[]
for route,entry in routes:
    for equipment in zones+[board,battery]:
        if equipment.Name in entry['allowed_equipment_connections']:continue
        vol=overlaps(route,equipment)
        if vol>.001:route_equipment_hits.append({'route':route.Name,'unrelated_equipment':equipment.Name,'mm3':vol})
route_crossings=[]
for (a,ea),(b,eb) in combinations(routes,2):
    vol=overlaps(a,b)
    if vol>.001:route_crossings.append({'a':a.Name,'b':b.Name,'kind_a':ea['kind'],'kind_b':eb['kind'],'mm3':vol})
results={
 'status':'reference_packaging_only_not_electrical_or_assembly_release',
 'base_physical_objects':len(parts),'reference_routes':len(routes),
 'reference_vs_chassis_collisions':base_hits,'permanent_reservation_vs_service_collisions':service_hits,
 'equipment_zone_collisions':zone_hits,'route_envelope_intersections':route_crossings,
 'routes_vs_unrelated_equipment_or_proposed_deck':route_equipment_hits,
 'invalid_shapes':[o.Name for o in doc.Objects if o.TypeId=='PartDesign::Feature' and not o.Shape.isValid()],
 'battery_connector_route_must_disconnect_for_service':True,
 'upper_service_height_mm':190,'motor_harness_endpoints_not_connected_to_verified_terminals':True,
 'minimum_terminal_side_slack_current_pack_mm':2,
 'not_checked':['Selected pack/adapter geometry and removal mechanism','Real motor connector exit in18mm encoder gap','Clamp attachment and proposed front-deck fasteners','Cable ratings, EMI, actual bend minimum, wiring lengths and electric protection','Battery capacity/runtime, power conversion/regeneration and heat'],
}
(HERE/'electrical_layout_validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
assert not base_hits and not service_hits and not zone_hits and not route_crossings and not route_equipment_hits and not results['invalid_shapes']
doc.recompute()
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll()
doc.saveAs(str(HERE/(name+'.FCStd')))

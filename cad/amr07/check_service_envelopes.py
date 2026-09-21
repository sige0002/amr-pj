"""Continuous conservative service envelopes and D2 part identity, headless."""
from pathlib import Path
import json,hashlib,math
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
V=App.Vector
doc=App.openDocument(str(HERE/'AMR01_M0601C_A6.FCStd'))
parts=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature' and o.MaterialBasis!='reference']
boxes={o.Name:o.Shape.BoundBox for o in parts}
def check(shape,exclude):
    hits=[]
    for o in parts:
        if o.Name in exclude or not shape.BoundBox.intersect(boxes[o.Name]):continue
        vol=shape.common(o.Shape).Volume
        if vol>.001:hits.append({'part':o.Name,'overlap_mm3':vol})
    return hits
deck=[o.Name for o in parts if o.Name.startswith(('CargoDeck','CargoStop','SlotNut_CargoDeck','Printed','Fixture'))]
b=doc.getObject('BatteryReservedSpace').Shape.BoundBox
battery=Part.makeBox(b.XLength,b.YLength,b.ZLength+160,V(b.XMin,b.YMin,b.ZMin))
# D50/trail16/W20 gives sqrt(41^2+10^2)=42.202mm for the
# square tire-side corner; R41 alone is only the side-view reach.
turn_radius=43
caster=Part.makeCylinder(turn_radius,65,V(-150,0,0))
caster_parts=['CasterTop','SwivelRace','CasterFork','CasterTire','CasterCore']
caster_fixings=[o.Name for o in parts if o.Name.startswith(('CasterBolt_','Nut_CasterBolt_'))]
tests={'battery_upward_swept_box_0_to160_mm':check(battery,deck),
       'caster_full360_R43_H65_cylinder_vs_chassis':check(caster,caster_parts+caster_fixings)}
# The cylinder deliberately contains its own stationary mounting hardware.
# Check the rotating fork/wheel against those fixings separately, and bound
# the distance moved between samples to cover the unsampled angular interval.
min_gap=1e9;rotating_hits=[]
for name in ('CasterFork','CasterTire','CasterCore'):
    b=boxes[name]
    assert max(math.hypot(x+150,y) for x in (b.XMin,b.XMax) for y in (b.YMin,b.YMax))<turn_radius
for deg in range(0,360,2):
    for name in ('CasterFork','CasterTire','CasterCore'):
        shape=doc.getObject(name).Shape.copy();shape.rotate(V(-150,0,0),V(0,0,1),deg)
        for fixed in caster_fixings:
            gap=shape.distToShape(doc.getObject(fixed).Shape)[0];min_gap=min(min_gap,gap)
            if gap<1e-6 and shape.common(doc.getObject(fixed).Shape).Volume>.001:
                rotating_hits.append({'angle_deg':deg,'moving':name,'fixed':fixed})
tests['caster_rotating_proxy_vs_mounting_bolts']=rotating_hits
max_unsampled_motion=2*turn_radius*math.sin(math.radians(1)/2)
# Plate and attached small fixtures lift as one group after all six M6 bolts
# are withdrawn; use swept AABBs, which overestimate the actual occupied space.
deck_lift=[]
for name in deck:
    if name.startswith(('SlotNut_CargoDeck','CargoDeckBolt','CargoDeckSupport')):continue
    b=boxes[name]
    env=Part.makeBox(b.XLength,b.YLength,b.ZLength+160,V(b.XMin,b.YMin,b.ZMin))
    hits=check(env,deck)
    if hits:deck_lift.append({'moving':name,'hits':hits})
tests['deck_and_fixtures_upward_swept_boxes_0_to160_mm']=deck_lift
source=HERE/'aluminum-grid-deck/AMR_GridDeck_C45_D2.step'
q=Part.read(str(source));q.translate(V(0,0,114));plate=doc.getObject('CargoDeckPlate').Shape
diff=plate.cut(q).Volume+q.cut(plate).Volume
assert diff<.001
guide_clearance={}
for side in ('L','R'):
    b=doc.getObject('FixtureCableEnvelope'+side).Shape.BoundBox
    guide_clearance[side]={'bundle_floor_z_mm':b.ZMin,'frame_top_z_mm':99,'vertical_nominal_gap_mm':b.ZMin-99}
result={'status':'passed' if all(not v for v in tests.values()) and min_gap>max_unsampled_motion else 'failed','tests':tests,
        'caster_fixing_clearance':{'minimum_sampled_mm':min_gap,'angular_step_deg':2,
            'maximum_motion_to_nearest_sample_mm':max_unsampled_motion,'continuous_gap_lower_bound_mm':min_gap-max_unsampled_motion},
        'quoted_plate_symmetric_difference_mm3':diff,'quoted_STEP_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'local_D6_bundle_to_frame_vertical_clearance':guide_clearance,
        'conditions':['Power off; cargo/straps removed and deck cable unplugged before deck removal. Six M6 bolts withdrawn; retain six loose support blocks.',
        'Caster nominal envelopeR43/H65 includes side-view reach41 plus half wheel width10. Proxy rotating boxes fit insideR43. Exact supplier fork and received tolerances/deflection remain unverified.',
        'Tire service remains the separately recorded axial samples; actual tire deformation/fastener details need received-part fit.',
        'Local cable gauge only; full routing, connector envelopes and bend radii remain unselected.']}
(HERE/'service_envelope_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
assert all(not v for v in tests.values())
assert min_gap>max_unsampled_motion

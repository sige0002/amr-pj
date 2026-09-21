"""Nominal tool shafts and tire-removal clearance. Run inside FreeCAD.

This checks access volumes, not socket brand/handle fit or tire elasticity.
"""
from pathlib import Path
import json
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
doc=App.getDocument('AMR01_M0601C_A4')
V=App.Vector
parts=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature' and o.MaterialBasis!='reference']
checks=[]


def check(name, shape, exclude=()):
    box=shape.optimalBoundingBox(False,False)
    hits=[]
    for p in parts:
        if p.Name in exclude or not box.intersect(p.Shape.optimalBoundingBox(False,False)):
            continue
        overlap=shape.common(p.Shape).Volume
        if overlap>.001: hits.append({'part':p.Name,'mm3':overlap})
    checks.append({'name':name,'hits':hits,'minimum_z_mm':box.ZMin})


for side,sign in [('L',1),('R',-1)]:
    # Driver reaches the motor fixed-end screws from the inner side.
    for i,(x,z) in enumerate([(90,57.95),(83.41820693,46.55),(96.58179307,46.55)]):
        tool=Part.makeCylinder(2,30,V(x,sign*127.5,z),V(0,-sign,0))
        check('M2p5_inner_tool_'+side+str(i),tool,['MotorFaceBolt_'+str(i)+side])
    for x in (52.5,127.5):
        tool=Part.makeCylinder(4,40,V(x,sign*135,58),V(0,0,-1))
        check('M6_bottom_tool_'+side+str(x),tool)
    # Remove the cap first. The actual tyre fit/elastic deformation is not known.
    for travel in (1,5,10,20,40,80):
        tire=doc.getObject('Tire'+side).Shape.copy();tire.translate(V(0,sign*travel,0))
        check('Tire_outboard_'+side+str(travel),tire,['Tire'+side,'TireCover'+side])

left=doc.getObject('CustomMotorMountL').Shape.copy()
left.rotate(V(90,0,0),V(0,0,1),180)
right=doc.getObject('CustomMotorMountR').Shape
same_part_error=left.cut(right).Volume+right.cut(left).Volume
layout=App.getDocument('AMR01_ElectricalLayout_A4')
wire_min=min(layout.getObject('Route_M0601FixedHarness'+side).Shape.optimalBoundingBox(False,False).ZMin for side in ('L','R'))
result={'status':'nominal_service_volumes_only', 'checks':checks,
        'passed':all(not c['hits'] for c in checks),
        'same_part_left_right_rotation_volume_error_mm3':same_part_error,
        'motor_lead_reservation_minimum_z_mm':wire_min,
        'bracket_minimum_z_mm':35,'fixed_rigid_chassis_minimum_z_mm':32,
        'motor_screw_head_land_to_slot_edge_nominal_mm':6.58179307-2.25-3.5,
        'motor_clearance_hole_to_slot_ligament_nominal_mm':6.58179307-1.4-3.5,
        'scope':'Tool shaft radii2mm (M2.5) /4mm (M6), straight insertion only. Hex sockets/head recesses not modeled. Tire translated at6 discrete positions after cover removal, using assumed bore/axial datum. Chassis must be supported during service. No real tire fit, wrench handle, fatigue, tolerance or assembly-process certification.'}
(HERE/'mount_service_validation.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'] and same_part_error<.001
assert wire_min>=25
print(json.dumps(result))

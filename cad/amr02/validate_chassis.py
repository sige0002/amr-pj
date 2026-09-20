"""Run in FreeCAD after build_chassis.py; nominal checks, not a load rating."""
from pathlib import Path
from itertools import combinations
from collections import defaultdict
import csv
import json
import math
import FreeCAD as App
import Part
import Mesh

HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'design_parameters.json').read_text())
doc=App.getDocument('AMR01_SecondDesign_B')
parts=[o for o in doc.Objects if o.TypeId=='PartDesign::Feature']
fasteners=set(doc.getObject('_07_Fasteners').Group)
primary=[o for o in parts if o not in fasteners]
bounds={o.Name:o.Shape.optimalBoundingBox(False,False) for o in parts}
collisions=[]
boolean_count=0
for a,b in combinations(parts,2):
    if bounds[a.Name].intersect(bounds[b.Name]):
        boolean_count+=1
        overlap=a.Shape.common(b.Shape).Volume
        if overlap>.001:
            collisions.append({'a':a.Name,'b':b.Name,'mm3':overlap})
bb=Part.makeCompound([o.Shape for o in parts]).optimalBoundingBox(False,False)
frames=[o for o in parts if o.Name.startswith(('Rail400_','Cross300_'))]
fb=Part.makeCompound([o.Shape for o in frames]).optimalBoundingBox(False,False)
ground={n:bounds[n].ZMin for n in ('TireL','TireR','CasterTire')}
excluded_ground=('Caster','Swivel','Tire','WheelMetal')
fixed=[o for o in parts if not o.Name.startswith(excluded_ground)]
lowest=min(fixed,key=lambda o:bounds[o.Name].ZMin)
pairs=[('FrameSideAngleL','TireL'),('ForkBridgeL','TireL'),('Rail400_4','TireL'),
       ('CouplerL','KFL08_InnerL'),('EncoderL','EncoderR'),('GearboxL','Rail400_3'),
       ('HubL','Collar_1L'),('Collar_1L','KFL08_OuterL')]
clearances=[{'a':a,'b':b,'mm':doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]} for a,b in pairs]

# Purchased-part mass overrides: nominal solid envelopes are not product weights.
mass=[
 {'part':'NFSL6-3030 2.2 m','kg':1.672,'basis':'manufacturer 0.76 kg/m'},
 {'part':'FIT0185 x2','kg':.410,'basis':'manufacturer 205 g each'},
 {'part':'100mm wheel+tire x2','kg':.600,'basis':'seller reference 300 g each; unmeasured'},
 {'part':'KFL08 x4','kg':.240,'basis':'60 g each reference supplier shipping weight; conservative allowance, vendor unselected'},
 {'part':'HBLFSN6 x8','kg':.120,'basis':'MISUMI official catalog 15 g each; bolts/nuts counted separately'},
 {'part':'420G-R50','kg':.150,'basis':'engineering allowance, not measured'},
 {'part':'couplings x2','kg':.040,'basis':'20 g each allowance'},
 {'part':'unmodeled grub screws, retaining hardware','kg':.030,'basis':'allowance; plain modeled nuts not counted twice'}]
skip_prefix=('Rail400_','Cross300_','Bracket_','Gearbox','MotorCan','Encoder','MotorShaft','KFL08_','Coupler','WheelMetal','Tire')
skip_names={'CasterTop','SwivelRace','CasterFork','CasterTire','CasterCore'}
rho={'aluminum':2.70e-6,'steel':7.85e-6,'PLA':1.24e-6}
for o in parts:
    if o.Name.startswith(skip_prefix) or o.Name in skip_names: continue
    density=rho[o.MaterialBasis]
    mass.append({'part':o.Name,'kg':o.Shape.Volume*density,'basis':'CAD volume x '+o.MaterialBasis+' assumed density; threads omitted'})
mechanical=sum(i['kg'] for i in mass)
electrical=sum(cfg['mass_electrical_budget_kg'].values())

# Purchases must include packs/spares. This CSV is installed modeled hardware only.
inventory=defaultdict(list)
for o in sorted(fasteners,key=lambda o:o.Name):
    if 'HardwareSpec' in o.PropertiesList:
        spec=o.HardwareSpec
    elif o.Name.startswith('TrayWasher_'):
        spec='M6 large washer OD18 ID6.6 t1.6'
    elif 'Washer_' in o.Name:
        spec='M6 washer OD13 ID6.6 t1.6'
    else:
        raise AssertionError('Hardware not counted: '+o.Name)
    inventory[spec].append(o.Name)
with (HERE/'fasteners.csv').open('w',newline='') as f:
    writer=csv.writer(f,lineterminator='\n')
    writer.writerow(['specification','installed_quantity','included_in_HBLFSN6_SET','additional_installed_quantity','model_object_names'])
    for spec,names in sorted(inventory.items()):
        included=16 if spec in ('M6x12 socket screw','HNTT6-6 slot nut') else 0
        writer.writerow([spec,len(names),included,len(names)-included,';'.join(names)])

printed=[]
for name in ('EquipmentTrayPLA','ShaftEndCapL'):
    mesh=Mesh.Mesh(str(HERE/(name+'.stl')))
    box=mesh.BoundBox
    dims=[box.XLength,box.YLength,box.ZLength]
    printed.append({'file':name+'.stl','dimensions_mm':dims,'watertight':mesh.isSolid(),
                    'fits_P1S_256_cube':all(d<=256 for d in dims),'quantity':2 if 'Cap' in name else 1})

# Sample actual caster shape: the full containing cylinder would also contain
# its stationary mounting nuts above the fork, which is not a collision.
rotating_names={'SwivelRace','CasterFork','CasterTire','CasterCore'}
caster_shape=Part.makeCompound([doc.getObject(n).Shape for n in rotating_names])
sweep_targets=[o for o in parts if o.Name not in rotating_names and bounds[o.Name].ZMin<62.5-1e-6 and bounds[o.Name].XMin<-105 and bounds[o.Name].XMax>-195 and bounds[o.Name].YMin<45 and bounds[o.Name].YMax>-45]
sweep_hits=[]
for angle in range(0,360,5):
    rotated=caster_shape.copy();rotated.rotate(App.Vector(-150,0,0),App.Vector(0,0,1),angle)
    rb=rotated.optimalBoundingBox(False,False)
    for o in sweep_targets:
        if rb.intersect(bounds[o.Name]) and rotated.common(o.Shape).Volume>.001:
            sweep_hits.append({'angle_deg':angle,'part':o.Name})

result={
 'status':'nominal_geometry_checks_only_not_manufacturing_release',
 'part_objects':len(parts),'primary_objects':len(primary),
 'invalid_shapes':[o.Name for o in parts if not o.Shape.isValid() or o.Shape.isNull()],
 'all_part_pair_count':len(parts)*(len(parts)-1)//2,
 'bounding_box_candidate_boolean_count':boolean_count,
 'all_part_collisions':collisions,
 'collision_scope':'All modeled parts including screw-to-screw and screw-to-nut pairs; >0.001 mm3 threshold. Nominal geometry; bought-part shape, angular nut orientation, extrusion/angle corner radii, tools, tolerance, deformation, cables and mounting details remain unverified.',
 'frame_LWH_mm':[fb.XLength,fb.YLength,fb.ZLength],
 'assembled_mechanical_LWH_mm':[bb.XLength,bb.YLength,bb.ZLength],
 'body_envelope_target_mm':cfg['requirements']['body_envelope_target_mm'],
 'ground_contacts_z_mm':ground,
 'minimum_fixed_nonwheel_clearance_mm':bounds[lowest.Name].ZMin,'lowest_component':lowest.Name,
 'drive_track_mm':bounds['TireL'].Center.y-bounds['TireR'].Center.y,
 'clearances':clearances,'caster_sweep_fixed_hits':sweep_hits,
 'caster_sweep_scope':'72 nominal orientations at 5 degree spacing against all nearby fixed parts, including stationary caster mounting fasteners; not continuous/tolerance proof.',
 'shaft_interfaces_mm':{'shaft_length':100,'motor_shaft_in_coupler':12,'wheel_shaft_in_coupler':10,
    'shaft_end_gap_in_coupler':3,'coupler_to_inner_bearing':1,'bearing_housing_axial_envelope':12,
    'inner_bearing_whole_housing_on_shaft':True,'outer_bearing_whole_housing_on_shaft':True,
    'note':'Housing axial envelopes only; inner-ring width, set screw positions, bore fit and allowable coupling engagement need supplier/received-part confirmation.'},
 'motor_M3_thread_engagement_mm':2,'motor_M3_max_engagement_mm':3,
 'hardware_installed':{k:len(v) for k,v in sorted(inventory.items())},
 'printed_parts':printed,
 'mass':{'mechanical_estimate_kg':mechanical,'additional_electrical_budget_kg':electrical,
    'estimated_complete_base_kg':mechanical+electrical,'base_upper_budget_kg':10,
    'remaining_budget_kg':10-mechanical-electrical,'within_upper_budget':mechanical+electrical<=10,
    'note':'Estimate, not measured mass. PLA modeled as solid. Equipment/guard budget does not mean these unmodeled items fit the CAD.',
    'breakdown':mass},
 'unverified':cfg['unverified']+['Tool access, nut angular orientation and angle inside radius; no locking/thread friction or bolt preload model',
    'Motor saddle bend flat length, bend radius tolerance and metal grade/temper; no fabrication release',
    'Gearbox holes and extrusion grooves are nominal thread-free envelopes, not supplier CAD']}

assert not result['invalid_shapes'] and not collisions,(result['invalid_shapes'],collisions)
assert all(a<=b+1e-6 for a,b in zip(result['assembled_mechanical_LWH_mm'],cfg['requirements']['body_envelope_target_mm']))
assert all(abs(z)<1e-6 for z in ground.values())
assert bounds[lowest.Name].ZMin>=cfg['requirements']['minimum_ground_clearance_mm']-1e-6
assert not sweep_hits,sweep_hits
assert all(p['watertight'] and p['fits_P1S_256_cube'] for p in printed)
assert len(inventory['HNTT6-6 slot nut'])==44
assert math.isclose(result['drive_track_mm'],cfg['geometry']['drive_track_mm'])
assert math.isclose(bounds['TireL'].Center.y,cfg['geometry']['wheel_center_y_mm'])
assert math.isclose(fb.XLength,460) and math.isclose(fb.YLength,300)
assert math.isclose(bounds['WheelShaftL'].YMin,98) and math.isclose(bounds['WheelShaftL'].YMax,198)
assert all(c['mm']>0 for c in clearances)
assert result['mass']['within_upper_budget']
(HERE/'validation_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('mass','unverified')},ensure_ascii=False))
print(json.dumps({k:v for k,v in result['mass'].items() if k!='breakdown'},ensure_ascii=False))

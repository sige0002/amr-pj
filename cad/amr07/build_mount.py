"""A6 review correction, using the published analytic seat profile.

Run in headless FreeCAD. A4 and A5 quoted files are read-only references.
The nominal motor is seated upward; pocket axis and screw pattern differ
intentionally by 0.17 mm. Manufacturing release still needs lot gauging.
"""
from pathlib import Path
import hashlib
import json
import sys
import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'amr05'))
from reconstruct_motor_seat import source_floor_wire

V = App.Vector
STEM = 'M0601C_mount_A6_R1'


def make_mount():
    flange = Part.makeBox(90,30,5,V(45,120,64))
    web = Part.makeBox(60,17,34,V(60,130,35))
    shape = flange.fuse(web).removeSplitter()
    wire, spec = source_floor_wire()
    expanded = wire.makeOffset2D(.12)
    wire = expanded if expanded.ShapeType == 'Wire' else expanded.Wires[0]
    assert wire.isClosed() and wire.isValid()
    pocket = Part.Face(wire).extrude(V(0,0,9))
    rot = App.Rotation(V(-1,0,0),V(0,0,-1),V(0,-1,0),'ZXY')
    pocket.Placement = App.Placement(V(90,147,50.18),rot)
    cutters = [pocket]
    holes = []
    for x,y in spec['mount_holes_local_xy_mm']:
        # Screw pattern remains at the actual nominal motor axis, not the seat axis.
        xw, zw = 90-x, 50.35-y
        cutters.append(Part.makeCylinder(1.6,19,V(xw,129,zw),V(0,1,0)))
        cutters.append(Part.makeCylinder(3.1,.5,V(xw,130,zw),V(0,1,0)))
        holes.append([xw-45,zw-35])
    cutters += [Part.makeCylinder(3.25,19,V(90,129,50.35),V(0,1,0)),
                Part.makeBox(6.5,19,16.35,V(86.75,129,34)),
                Part.makeCylinder(4.75,10,V(90,138,50.35),V(0,1,0)),
                Part.makeBox(9.5,10,16.35,V(85.25,138,34)),
                Part.makeBox(9.5,19,7,V(85.25,129,34))]
    for x in (52.5,127.5):
        cutters.append(Part.makeCylinder(3.3,7,V(x,135,63)))
        cutters.append(Part.makeCone(3.6,3.3,.3,V(x,135,64)))
    shape = shape.cut(Part.makeCompound(cutters)).removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1
    return shape, holes


def main():
    shape, holes = make_mount()
    local = shape.copy(); local.translate(V(-45,-120,-35))
    step = HERE/(STEM+'.step')
    local.exportStep(str(step))
    step.write_text('\n'.join(line.rstrip() for line in step.read_text().splitlines())+'\n')
    restored = Part.read(str(step))
    difference = restored.cut(local).Volume + local.cut(restored).Volume
    assert restored.isValid() and len(restored.Solids)==1 and difference<.001
    report = {'revision':'A6-R1','status':'quote_and_fit_mock_only_not_released',
        'step_file':step.name,'step_sha256':hashlib.sha256(step.read_bytes()).hexdigest(),
        'date':'2026-09-21','material':'A6061-T6','quantity':2,'same_part_both_sides':True,
        'quote_origin_world_mm':[45,120,35], 'overall_LWH_mm':[90,30,34],
        'flange_thickness_mm':5,'frame_hole_pitch_mm':75,'frame_holes_diameter_mm':6.6,
        'web_width_thickness_mm':[60,17], 'seat_depth_mm':9,'rear_wall_mm':8,
        'source_profile_offset_mm':.12,'seat_small_corner_radius_mm':1.62,
        'seat_large_arc_radius_mm':9.67,'seat_flat_distance_mm':8.22,
        'seat_axis_local_xz_mm':[45,15.18],'motor_axis_local_xz_mm':[45,15.35],
        'motor_holes_local_xz_mm':holes,'motor_holes_diameter_mm':3.2,
        'motor_holes_size_limits_mm':[3.2,3.3],'motor_holes_PCD_mm':15.2,
        'functional_profile_total_zone_mm':.10, 'profile_includes_location':True,
        'hole_position_diametral_zone_mm':.10,
        'rear_wall_size_tolerance_pm_mm':.05,'datum_A_flatness_mm':.05,
        'datum_B_flatness_mm':.05,'datum_B_perpendicularity_to_A_mm':.05,
        'datums':{'A':'frame contact surface local Z34',
                  'B':'motor end seating plane local Y18',
                  'C':'derived median plane of outside X0 and X90 faces'},
        'motor_washer_counterbore_diameter_mm':6.2,'motor_washer_counterbore_depth_mm':.5,
        'motor_washer':'WILCO FW-2505-05EB 2.7x5x0.5, received dimensions and seating must be inspected',
        'frame_head_side_chamfer_mm':.3,
        'cable_through_throat_width_mm':6.5,'cable_front_and_lower_relief_width_mm':9.5,
        'nominal_motor_upward_seating_offset_mm':.17,
        'volume_mm3_each':shape.Volume,'mass_kg_each_estimate':shape.Volume*2.7e-6,
        'roundtrip_symmetric_difference_mm3':difference,
        'scope':'Basic contour dimensions controlled by total profile zone 0.10 to A|B|C; do not add an independent +/-0.05 axis-location error. Actual motor profile/hole-pattern gauges and local strength remain required.'}
    (HERE/(STEM+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()

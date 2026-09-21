"""A4 one-piece CNC mount. New chassis geometry; source-derived motor seat.

Nominal quote model, not a released tolerance/load-qualified part.
Coordinates match the left AMR module; the right uses the same part turned over.
"""
from pathlib import Path
import json
import FreeCAD as App
import Part
from reconstruct_motor_seat import source_floor_wire

V = App.Vector
HERE = Path(__file__).resolve().parent


def make_mount():
    # Flange directly contacts the underside of the existing 3030 rail.
    flange = Part.makeBox(90, 30, 5, V(45, 120, 64))
    web = Part.makeBox(60, 17, 34, V(60, 130, 35))
    part = flange.fuse(web).removeSplitter()
    wire, spec = source_floor_wire()
    # Deliberate fit allowance: original flat 8.10 -> 8.25 mm.
    # Offset is applied to native analytic curves, not a polygon traced from a photo.
    expanded = wire.makeOffset2D(0.15)
    wires = expanded.Wires if expanded.ShapeType != 'Wire' else [expanded]
    assert len(wires) == 1 and wires[0].isClosed()
    assert Part.Face(wires[0]).Area > Part.Face(wire).Area
    pocket = Part.Face(wires[0]).extrude(V(0, 0, 9))
    # source local +Y is toward cable slot; make it downward on the chassis.
    # local (x,y,z) -> (90-x,147-z,50.35-y), a rigid rotation.
    rot = App.Rotation(V(-1, 0, 0), V(0, 0, -1), V(0, -1, 0), 'ZXY')
    pocket.Placement = App.Placement(V(90, 147, 50.35), rot)
    cutters = [pocket]
    for x, y in spec['mount_holes_local_xy_mm']:
        cutters.append(Part.makeCylinder(1.4, 19, V(90-x, 129, 50.35-y), V(0, 1, 0)))
    # A wide open slot lets the complete factory harness enter from below.
    # This is new geometry, wider than the source throat; no cable through a closed hole.
    # Keep the rear screw-head lands:7mm through throat;9.5mm only on the
    # motor side of the seat and below the M2.5 hole group (z<=41).
    cutters += [Part.makeCylinder(3.5, 19, V(90, 129, 50.35), V(0, 1, 0)),
                Part.makeBox(7, 19, 16.35, V(86.5, 129, 34)),
                Part.makeCylinder(4.75, 10, V(90, 138, 50.35), V(0, 1, 0)),
                Part.makeBox(9.5, 10, 16.35, V(85.25, 138, 34)),
                Part.makeBox(9.5, 19, 7, V(85.25, 129, 34))]
    for x in (52.5, 127.5):
        cutters.append(Part.makeCylinder(3.3, 7, V(x, 135, 63)))
    part = part.cut(Part.makeCompound(cutters)).removeSplitter()
    assert part.isValid() and len(part.Solids) == 1
    return part


def report(shape):
    return {'status': 'quotation_model_not_manufacturing_release',
            'material': 'A6061-T6, quotation preference; alloy to be agreed',
            'quantity': 2, 'same_part_both_sides': True,
            'volume_mm3_each': shape.Volume, 'density_kg_per_mm3': 2.70e-6,
            'mass_kg_each_estimate': shape.Volume*2.70e-6,
            'overall_LWH_mm': [90, 30, 34], 'flange_thickness_mm': 5,
            'web_width_thickness_mm': [60, 17],
            'seat_depth_mm': 9, 'rear_wall_mm': 8,
            'source_seat_depth_mm': 3, 'source_floor_offset_mm': 0.15,
            'seat_flat_distance_mm': 8.25, 'seat_large_arc_radius_mm': 9.70,
            'proposed_fit_profile_tolerance_mm': 0.05,
            'fit_note': 'Motor drawing flat maximum8.15 vs pocket minimum8.20 gives nominal minimum0.05mm on flats only. Full contour, corner radii and delivered revision need received-part gauging before release.',
            'motor_holes_diameter_mm': 2.8, 'motor_holes_PCD_mm': 15.2,
            'motor_screw': '3x M2.5x12 per mount, nominal4mm engagement in max5mm hole',
            'frame_holes_diameter_mm': 6.6, 'frame_hole_pitch_mm': 75,
            'frame_screw': '2x M6x12 per mount, direct head seating on5mm flange',
            'cable_through_throat_width_mm': 7,
            'cable_front_and_lower_relief_width_mm': 9.5,
            'ground_clearance_bracket_mm': 35,
            'scope': 'Source motor-seat analytic curves reused with explicit offset; external body, deeper pocket, wider cable slot and chassis fastening are new. Native bracket STEP conversion is not claimed.'}

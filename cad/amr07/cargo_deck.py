"""Removable, low cargo deck for A6; no document or GUI side effects.

Use build_deck_specs() in FreeCAD and add each returned shape to the assembly.
Strap routes and cargo volume are references, not measured purchased geometry.
The slot nut envelopes are isolated so the frame reviewer can replace them.
Pure-Python screening() is deliberately not a complete vehicle certification.
"""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent


def parameters():
    return json.loads((HERE / 'deck_parameters.json').read_text())


def screening(cfg=None):
    p = cfg or parameters()
    s = p['structural_screening']
    payload_force = s['payload_kg'] * 9.80665
    dead_force = s['plate_borne_dead_mass_allowance_kg'] * 9.80665
    restraint_force = s['strap_vertical_legs'] * s['strap_pretension_N_each']
    load = payload_force + dead_force + restraint_force
    span, width, contact = s['support_span_mm'], s['effective_strip_width_mm'], s['loaded_length_mm']
    t, young, proof = s['minimum_thickness_for_screening_mm'], s['youngs_modulus_MPa'], s['conditional_proof_stress_MPa']
    section, inertia = width*t*t/6, width*t**3/12
    # Central partial UDL on a simply supported strip (ignore plate action).
    moment = load*(2*span-contact)/8
    stress = moment/section
    delta = load*(8*span**3-4*span*contact**2+contact**3)/(384*young*inertia)
    factor = s['static_safety_factor_target']
    point_width = s['rejected_point_load_patch_width_mm']
    point_section = point_width*t*t/6
    point_stress = (load*span/4)/point_section
    return {
        'scope': 'Central200x200 uniform equivalent load including plate-borne dead mass and four strap legs. Upward strap-anchor reactions are ignored for this comparison. Local forces/contact and joints remain to be verified.',
        'payload_kg': s['payload_kg'], 'payload_force_N': payload_force,
        'plate_borne_dead_mass_allowance_kg': s['plate_borne_dead_mass_allowance_kg'],
        'dead_force_N': dead_force, 'strap_vertical_force_N': restraint_force,
        'service_force_N': load,
        'factored_force_N': factor*load,
        'minimum_thickness_mm': t, 'strip_section_modulus_mm3': section,
        'service_bending_moment_Nmm': moment,
        'service_bending_stress_MPa': stress,
        'factored_bending_stress_MPa': factor*stress,
        'conditional_proof_stress_MPa': proof,
        'conditional_simple_bending_safety_factor': proof/stress,
        'service_center_deflection_mm': delta,
        'factored_center_deflection_mm': factor*delta,
        'conditional_simple_bending_meets_target': factor*stress <= proof,
        'arbitrary_total_load_on_50mm_strip_service_MPa': point_stress,
        'arbitrary_point_load_factored_MPa': factor*point_stress,
        'point_load_permitted': False,
        'rejected_3mm_at_min2p87_factored_MPa': factor*moment/(width*2.87**2/6),
        'sensitivity_50N_each_strap_factored_MPa': factor*(payload_force+dead_force+4*50)*(2*span-contact)/8/section,
        'sensitivity_50N_is_operating_permission': False,
        'vehicle_SF2_certified': False,
        'deck_SF2_certified': False,
    }


def build_deck_specs(cfg=None, include_reference=True, slotnut_factory=None):
    """Return dictionaries: name, shape, group, material, color, label, note.

    Hardware also has hardware_spec, diameter_mm and length_mm as applicable.
    All coordinates are assembly/world millimetres. No App.newDocument/save.
    slotnut_factory(x,y,frame_top_z,(0,0,-1)) returns the revised HNTT6 shape.
    Without that callback six slot nuts are deliberately omitted from CAD and
    carried as a mass allowance; obsolete legacy nut geometry is never reused.
    """
    import FreeCAD as App
    import Part
    p = cfg or parameters()
    g, h = p['geometry'], p['hardware']
    V = App.Vector
    specs = []
    al, steel, belt = (.70, .75, .81), (.45, .48, .52), (.13, .16, .18)

    def box(x, y, z, a, b, c):
        return Part.makeBox(a, b, c, V(x, y, z))

    def cyl(r, height, x, y, z):
        return Part.makeCylinder(r, height, V(x, y, z))

    def cut(shape, cutters):
        return shape.cut(Part.makeCompound(cutters)).removeSplitter()

    def add(name, shape, material='aluminum', label='', note='', **extra):
        assert shape.isValid() and not shape.isNull() and shape.Volume > 0, name
        row = {'name': name, 'shape': shape,
               'group': '08_CargoDeck' if material != 'reference' else '09_CargoReference',
               'material': material, 'color': steel if material == 'steel' else al,
               'label': label or name, 'note': note or 'Nominal fabrication candidate; inspect and validate before loaded use.'}
        row.update(extra)
        specs.append(row)

    z0, z1 = g['plate_bottom_top_z_mm']
    mount_holes = g['frame_holes_xy_mm']
    stop_holes = g['stop_holes_xy_mm']
    cut_height = z1-z0+2
    holes = [cyl(g['frame_hole_diameter_mm']/2, cut_height, x, y, z0-1) for x, y in mount_holes]
    holes += [cyl(g['stop_hole_diameter_mm']/2, cut_height, x, y, z0-1) for x, y in stop_holes]
    for slot in g['strap_slots']:
        x, y = slot['center_xy_mm']
        length, width = slot['overall_length_width_mm']
        r, spacing = width/2, length-width
        cutter = cyl(r, cut_height, -spacing/2, 0, z0-1).fuse(cyl(r, cut_height, spacing/2, 0, z0-1))
        cutter = cutter.fuse(box(-spacing/2, -r, z0-1, spacing, width, cut_height))
        if slot['long_axis'] == 'y':
            cutter.rotate(V(0, 0, 0), V(0, 0, 1), 90)
        cutter.translate(V(x, y, 0))
        holes.append(cutter)
    add('CargoDeckPlate', cut(box(-150, -150, z0, 300, 300, z1-z0), holes),
        label='A5052 cargo plate 300x300x4 | top Z118',
        source=p['procurement']['plate']['url'],
        note='14 round holes +4 obround slots; deburr and pad webbing edges. Temper/proof strength and minimum thickness require confirmation.')
    for name, y in [('R', -135), ('L', 135)]:
        support = box(-150, y-7.5, g['frame_top_z_mm'], 300, 15, 15)
        support = cut(support, [cyl(3.3, 17, x, y, 98) for x in (-120, 0, 120)])
        add('CargoDeckSupport'+name, support,
            label='Al solid bar 15x15 L300 | continuous rail bearing',
            source=p['procurement']['square_bar']['url'])
    for name, radial, axis in [('XP', 109.5, 'x'), ('XN', -109.5, 'x'), ('YP', 109.5, 'y'), ('YN', -109.5, 'y')]:
        if axis == 'x':
            stop = box(radial-7.5, -25, z1, 15, 50, 15)
            pts = [(radial, -19), (radial, 19)]
        else:
            stop = box(-25, radial-7.5, z1, 50, 15, 15)
            pts = [(-19, radial), (19, radial)]
        add('CargoStop'+name, cut(stop, [cyl(2.25, 17, x, y, z1-1) for x, y in pts]),
            label='Al stop 15x15 L50 | inner face102 | not a lifting point')

    def screw(name, x, y, seating_z, diameter, length):
        radius = {4: 3.5, 6: 5}[diameter]
        shape = cyl(diameter/2, length, x, y, seating_z-length).fuse(cyl(radius, diameter, x, y, seating_z))
        add(name, shape, 'steel', hardware_spec=f'M{diameter}x{length} socket screw',
            diameter_mm=diameter, length_mm=length,
            note='Unthreaded envelope; verify thread engagement and tightening for received hardware.')

    for i, (x, y) in enumerate(mount_holes):
        for k in range(2):
            washer = cyl(6, 1.6, x, y, z1+k*1.6).cut(cyl(3.2, 1.6, x, y, z1+k*1.6))
            add('CargoDeckWasher'+str(i)+'_'+str(k), washer, 'steel',
                hardware_spec='M6 JIS B1256 grade A washer 12x6.4x1.6',
                note='Two standard washers per frame screw; measure combined thickness and seating. Not a spring washer.')
        screw('CargoDeckBolt'+str(i), x, y, z1+3.2, 6, h['frame_bolt_length_mm'])
        if slotnut_factory is not None:
            nut = slotnut_factory(x, y, g['frame_top_z_mm'], (0, 0, -1))
            add('SlotNut_CargoDeck'+str(i), nut, 'steel', hardware_spec='HNTT6-6 slot nut',
                note='Revised supplier-dimensioned slot-nut geometry supplied by assembly builder; actual thread lead-in/preload remain to verify.')
    for i, (x, y) in enumerate(stop_holes):
        screw('CargoStopBolt'+str(i), x, y, z1+15, 4, 25)
        washer = cyl(4.5, .8, x, y, z0-.8).cut(cyl(2.15, .8, x, y, z0-.8))
        add('CargoStopWasher'+str(i), washer, 'steel', hardware_spec='M4 plain washer 9x4.3x0.8')
        radius, zn = 7/math.sqrt(3), z0-.8-3.2
        pts = [V(x+radius*math.cos(math.radians(60*j)), y+radius*math.sin(math.radians(60*j)), zn) for j in range(6)]
        nut = Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0, 0, 3.2)).cut(cyl(2.1, 3.2, x, y, zn))
        add('CargoStopNut'+str(i), nut, 'steel', hardware_spec='M4 plain hex nut')

    if include_reference:
        add('CargoFlatBottomReference', box(-100, -100, z1, 200, 200, 160), 'reference',
            label='REFERENCE cargo200x200x160 | container mass included in payload',
            note='Example only; required cargo CG x/ywithin30 and Z<=220. Not a purchased container or a rated load model.',
            color=(.75, .55, .20), transparency=80)
        # Routing reference for two crossed25mm straps; buckle/edge pads/slack
        # are not represented. The purchased125g/strap is in mass_report.
        def route_strip(points, width=25, thickness=1.5):
            pieces = []
            for a, b in zip(points, points[1:]):
                dx, dz = b[0]-a[0], b[1]-a[1]
                length = math.hypot(dx, dz)
                nx, nz = -dz/length*thickness/2, dx/length*thickness/2
                verts = [V(a[0]+nx, -width/2, a[1]+nz), V(b[0]+nx, -width/2, b[1]+nz),
                         V(b[0]-nx, -width/2, b[1]-nz), V(a[0]-nx, -width/2, a[1]-nz)]
                pieces.append(Part.Face(Part.makePolygon(verts+[verts[0]])).extrude(V(0, width, 0)))
            shape = pieces[0]
            for piece in pieces[1:]:
                shape = shape.fuse(piece)
            return shape.removeSplitter()
        for name, bottom, top, rotation in [('X', 111.75, z1+160+.75, 0), ('Y', 113.25, z1+160+2.25, 90)]:
            shoulder = z1+16.5
            points = [(-120, bottom), (-120, shoulder), (-100.75, shoulder), (-100.75, top),
                      (100.75, top), (100.75, shoulder), (120, shoulder), (120, bottom), (-120, bottom)]
            route = route_strip(points)
            route.rotate(V(0, 0, 0), V(0, 0, 1), rotation)
            add('CargoStrapRoute'+name, route, 'reference', color=belt,
                label='BT-2520BK route only | buckle/edge protection not shown',
                note='Routing on example cargo only; do not derive mass or restraint rating from the CAD strip.')
    return specs


make_deck = build_deck_specs


def mass_report(specs):
    p = parameters()
    rows = []
    for spec in specs:
        if spec['material'] == 'reference':
            continue
        density = 7.85e-6 if spec['material'] == 'steel' else 2.70e-6
        rows.append({'name': spec['name'], 'mass_kg': spec['shape'].Volume*density,
                     'basis': 'nominal CAD volume x density'})
    cad_mass = sum(row['mass_kg'] for row in rows)
    absent_nuts = 6-sum(spec['name'].startswith('SlotNut_CargoDeck') for spec in specs)
    absent_nut_mass = absent_nuts*p['mass_budget']['unmodeled_slot_nut_each_allowance_kg']
    strap_mass = 2*p['procurement']['cargo_straps']['catalog_each_mass_kg']
    padding = p['mass_budget']['edge_protection_and_slack_retention_kg']
    return {'cad_metal_and_fasteners_kg': cad_mass, 'catalog_two_straps_kg': strap_mass,
            'slot_nuts_missing_from_CAD_count': absent_nuts,
            'unmodeled_slot_nut_mass_allowance_kg': absent_nut_mass,
            'edge_protection_and_slack_retention_allowance_kg': padding,
            'total_added_base_mass_kg': cad_mass+absent_nut_mass+strap_mass+padding,
            'measured': False, 'rows': rows}


if __name__ == '__main__':
    print(json.dumps(screening(), ensure_ascii=False, indent=2))

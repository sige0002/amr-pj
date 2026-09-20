"""A3 electrical packaging reservations over the physical DDSM115 chassis.

Run in FreeCAD to build/validate/save. Importing this module outside FreeCAD is
safe for checking the configuration and the rounded centreline lengths only.
The route tubes are reservations, not released wires or verified connectors.
"""
from itertools import combinations
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent
EPS = 1e-8
VOLUME_TOL = 0.001


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def vsub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(a, factor):
    return tuple(x * factor for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def length(a):
    return math.sqrt(dot(a, a))


def unit(a):
    size = length(a)
    if size <= EPS:
        raise ValueError('Zero-length route segment')
    return scale(a, 1 / size)


def route_plan(entry):
    """Circular fillets on a 3-D polyline; returns pure-Python geometry/lengths."""
    points = [tuple(float(x) for x in p) for p in entry['points_mm']]
    radius, bend = entry['radius_mm'], entry['bend_radius_mm']
    if len(points) < 2 or any(len(p) != 3 for p in points):
        raise ValueError(entry['name'] + ': at least two 3-D points required')
    if not all(math.isfinite(x) for p in points for x in p) or not 0 < radius < bend:
        raise ValueError(entry['name'] + ': invalid coordinates/radii')
    distances = [length(vsub(b, a)) for a, b in zip(points, points[1:])]
    if min(distances) <= EPS:
        raise ValueError(entry['name'] + ': repeated route point')
    corners = [None] * len(points)
    trims = [0.0] * len(points)
    for i in range(1, len(points) - 1):
        incoming = unit(vsub(points[i], points[i - 1]))
        outgoing = unit(vsub(points[i + 1], points[i]))
        cosine = max(-1.0, min(1.0, dot(incoming, outgoing)))
        angle = math.acos(cosine)
        if angle < EPS:
            continue
        if math.pi - angle < EPS:
            raise ValueError(entry['name'] + ': route reverses at a corner')
        tangent = bend * math.tan(angle / 2)
        trims[i] = tangent
        start = vsub(points[i], scale(incoming, tangent))
        end = vadd(points[i], scale(outgoing, tangent))
        normal = unit(vsub(outgoing, scale(incoming, cosine)))
        centre = vadd(start, scale(normal, bend))
        mid = vadd(centre, scale(unit(vadd(vsub(start, centre), vsub(end, centre))), bend))
        corners[i] = {'type': 'arc', 'start': start, 'mid': mid, 'end': end,
                      'centre': centre, 'angle_rad': angle, 'length_mm': bend * angle}
    for i, segment_length in enumerate(distances):
        if trims[i] + trims[i + 1] >= segment_length - EPS:
            raise ValueError(entry['name'] + ': adjacent fillets consume segment ' + str(i))
    pieces, current = [], points[0]
    for corner in corners[1:-1]:
        if corner is None:
            continue
        straight = length(vsub(corner['start'], current))
        if straight > EPS:
            pieces.append({'type': 'line', 'start': current, 'end': corner['start'], 'length_mm': straight})
        pieces.append(corner)
        current = corner['end']
    straight = length(vsub(points[-1], current))
    if straight > EPS:
        pieces.append({'type': 'line', 'start': current, 'end': points[-1], 'length_mm': straight})
    return {'pieces': pieces, 'points_mm': points,
            'polyline_length_mm': sum(distances),
            'rounded_length_mm': sum(p['length_mm'] for p in pieces),
            'radius_mm': radius, 'bend_radius_mm': bend}


def planning_report(cfg):
    """No CAD execution: check references and calculate centreline budgets."""
    routes = {entry['name']: entry for entry in cfg['cable_routes']}
    if len(routes) != len(cfg['cable_routes']):
        raise ValueError('Duplicate route names')
    services = set(cfg['service_xyz_LWH_mm']) | set(cfg['service_cylinders'])
    equipment = {name + '_RESERVED' for name in cfg['zones_xyz_LWH_mm']} | set(cfg['connection_nodes'])
    measurements = {}
    for name, entry in routes.items():
        if set(entry['allowed_service']) - services:
            raise ValueError(name + ': unknown service exception')
        if set(entry['allowed_equipment_connections']) - equipment:
            raise ValueError(name + ': unknown connection reservation')
        plan = route_plan(entry)
        item = {k: v for k, v in plan.items() if k not in ('pieces', 'points_mm')}
        if entry.get('fixed_supplied_harness'):
            budget = cfg['fixed_harness_budget_mm']
            item.update({'published_total_nominal_mm': budget['nominal_total'],
                         'published_total_minimum_mm': budget['minimum_total'],
                         'remaining_to_minimum_mm': budget['minimum_total'] - plan['rounded_length_mm'],
                         'remaining_to_nominal_mm': budget['nominal_total'] - plan['rounded_length_mm'],
                         'centreline_within_minimum_total': plan['rounded_length_mm'] <= budget['minimum_total'],
                         'connector_and_slack_fit_verified': False})
        measurements[name] = item
    for name, node in cfg['connection_nodes'].items():
        x, y, z, sx, sy, sz = node['xyz_LWH_mm']
        point = node['point_mm']
        if not all(lo <= value <= hi for lo, value, hi in zip((x, y, z), point, (x + sx, y + sy, z + sz))):
            raise ValueError(name + ': junction point lies outside its reservation')
        for route_name in node['route_names']:
            if route_name not in routes or name not in routes[route_name]['allowed_equipment_connections']:
                raise ValueError(name + ': inconsistent route membership')
            ends = (routes[route_name]['points_mm'][0], routes[route_name]['points_mm'][-1])
            if min(length(vsub(end, point)) for end in ends) > EPS:
                raise ValueError(name + ': shared route must terminate at the declared point')
    return measurements


def build_layout():
    import FreeCAD as App
    import Part

    cfg = json.loads((HERE / 'electrical_layout_parameters.json').read_text())
    measurements = planning_report(cfg)
    base_name, name = cfg['base_document'], cfg['layout_document']
    if base_name not in App.listDocuments():
        App.openDocument(str(HERE / (base_name + '.FCStd')))
    base = App.getDocument(base_name)
    if name in App.listDocuments():
        App.closeDocument(name)
    doc = App.newDocument(name)
    doc.Label = 'A3 electrical packaging STUDY | DDSM115 | reference zones/routes'
    groups, parts = {}, []
    V = App.Vector

    def add(name, shape, group, color, transparency=0, note='', role='reference_only'):
        if group not in groups:
            groups[group] = doc.addObject('App::DocumentObjectGroup', group)
        obj = doc.addObject('PartDesign::Feature', name)
        obj.Shape = shape
        for prop, value in [('DesignRole', role), ('DesignNote', note)]:
            obj.addProperty('App::PropertyString', prop, 'Packaging')
            setattr(obj, prop, value)
        groups[group].addObject(obj)
        if App.GuiUp:
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = (.15, .18, .20)
            obj.ViewObject.DisplayMode = 'Flat Lines'
            obj.ViewObject.Transparency = transparency
        return obj

    for source in base.Objects:
        if source.TypeId != 'PartDesign::Feature' or getattr(source, 'MaterialBasis', 'reference') == 'reference':
            continue
        color = source.ViewObject.ShapeColor if App.GuiUp else (.7, .7, .7)
        obj = add(source.Name, source.Shape.copy(), 'Chassis', color,
                  note='Physical geometry copied from ' + base_name + '/' + source.Name,
                  role='copied_A3_physical_geometry')
        obj.Label = source.Label
        parts.append(obj)
    if not parts or doc.getObject('FrontElectronicsTrayPLA') is None:
        raise ValueError('A3 physical chassis/front electronics tray was not found')

    def box(values):
        x, y, z, sx, sy, sz = values
        return Part.makeBox(sx, sy, sz, V(x, y, z))

    battery = add('BatteryBody_ONLY', box(cfg['battery_body_xyz_LWH_mm']), 'Reservations', (.88, .58, .16), 55,
                  'Unselected battery BODY only. Connector/adapter geometry and battery capacity are not verified.')
    zones = []
    for zone_name, dims in cfg['zones_xyz_LWH_mm'].items():
        color = (.35, .45, .75) if zone_name in ('ComputerAndControl', 'USBRS485') else (.72, .47, .23)
        if zone_name == 'EmergencyStopAccess':
            color = (.8, .14, .16)
        zones.append(add(zone_name + '_RESERVED', box(dims), 'Reservations', color, 65,
                         cfg['zone_status'].get(zone_name, cfg['zone_status']['default'])))
    nodes = {n: add(n, box(e['xyz_LWH_mm']), 'ConnectionReferences', (.65, .25, .75), 75, e['note'])
             for n, e in cfg['connection_nodes'].items()}
    services = {n: add(n, box(dims), 'ServiceClearances', (.30, .75, .95), 85,
                       'Temporary service reservation; disconnect battery cable before battery removal.')
                for n, dims in cfg['service_xyz_LWH_mm'].items()}
    for service_name, entry in cfg['service_cylinders'].items():
        shape = Part.makeCylinder(entry['radius_mm'], entry['length_mm'], V(*entry['base_center_mm']), V(*entry['axis']))
        services[service_name] = add(service_name, shape, 'ServiceClearances', (.30, .75, .95), 85, cfg['tire_removal_note'])
    if App.GuiUp:
        for hidden in cfg['hidden_services']:
            services[hidden].ViewObject.Visibility = False

    def route_tube(plan):
        edges = []
        for piece in plan['pieces']:
            if piece['type'] == 'line':
                edges.append(Part.makeLine(V(*piece['start']), V(*piece['end'])))
            else:
                edges.append(Part.Arc(V(*piece['start']), V(*piece['mid']), V(*piece['end'])).toShape())
        wire = Part.Wire(edges)
        direction = unit(vsub(plan['points_mm'][1], plan['points_mm'][0]))
        profile = Part.Wire([Part.makeCircle(plan['radius_mm'], V(*plan['points_mm'][0]), V(*direction))])
        return wire.makePipeShell([profile], True, False), wire.Length

    routes = []
    for entry in cfg['cable_routes']:
        shape, cad_length = route_tube(route_plan(entry))
        colors = {'power': (.88, .20, .07), 'signal': (.10, .45, .88), 'integrated_motor_harness': (.65, .20, .72)}
        obj = add('Route_' + entry['name'], shape, 'CableRouteReservations', colors[entry['kind']],
                  note='Bundle envelope with planning bend radius. Actual wire/connector/bend minimum not verified.')
        obj.addProperty('App::PropertyString', 'CableKind', 'Packaging')
        obj.CableKind = entry['kind']
        obj.addProperty('App::PropertyLength', 'CentrelineLength', 'Packaging')
        obj.CentrelineLength = cad_length
        item = measurements[entry['name']]
        item['cad_wire_length_mm'] = cad_length
        item['analytic_vs_cad_length_difference_mm'] = abs(cad_length - item['rounded_length_mm'])
        routes.append((obj, entry))

    features = [o for o in doc.Objects if o.TypeId == 'PartDesign::Feature']
    bounds = {o.Name: o.Shape.optimalBoundingBox(False, False) for o in features}

    def common(a, b):
        if not bounds[a.Name].intersect(bounds[b.Name]):
            return None
        shape = a.Shape.common(b.Shape)
        return shape if shape.Volume > VOLUME_TOL else None

    base_hits, service_hits, zone_hits, equipment_hits = [], [], [], []
    allowed_service_hits, allowed_equipment_hits = [], []
    all_equipment = [battery, *zones, *nodes.values()]
    for reference in [*all_equipment, *services.values(), *[o for o, _ in routes]]:
        for physical in parts:
            shape = common(reference, physical)
            if shape is not None:
                base_hits.append({'reference': reference.Name, 'chassis': physical.Name, 'mm3': shape.Volume})
    # The battery body is the item being removed, not an obstruction to its own service volume.
    for service_name, service in services.items():
        for reference in [*zones, *nodes.values()]:
            shape = common(service, reference)
            if shape is not None:
                service_hits.append({'service': service_name, 'reference': reference.Name, 'mm3': shape.Volume})
        for route, entry in routes:
            shape = common(service, route)
            if shape is not None:
                row = {'service': service_name, 'reference': route.Name, 'mm3': shape.Volume}
                (allowed_service_hits if service_name in entry['allowed_service'] else service_hits).append(row)
    for a, b in combinations(all_equipment, 2):
        shape = common(a, b)
        if shape is not None:
            zone_hits.append({'a': a.Name, 'b': b.Name, 'mm3': shape.Volume})
    for route, entry in routes:
        for equipment in all_equipment:
            shape = common(route, equipment)
            if shape is not None:
                row = {'route': route.Name, 'equipment': equipment.Name, 'mm3': shape.Volume}
                target = allowed_equipment_hits if equipment.Name in entry['allowed_equipment_connections'] else equipment_hits
                target.append(row)

    route_crossings, intentional_contacts = [], []
    for (a, ea), (b, eb) in combinations(routes, 2):
        intersection = common(a, b)
        if intersection is None:
            continue
        remaining = intersection
        for node_name, node_cfg in cfg['connection_nodes'].items():
            if ea['name'] not in node_cfg['route_names'] or eb['name'] not in node_cfg['route_names']:
                continue
            local = remaining.common(nodes[node_name].Shape)
            if local.Volume > VOLUME_TOL:
                intentional_contacts.append({'a': a.Name, 'b': b.Name, 'connection_node': node_name,
                                             'kind_a': ea['kind'], 'kind_b': eb['kind'], 'mm3': local.Volume,
                                             'meaning': 'Reserved co-location near separate connector ends; not a wire-to-wire short'})
                remaining = remaining.cut(nodes[node_name].Shape)
        if remaining.Volume > VOLUME_TOL:
            route_crossings.append({'a': a.Name, 'b': b.Name, 'kind_a': ea['kind'], 'kind_b': eb['kind'],
                                    'unexpected_mm3': remaining.Volume, 'total_intersection_mm3': intersection.Volume})

    invalid = [o.Name for o in features if o.Shape.isNull() or not o.Shape.isValid()]
    length_errors = [n for n, item in measurements.items() if item['analytic_vs_cad_length_difference_mm'] > 1e-5]
    over_budget = [n for n, item in measurements.items() if item.get('centreline_within_minimum_total') is False]
    passed = not any((base_hits, service_hits, zone_hits, equipment_hits, route_crossings, invalid, length_errors, over_budget))
    results = {
        'status': 'reference_packaging_only_not_electrical_or_assembly_release',
        'nominal_geometry_checks_passed': passed,
        'base_document': base_name, 'layout_document': name,
        'base_physical_objects': len(parts), 'reference_routes': len(routes),
        'front_deck_is_copied_physical_part': True,
        'reference_vs_chassis_collisions': base_hits,
        'permanent_reservation_vs_service_collisions': service_hits,
        'equipment_zone_collisions': zone_hits,
        'route_envelope_intersections': route_crossings,
        'routes_vs_unrelated_equipment': equipment_hits,
        'intentional_route_connection_overlaps': intentional_contacts,
        'allowed_equipment_connection_overlaps': allowed_equipment_hits,
        'battery_lead_service_overlaps_requiring_disconnection': allowed_service_hits,
        'invalid_shapes': invalid, 'route_length_check_failures': length_errors,
        'fixed_harness_centreline_over_budget': over_budget,
        'route_measurements': measurements,
        'collision_threshold_mm3': VOLUME_TOL,
        'connection_exception_scope': 'Only intersection portions inside declared connection boxes are exempt; all outside portions are failures.',
        'battery_connector_route_must_disconnect_for_service': True,
        'upper_service_height_mm': 190,
        'tire_service_requires_chassis_support_or_lift': True,
        'fixed_harness_connector_and_slack_fit_verified': False,
        'not_checked': [
            'Selected battery/adapter geometry, retention and removal mechanism',
            'Actual USB-RS485B and other device dimensions, terminals, cooling and mounting',
            'DDSM supplied connector bodies, bundle diameter, minimum bend radius and installation slack',
            'Tire extraction/fit, fastening tool access and real maintenance procedure',
            'Cable/clamp installation, current ratings, EMI, bus termination, ground reference and electrical stop circuit',
            'Battery endurance, protection, regeneration and temperature',
        ],
    }
    (HERE / 'electrical_layout_validation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    doc.recompute()
    if App.GuiUp:
        import FreeCADGui as Gui
        App.setActiveDocument(name)
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    # Preserve a reviewable document even when validation reports a collision.
    doc.saveAs(str(HERE / (name + '.FCStd')))
    print(json.dumps(results, ensure_ascii=False))
    if not passed:
        raise AssertionError('A3 electrical packaging has unresolved geometry checks; see electrical_layout_validation.json')
    return results


if __name__ == '__main__':
    build_layout()

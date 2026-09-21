"""Separate printed-deck fit concept; does not overwrite the A6 assembly or BOM."""
from pathlib import Path
from itertools import combinations, product
import hashlib
import json
import math
import sys
import subprocess
import tempfile
import FreeCAD as App
import Part
import MeshPart

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE))
from hardware_geometry import deck_slotnut
from cargo_deck import build_deck_specs

V = App.Vector
P = json.loads((HERE/'parameters.json').read_text())
NAME = 'AMR01_PrintedDeck_P0'


def main():
    # P0 is a historical comparison. Do not silently inherit D2's six-block
    # supports and extra fixtures when regenerating the old printed concept.
    revision='7f6bf0501322def11120138fecc62a40ea970170'
    snapshot=tempfile.TemporaryDirectory(prefix='amr-p0-source-')
    source=Path(snapshot.name)/'AMR01_M0601C_A6.FCStd'
    def historical(name):
        return subprocess.check_output(['git','-C',str(BASE),'show',revision+':cad/amr07/'+name])
    source.write_bytes(historical(source.name))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    old = App.openDocument(str(source))
    height_change = P['plate_thickness_mm']-4
    doc = App.newDocument(NAME)
    doc.Label = 'PLA deck P0 | fit concept | 50mm M4 grid | not load qualified'
    removed = []
    for obj in old.Objects:
        if obj.TypeId != 'PartDesign::Feature':
            continue
        if obj.Name == 'CargoDeckPlate' or obj.Name.startswith(tuple(P['removed_feature_prefixes'])):
            removed.append(obj.Name)
            continue
        new = doc.copyObject(obj, False)
        if obj.Name.startswith(('CargoStop', 'CargoStrapRoute')) or obj.Name == 'CargoFlatBottomReference':
            shape = new.Shape.copy()
            shape.translate(V(0, 0, height_change))
            new.Shape = shape
            new.Label += f' | raised{height_change}mm with printed deck'

    def add(name, shape, material, note):
        assert shape.isValid() and len(shape.Solids) == 1, name
        o = doc.addObject('PartDesign::Feature', name)
        o.Shape = shape
        o.addProperty('App::PropertyString', 'MaterialBasis', 'Design')
        o.MaterialBasis = material
        o.addProperty('App::PropertyString', 'ModelNote', 'Design')
        o.ModelNote = note
        return o

    def cyl(r, z, h, x, y):
        return Part.makeCylinder(r, h, V(x, y, z))

    def hexagon(x, y, z, across, depth):
        r = across/math.sqrt(3)
        pts = [V(x+r*math.cos(i*math.pi/3), y+r*math.sin(i*math.pi/3), z) for i in range(6)]
        return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0, 0, depth))

    # Keep the original stop holes and strap slots, but not the original 4 mm plate.
    z0 = P['plate_bottom_z_mm']
    z1 = z0+P['plate_thickness_mm']
    cut_height = z1-z0+2
    plate = Part.makeBox(300, 300, z1-z0, V(-150, -150, z0))
    cuts = []
    cfg = json.loads(historical('deck_parameters.json'))
    cfg['geometry']['plate_bottom_top_z_mm'] = [z0, z1]
    for spec in build_deck_specs(cfg=cfg, include_reference=True):
        if spec['name'].startswith('CargoStrapRoute'):
            doc.getObject(spec['name']).Shape = spec['shape']
    # Locally route the Y strap above the added bars, in printed underside
    # recesses. Keep its underside loop above the battery reservation.
    shoulder, top = z1+16.5, z1+160+2.25
    route = [(-120,113.25),(-120,shoulder),(-100.75,shoulder),(-100.75,top),
             (100.75,top),(100.75,shoulder),(120,shoulder),(120,113.25),
             (77,113.25),(73,115),(57,115),(53,113.25),
             (-53,113.25),(-57,115),(-73,115),(-77,113.25),(-120,113.25)]
    pieces=[]
    for a,b in zip(route,route[1:]):
        dx,dz=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dz)
        nx,nz=-dz/length*.75,dx/length*.75
        pts=[V(a[0]+nx,-12.5,a[1]+nz),V(b[0]+nx,-12.5,b[1]+nz),
             V(b[0]-nx,-12.5,b[1]-nz),V(a[0]-nx,-12.5,a[1]-nz)]
        pieces.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,25,0)))
    strap=pieces[0].multiFuse(pieces[1:]).removeSplitter()
    strap.rotate(V(0,0,0),V(0,0,1),90)
    doc.getObject('CargoStrapRouteY').Shape=strap
    for y in (-65,65):
        cuts.append(Part.makeBox(26,32,3,V(-13,y-16,z0-1)))
    for x, y in cfg['geometry']['stop_holes_xy_mm']:
        cuts.append(cyl(2.25, z0-1, z1-z0+2, x, y))
    for slot in cfg['geometry']['strap_slots']:
        x, y = slot['center_xy_mm']
        s = cyl(3, z0-1, cut_height, -12, 0).fuse(cyl(3, z0-1, cut_height, 12, 0))
        s = s.fuse(Part.makeBox(24, 6, cut_height, V(-12, -3, z0-1)))
        if slot['long_axis'] == 'y':
            s.rotate(V(0,0,0), V(0,0,1), 90)
        s.translate(V(x,y,0)); cuts.append(s)
    grid = list(product(P['grid_axis_mm'], repeat=2))
    for x, y in grid:
        cuts += [cyl(2.25, z0-1, cut_height, x, y),
                 hexagon(x, y, z0-1, P['nut_pocket_across_flats_mm'], P['nut_pocket_depth_mm']+1)]
    attachments = list(product(P['attachment_x_mm'], (-135,135))) + list(product(P['inner_attachment_x_mm'], (-65,65)))
    for x, y in attachments:
        cuts += [cyl(5, z0-1, cut_height, x, y), cyl(7, 118, z1-118+1, x, y)]
    plate = plate.cut(Part.makeCompound(cuts)).removeSplitter()
    seam = P['seam_xy_mm'][0]
    assert P['seam_xy_mm'][1] == seam
    half_gap = P['seam_gap_mm']/2
    intervals = [(-150, seam-half_gap), (seam+half_gap, 150)]
    panels = []
    for i, (xs, ys) in enumerate(product(intervals, repeat=2), 1):
        x0, x1 = xs; y0, y1 = ys
        s = plate.common(Part.makeBox(x1-x0, y1-y0, z1-z0, V(x0,y0,z0))).removeSplitter()
        name = f'PrintedDeckPanel{i}'
        obj = add(name, s, 'PLA', f'{z1-z0}mm solid geometry; slicer and actual filament unconfirmed; no payload rating. M4 nuts optional, flush bottom tips only.')
        panels.append(obj)
        # Put each export top-side down on the bed; avoids bridging nut pockets.
        printable = s.copy()
        printable.rotate(V(0,0,0), V(1,0,0), 180)
        bb = printable.BoundBox
        printable.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
        mesh = MeshPart.meshFromShape(Shape=printable, LinearDeflection=.06, AngularDeflection=.25, Relative=False)
        mesh.write(str(HERE/(name+'.stl')))
        assert max(printable.BoundBox.XLength, printable.BoundBox.YLength) < 200
    for y in (-65,65):
        s = Part.makeBox(300,15,15,V(-150,y-7.5,99))
        s = s.cut(Part.makeCompound([cyl(3.3,98,17,x,y) for x in P['inner_attachment_x_mm']])).removeSplitter()
        add('ExtraSupport'+('L' if y>0 else 'R'), s, 'aluminum', 'Additional15x15L300 metal support; one extra995mm stock for two. Old PLA trays and mounting screws removed.')
        for i,x in enumerate(P['inner_attachment_x_mm']):
            suffix = ('L' if y>0 else 'R')+str(i)
            for k in range(2):
                add('ExtraWasher'+suffix+str(k), cyl(6,118+k*1.6,1.6,x,y).cut(cyl(3.2,118+k*1.6,1.6,x,y)), 'steel', 'M6 grade A1.6 washer, nominal only.')
            add('ExtraFrameBolt'+suffix, cyl(3,91.2,30,x,y).fuse(cyl(5,121.2,6,x,y)), 'steel', 'M6x30, same metal stack as A6. Check actual penetration/preload.')
            add('ExtraSlotNut'+suffix, deck_slotnut(x,y,99,(0,0,-1)), 'steel', 'HNTT6-6, additional purchase not priced.')
    for i,(x,y) in enumerate(attachments):
        add('CompressionSleeve'+str(i), cyl(5,114,4,x,y).cut(cyl(3.3,114,4,x,y)), 'aluminum', 'OD10 ID6.6 L4 candidate; purchase/process and tolerance not selected. Direct washer-to-metal-to-bar load path.')
    # Existing stop bolts are too short after raising the deck. Keep original
    # underside washer/nut at Z114, and use an M4x30 envelope.
    for o in list(doc.Objects):
        if o.Name.startswith(('CargoStopWasher','CargoStopNut')):
            s=o.Shape.copy(); s.translate(V(0,0,-height_change)); o.Shape=s
        elif o.Name.startswith('CargoStopBolt'):
            b=o.Shape.BoundBox; x,y=b.Center.x,b.Center.y
            o.Shape=cyl(2,z1+15-30,30,x,y).fuse(cyl(3.5,z1+15,4,x,y))
            o.ModelNote='M4x30 substituted for M4x25; candidate. Actual thread engagement required.'
            if hasattr(o,'HardwareSpec'): o.HardwareSpec='M4x30 socket screw'
    doc.recompute()
    physical=[o for o in doc.Objects if o.MaterialBasis!='reference']
    refs=[o for o in doc.Objects if o.MaterialBasis=='reference']
    boxes={o.Name:o.Shape.BoundBox for o in physical+refs}
    hits=[]
    for a,b in combinations(physical,2):
        if boxes[a.Name].intersect(boxes[b.Name]):
            v=a.Shape.common(b.Shape).Volume
            if v>.001: hits.append({'a':a.Name,'b':b.Name,'overlap_mm3':v})
    reference_hits=[]
    for a,b in product(refs,physical):
        if boxes[a.Name].intersect(boxes[b.Name]):
            v=a.Shape.common(b.Shape).Volume
            if v>.001: reference_hits.append({'reference':a.Name,'part':b.Name,'overlap_mm3':v})
    # Per-station nut and limited screw envelope. No nut is bought or added to
    # the assembly until an actual expansion fixture is selected.
    grid_access=[]
    for x,y in grid:
        nut=hexagon(x,y,114.1,7,3.2).cut(cyl(1.7,114,4,x,y))
        screw=cyl(2,114.1,z1-114.1,x,y).fuse(cyl(3.5,z1,4,x,y))
        blocked=[]
        for o in physical:
            if not boxes[o.Name].intersect(nut.BoundBox) and not boxes[o.Name].intersect(screw.BoundBox):
                continue
            if nut.common(o.Shape).Volume>.001 or screw.common(o.Shape).Volume>.001:
                blocked.append(o.Name)
        grid_access.append({'xy_mm':[x,y],'fixture_envelope_hits':blocked})
    density={'steel':7.85e-6,'aluminum':2.7e-6,'PLA':1.24e-6}
    removed_mass=sum(old.getObject(n).Shape.Volume*density[old.getObject(n).MaterialBasis] for n in removed)
    added=[o for o in physical if old.getObject(o.Name) is None]
    added_mass=sum(o.Shape.Volume*density[o.MaterialBasis] for o in added)
    bolt_delta=sum((o.Shape.Volume-old.getObject(o.Name).Shape.Volume)*7.85e-6 for o in physical if o.Name.startswith('CargoStopBolt'))
    old_mass=json.loads(historical('assembly_validation.json'))['mass']['estimated_base_kg']
    panel_mass=sum(o.Shape.Volume*1.24e-6 for o in panels)
    report={'status':P['status'],'base_CAD_sha256':source_hash,'all_shapes_valid':all(o.Shape.isValid() for o in physical),'physical_parts':len(physical),
            'collisions':hits,'reference_collisions':reference_hits,'grid_stations':grid_access,'removed_existing_parts':removed,
            'panel_sizes_mm':[[o.Shape.BoundBox.XLength,o.Shape.BoundBox.YLength,z1-z0] for o in panels],
            'mass':{'solid_PLA_panels_kg':panel_mass,'removed_CAD_mass_kg':removed_mass,'added_CAD_mass_kg':added_mass,'stop_bolt_change_kg':bolt_delta,
                    'estimated_base_kg':old_mass-removed_mass+added_mass+bolt_delta,'actual_slicing_done':False,'weighed':False},
            'cost_comparison':{'PLA_consumption_reference_JPY':panel_mass*1000*P['solid_geometry_cost_rate_JPY_g'],
                    'extra_support_stock_reference_JPY':1507,'replaced_aluminum_plate_reference_JPY':4521,
                    'incremental_complete_cost_JPY':None,'unpriced':['10 metal compression sleeves','4 M6x30 +8 washers;4 HNTT6-6 reused from removed trays','8 M4x30 replacement bolts','new shipping/tools/labor/printing overhead','expansion fixture screws/nuts when used']},
            'not_qualified':['Actual filament and print process','Long-term creep/temperature','Local hole/nut retention','Strap slot and split-panel load transfer','Cargo-deck SF2 and impact','Electronics remounting after removing old trays']}
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['physical_parts','collisions','reference_collisions','mass','cost_comparison']},ensure_ascii=False))
    assert not hits and not reference_hits
    assert all(not r['fixture_envelope_hits'] for r in grid_access)
    assert report['mass']['estimated_base_kg']<10
    doc.saveAs(str(HERE/(NAME+'.FCStd')))
    Part.export(physical,str(HERE/(NAME+'.step')))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash


if __name__=='__main__': main()

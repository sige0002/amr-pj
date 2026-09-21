"""Export A5's 1:1 PLA fit models from the selected candidate STEP.

Run: QT_QPA_PLATFORM=offscreen freecadcmd /absolute/path/build_print_mock.py
STL, FCStd, validation and ZIP are generated without FreeCADGui. A GUI run
additionally captures previews. Selection comes from selection.json.
After GUI save/capture, refresh_bundle_after_gui() updates hashes and ZIP
without regenerating STL. These are fit models, never load-test mounts.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

try:
    import FreeCAD as App
    import Part
    import Mesh
    import MeshPart
except ImportError:
    # Allow the hash/evidence-only finalizer to run in system Python too.
    App = Part = Mesh = MeshPart = None

HERE = Path(__file__).resolve().parent
OUT = HERE / 'print-mock'
SELECTION = HERE / 'selection.json'
BASELINE = HERE.parent / 'amr05' / 'M0601C_custom_mount_quote.step'
NAME = 'M0601C_PLA_Mock_A5'
FULL_STL = 'M0601C_mount_A5_selected_PLA_mock.stl'
COUPON_STL = 'M0601C_seat_A5_fit_coupon.stl'
ZIP_NAME = 'M0601C_A5_PLA_mock_files.zip'
V = App.Vector if App is not None else None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_selection(path=None):
    path = Path(path) if path is not None else SELECTION
    data = json.loads(path.read_text(encoding='utf-8'))
    candidate = data['selected_candidate']
    relative = Path(data['candidate_step_relative'])
    assert isinstance(candidate, str) and candidate
    assert not relative.is_absolute(), 'candidate_step_relative must be relative to cad/amr06'
    source = (HERE / relative).resolve()
    source.relative_to(HERE.resolve())
    if not source.is_file():
        raise FileNotFoundError(f'Selected A5 STEP is not ready: {source}')
    return {'candidate': candidate, 'source': source, 'selection_path': path.resolve(),
            'selection_sha256': digest(path)}


def fcstd_brep_hashes(path):
    with zipfile.ZipFile(path) as archive:
        return {name: hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist() if name.endswith('.brp')}


def assert_saved_visible(path):
    with zipfile.ZipFile(path) as archive:
        if 'GuiDocument.xml' not in archive.namelist():
            raise AssertionError('FCStd has no saved GUI visibility. Open it, show both objects and save in FreeCAD GUI.')
        tree = ET.fromstring(archive.read('GuiDocument.xml'))
    providers = {node.attrib['name']: node for node in tree.iter('ViewProvider')}
    for name in ('FullMountMock', 'SeatFitCoupon'):
        node = providers[name].find("./Properties/Property[@name='Visibility']/Bool")
        assert node is not None and node.attrib.get('value') == 'true', name


def verify_unchanged_inputs(report):
    source = (OUT / report['source_step']).resolve()
    assert digest(source) == report['source_sha256'], 'Selected STEP changed; regenerate the mock.'
    selection = (OUT / report['selection_file']).resolve()
    current = json.loads(selection.read_text(encoding='utf-8'))
    assert current['selected_candidate'] == report['candidate'], 'Selected candidate changed; regenerate the mock.'
    assert (HERE / current['candidate_step_relative']).resolve() == source, 'Selected STEP path changed; regenerate the mock.'
    # A reason/status edit need not remesh the same selected geometry.
    report['selection_sha256'] = digest(selection)
    report['selection_status'] = current.get('selection_status')
    report['selection_scope'] = {key: current.get(key) for key in (
        'manufacturing_released', 'cost_reduction_achieved',
        'payload_15kg_and_SF2_verified')}
    for record in report['files']:
        assert digest(OUT / record['file']) == record['sha256'], ('STL changed', record['file'])


def write_bundle(report):
    verify_unchanged_inputs(report)
    assert digest(OUT / report['preview_document']['file']) == report['preview_document']['sha256']
    report['print_guide_sha256'] = digest(OUT / 'PRINT_GUIDE.ja.md')
    (OUT / 'validation_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    bundle = [record['file'] for record in report['files']]
    bundle += ['PRINT_GUIDE.ja.md', 'validation_results.json', report['preview_document']['file']]
    for record in report.get('GUI_evidence', []):
        assert digest(OUT / record['file']) == record['sha256']
        bundle.append(record['file'])
    with zipfile.ZipFile(OUT / ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename in bundle:
            archive.write(OUT / filename, filename)
    with zipfile.ZipFile(OUT / ZIP_NAME) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(bundle)
        for filename in bundle:
            assert archive.read(filename) == (OUT / filename).read_bytes()


def _shape_topology(shape):
    return {name: len(getattr(shape, name))
            for name in ('Solids', 'Shells', 'Faces', 'Wires', 'Edges', 'Vertexes')}


def _shape_bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def _compare_solid_geometry(before, after):
    """A hash mismatch never authorizes geometry changes, even equal-volume ones."""
    assert before.isValid() and after.isValid()
    topology = _shape_topology(before)
    assert topology == _shape_topology(after) and topology['Solids'] == 1
    bbox_delta = max(abs(a-b) for a, b in zip(_shape_bounds(before), _shape_bounds(after)))
    volume_delta = after.Volume-before.Volume
    area_delta = after.Area-before.Area
    lost, added = before.cut(after).Volume, after.cut(before).Volume
    assert bbox_delta < 1e-6, ('Saved placement or envelope changed', bbox_delta)
    assert abs(volume_delta) < 1e-4 and abs(area_delta) < 1e-4
    assert abs(lost) < 1e-4 and abs(added) < 1e-4, ('Saved shape changed', lost, added)
    return {'valid_single_solids': True, 'topology_before_and_after': topology,
            'before_volume_mm3': before.Volume, 'after_volume_mm3': after.Volume,
            'volume_difference_mm3': volume_delta, 'area_difference_mm2': area_delta,
            'before_minus_after_volume_mm3': lost, 'after_minus_before_volume_mm3': added,
            'maximum_bbox_coordinate_difference_mm': bbox_delta,
            'before_bbox_mm': _shape_bounds(before), 'after_bbox_mm': _shape_bounds(after)}


def _translate_to_bbox_origin(shape):
    result = shape.copy()
    b = result.BoundBox
    result.translate(V(-b.XMin, -b.YMin, -b.ZMin))
    return result


def _geometry_recheck_worker(input_path, output_path):
    """Read both serialized documents in a separate headless process; never save."""
    assert App is not None and not App.GuiUp
    inputs = json.loads(Path(input_path).read_text(encoding='utf-8'))
    source_path = Path(inputs['source_step'])
    assert digest(source_path) == inputs['source_sha256']
    source = Part.read(str(source_path))
    full = print_orientation(source, 180)
    crop = Part.makeBox(24, 17, 29, V(source.BoundBox.XLength/2-12, 10, 0))
    coupon = print_orientation(source.common(crop).removeSplitter(), 90)
    previous = App.openDocument(inputs['previous_FCStd'])
    current = App.openDocument(inputs['current_FCStd'])
    try:
        names = {'FullMountMock', 'SeatFitCoupon'}
        assert {obj.Name for obj in previous.Objects} == names
        assert {obj.Name for obj in current.Objects} == names
        cases = {}
        for name, expected in [('FullMountMock', full), ('SeatFitCoupon', coupon)]:
            old, new = previous.getObject(name), current.getObject(name)
            assert old.SourceSHA256 == new.SourceSHA256 == inputs['source_sha256']
            cases[name] = {
                'previous_saved_vs_GUI_saved': _compare_solid_geometry(old.Shape, new.Shape),
                'source_STEP_vs_GUI_saved_after_translation_only': _compare_solid_geometry(
                    _translate_to_bbox_origin(expected), _translate_to_bbox_origin(new.Shape))}
        result = {'passed': True, 'method': 'headless readback, topology, volume, area, bounds and both-direction Boolean differences',
                  'source_sha256': inputs['source_sha256'],
                  'volume_tolerance_mm3': 1e-4, 'area_tolerance_mm2': 1e-4,
                  'coordinate_tolerance_mm': 1e-6,
                  'placement_scope': 'Saved-before vs saved-after includes display placement. STEP comparison translates each solid to its own bbox origin and does not rotate it.',
                  'objects': cases}
    finally:
        App.closeDocument(previous.Name)
        App.closeDocument(current.Name)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def _serialization_differences(previous_path, current_path):
    result = {}
    with zipfile.ZipFile(previous_path) as old, zipfile.ZipFile(current_path) as new:
        for name in (n for n in old.namelist() if n.endswith('.brp')):
            a, b = old.read(name), new.read(name)
            if a == b:
                continue
            try:
                lines_a, lines_b = a.decode('utf-8').splitlines(), b.decode('utf-8').splitlines()
                tokens_a, tokens_b = a.decode('utf-8').split(), b.decode('utf-8').split()
                changed = [(x, y) for x, y in zip(tokens_a, tokens_b) if x != y]
                numeric = len(tokens_a) == len(tokens_b)
                deltas = []
                for x, y in changed:
                    try:
                        deltas.append(abs(float(x)-float(y)))
                    except ValueError:
                        numeric = False
                result[name] = {'byte_lengths': [len(a), len(b)],
                                'line_counts': [len(lines_a), len(lines_b)],
                                'changed_lines': sum(x != y for x, y in zip(lines_a, lines_b)),
                                'changed_tokens': len(changed),
                                'all_changed_tokens_numeric': numeric,
                                'maximum_numeric_token_delta': max(deltas, default=0)}
            except UnicodeDecodeError:
                result[name] = {'byte_lengths': [len(a), len(b)], 'text_comparison_available': False}
    return result


def recheck_changed_brep(report, current_path):
    """Find the previously validated FCStd, then require a headless shape proof."""
    expected_hash = report['preview_document']['sha256']
    current_hash = digest(current_path)
    exe = shutil.which('freecadcmd')
    assert exe, 'FreeCADCmd is required to validate changed BRep serialization.'
    with tempfile.TemporaryDirectory(prefix='amr06-mock-geometry-recheck-') as folder:
        folder = Path(folder)
        old_path, new_path = folder/'previous.FCStd', folder/'current.FCStd'
        baseline_origin = None
        if (OUT / ZIP_NAME).exists():
            with zipfile.ZipFile(OUT / ZIP_NAME) as archive:
                old_bytes = archive.read(report['preview_document']['file'])
            if hashlib.sha256(old_bytes).hexdigest() == expected_hash:
                old_path.write_bytes(old_bytes)
                baseline_origin = ZIP_NAME + ':' + report['preview_document']['file']
        if not old_path.exists():
            for backup in OUT.glob(NAME+'*.FCBak'):
                if digest(backup) == expected_hash:
                    old_path.write_bytes(backup.read_bytes())
                    baseline_origin = backup.name
                    break
        assert old_path.exists(), 'Previously validated FCStd is unavailable; do not accept new hashes without a geometry recheck.'
        assert fcstd_brep_hashes(old_path) == report['preview_document']['BRep_sha256']
        new_path.write_bytes(current_path.read_bytes())
        assert digest(new_path) == current_hash
        inputs = {'previous_FCStd': str(old_path), 'current_FCStd': str(new_path),
                  'source_step': str((OUT / report['source_step']).resolve()),
                  'source_sha256': report['source_sha256']}
        input_path, output_path = folder/'input.json', folder/'result.json'
        input_path.write_text(json.dumps(inputs), encoding='utf-8')
        code = (f'import sys;sys.path.insert(0,{str(HERE)!r});import build_print_mock as m;'
                f'm._geometry_recheck_worker({str(input_path)!r},{str(output_path)!r})')
        proc = subprocess.run([exe, '-c', code], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                              capture_output=True, text=True, timeout=45)
        assert proc.returncode == 0 and output_path.is_file(), proc.stdout+proc.stderr
        result = json.loads(output_path.read_text(encoding='utf-8'))
        assert result['passed'] and digest(current_path) == current_hash
        result.update(previous_FCStd_sha256=expected_hash, current_FCStd_sha256=current_hash,
                      previous_FCStd_reference=baseline_origin,
                      serialized_BRep_differences=_serialization_differences(old_path, new_path))
        return result


def refresh_bundle_after_gui():
    """After GUI save and capture: verify, rehash and re-ZIP; never remesh.

    Can run in system Python. Both objects must be saved visible; both PNGs
    must be newer than this mock build. STL is immutable. Changed BRep bytes
    require a verified previous FCStd and an independent headless geometry check.
    """
    report = json.loads((OUT / 'validation_results.json').read_text(encoding='utf-8'))
    verify_unchanged_inputs(report)
    preview = report['preview_document']
    path = OUT / preview['file']
    current_brep_hashes = fcstd_brep_hashes(path)
    byte_identical = current_brep_hashes == preview['BRep_sha256']
    if not byte_identical:
        review = recheck_changed_brep(report, path)
        preview.setdefault('BRep_sha256_at_generation', dict(preview['BRep_sha256']))
        preview['BRep_sha256'] = current_brep_hashes
        report.setdefault('GUI_save_geometry_checks', []).append(review)
    assert_saved_visible(path)
    evidence = []
    for filename in ('viewport-mock.png', 'cad-screen-mock.png'):
        image_path = OUT / filename
        assert image_path.stat().st_mtime >= report['build_started_unix_s'] - 1, ('Old preview', filename)
        assert image_path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), filename
        evidence.append({'file': filename, 'sha256': digest(image_path)})
    preview.update(sha256=digest(path), saved_without_GUI=False,
                   saved_GUI_visibility_verified=True,
                   GUI_preview_captured_in_this_run=True,
                   GUI_preview_verified=True,
                   GUI_finalization_kept_BRep_unchanged=byte_identical,
                   GUI_finalization_kept_geometry_unchanged=True,
                   requires_GUI_visibility_finalize=False)
    report['GUI_evidence'] = evidence
    report['GUI_finalized_unix_s'] = time.time()
    write_bundle(report)
    return report


def finalize_gui_preview(doc=None):
    """GUI helper: show the saved mock, save/capture, then refresh the ZIP.

    Refuses an open stale candidate document. Existing STL files are untouched.
    """
    assert App is not None and App.GuiUp, 'Run this helper inside the FreeCAD GUI.'
    import FreeCADGui as Gui
    from PySide import QtWidgets
    report = json.loads((OUT / 'validation_results.json').read_text(encoding='utf-8'))
    verify_unchanged_inputs(report)
    path = OUT / report['preview_document']['file']
    if doc is None:
        doc = App.getDocument(NAME) if NAME in App.listDocuments() else App.openDocument(str(path))
    assert Path(doc.FileName).resolve() == path.resolve()
    expected = {'FullMountMock': report['files'][0], 'SeatFitCoupon': report['files'][1]}
    for name, record in expected.items():
        obj = doc.getObject(name)
        assert obj is not None and obj.SourceSHA256 == report['source_sha256'], 'Close the old mock document and open the current FCStd.'
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
        assert_dimensions(obj.Shape, record['dimensions_mm'], 1e-4)
        assert math.isclose(obj.Shape.Volume, record['CAD_volume_mm3'], abs_tol=1e-5, rel_tol=0)
        obj.ViewObject.Visibility = True
        obj.ViewObject.ShapeColor = (0.92, 0.55, 0.18) if name == 'FullMountMock' else (0.18, 0.65, 0.74)
        obj.ViewObject.LineColor = (0.15, 0.15, 0.15)
        obj.ViewObject.DisplayMode = 'Flat Lines'
    doc.recompute()
    App.setActiveDocument(doc.Name)
    Gui.activateWorkbench('PartWorkbench')
    Gui.Selection.clearSelection()
    view = Gui.activeDocument().activeView()
    view.viewAxonometric()
    view.fitAll()
    Gui.updateGui()
    QtWidgets.QApplication.processEvents()
    doc.save()
    view.saveImage(str(OUT / 'viewport-mock.png'), 1500, 1000, 'White')
    assert Gui.getMainWindow().grab().save(str(OUT / 'cad-screen-mock.png'))
    return refresh_bundle_after_gui()


def bbox(shape):
    box = shape.BoundBox
    return [box.XLength, box.YLength, box.ZLength]


def assert_dimensions(shape, expected, tolerance=1e-6):
    actual = bbox(shape)
    assert all(math.isclose(a, b, abs_tol=tolerance, rel_tol=0)
               for a, b in zip(actual, expected)), (actual, expected)


def print_orientation(shape, rotation_degrees):
    result = shape.copy()
    result.rotate(V(0, 0, 0), V(1, 0, 0), rotation_degrees)
    box = result.BoundBox
    result.translate(V(-box.XMin, -box.YMin, -box.ZMin))
    return result


def export_and_check(shape, filename, expected_dimensions):
    assert shape.isValid() and len(shape.Solids) == 1
    assert_dimensions(shape, expected_dimensions)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02,
                                 AngularDeflection=0.08, Relative=False)
    mesh.write(str(OUT / filename))
    # Check the serialized STL, not only the CAD solid or in-memory mesh.
    restored = Mesh.Mesh(str(OUT / filename))
    assert restored.isSolid()
    assert restored.countComponents() == 1
    assert not restored.hasNonManifolds()
    assert not restored.hasSelfIntersections()
    assert restored.Volume > 0
    error = abs(restored.Volume - shape.Volume) / shape.Volume
    assert error < 0.001
    assert_dimensions(restored, expected_dimensions, 1e-4)
    assert abs(restored.BoundBox.ZMin) < 1e-5
    return {
        'file': filename, 'units': 'mm', 'scale': 1.0,
        'dimensions_mm': bbox(restored), 'bed_z_min_mm': restored.BoundBox.ZMin,
        'CAD_volume_mm3': shape.Volume, 'STL_volume_mm3': restored.Volume,
        'relative_volume_error': error, 'triangles': restored.CountFacets,
        'closed_solid': True, 'connected_components': 1,
        'non_manifold_edges': False, 'self_intersections': False,
        'within_P1S_nominal_256mm_cube': all(n < 256 for n in expected_dimensions),
        'sha256': digest(OUT / filename),
    }


def compare_coupon(coupon_source, crop, center_x):
    result = {'reference_step': os.path.relpath(BASELINE, OUT),
              'checked': False, 'unchanged_from_A4': None}
    if not BASELINE.exists():
        result['note'] = 'A4 reference absent; coupon is still the exact A5 crop.'
        return result
    baseline_hash = digest(BASELINE)
    baseline = Part.read(str(BASELINE))
    baseline.translate(V(center_x-45, 0, 0))
    baseline_coupon = baseline.common(crop).removeSplitter()
    assert baseline_coupon.isValid() and len(baseline_coupon.Solids) == 1
    added = coupon_source.cut(baseline_coupon).Volume
    removed = baseline_coupon.cut(coupon_source).Volume
    # R2 candidates enlarge six seat relief arcs and may add web/flange roots.
    # The relief cuts belong in the fit coupon; the added roots lie outside it.
    assert added < 1e-5, ('Root addition unexpectedly enters the coupon', added)
    assert removed > 0
    back = Part.makeBox(24, 8, 29, V(center_x-12, 10, 0))
    current_back = coupon_source.common(back)
    baseline_back = baseline_coupon.common(back)
    back_difference = (current_back.cut(baseline_back).Volume
                       + baseline_back.cut(current_back).Volume)
    assert back_difference < 1e-5
    holes = []
    reliefs = []
    for face in coupon_source.Faces:
        cylinder = face.Surface
        if not isinstance(cylinder, Part.Cylinder) or abs(abs(cylinder.Axis.y)-1) > 1e-6:
            continue
        if abs(cylinder.Radius-1.4) < 1e-6:
            holes.append([cylinder.Center.x, cylinder.Center.z, face.BoundBox.YLength])
        if abs(cylinder.Radius-2.0) < 1e-6:
            reliefs.append(face.BoundBox.YLength)
    expected_holes = [[center_x-6.5817930687617, 11.55, 8], [center_x, 22.95, 8],
                      [center_x+6.5817930687617, 11.55, 8]]
    holes.sort()
    assert len(holes) == 3
    assert all(abs(a-b) < 1e-6 for actual, expected in zip(holes, expected_holes)
               for a, b in zip(actual, expected)), holes
    assert len(reliefs) == 6 and all(abs(depth-9) < 1e-6 for depth in reliefs)
    assert baseline_hash == digest(BASELINE)
    result.update(checked=True, unchanged_from_A4=False,
                  reference_sha256=baseline_hash,
                  baseline_alignment_translation_mm=[center_x-45, 0, 0],
                  added_to_A4_coupon_mm3=added, removed_from_A4_coupon_mm3=removed,
                  symmetric_difference_volume_mm3=added+removed,
                  rear_wall_difference_mm3=back_difference,
                  retained_motor_holes_x_z_length_mm=holes,
                  seat_relief_count=6, seat_relief_radius_mm=2.0,
                  seat_relief_depths_mm=reliefs,
                  note='Seat R2 relief cuts are retained; added web/flange R2 roots lie outside the coupon.')
    return result


def save_preview_document(full, coupon, selection, source_hash):
    if NAME in App.listDocuments():
        raise RuntimeError('A5 mock document is already open; preserve its edits before regenerating.')
    doc = App.newDocument(NAME)
    dimensions = bbox(full)
    size_label = ' x '.join(f'{v:g}' for v in dimensions)
    for name, label, shape, color, offset in [
        ('FullMountMock', f'A5 PLA mock | {selection["candidate"]} | {size_label}', full, (0.92, 0.55, 0.18), 0),
        ('SeatFitCoupon', 'A5 PLA fit coupon | seat UP | 24 x 29 x 17', coupon, (0.18, 0.65, 0.74), dimensions[0]+18),
    ]:
        obj = doc.addObject('PartDesign::Feature', name)
        obj.Label = label
        obj.Shape = shape
        obj.Placement.Base = V(offset, 0, 0)
        obj.addProperty('App::PropertyString', 'Purpose').Purpose = 'FIT MOCK ONLY: no load testing or driving'
        obj.addProperty('App::PropertyString', 'SourceSTEP').SourceSTEP = os.path.relpath(selection['source'], OUT)
        obj.addProperty('App::PropertyString', 'SourceSHA256').SourceSHA256 = source_hash
        obj.addProperty('App::PropertyString', 'Candidate').Candidate = selection['candidate']
        if App.GuiUp:
            obj.ViewObject.Visibility = True
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = (0.15, 0.15, 0.15)
            obj.ViewObject.DisplayMode = 'Flat Lines'
    doc.recompute()
    path = OUT / (NAME + '.FCStd')
    doc.saveAs(str(path))
    if App.GuiUp:
        readback_checked = False
    else:
        # A true headless App document; no GUI or saved screenshot is required.
        App.closeDocument(doc.Name)
        restored = App.openDocument(str(path))
        assert len(restored.Objects) == 2
        for obj_name, expected_shape in [('FullMountMock', full), ('SeatFitCoupon', coupon)]:
            obj = restored.getObject(obj_name)
            assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
            assert math.isclose(obj.Shape.Volume, expected_shape.Volume, abs_tol=1e-5, rel_tol=0)
            assert_dimensions(obj.Shape, bbox(expected_shape))
        App.closeDocument(restored.Name)
        readback_checked = True
    return {'file': path.name, 'sha256': digest(path),
            'BRep_sha256': fcstd_brep_hashes(path),
            'initial_creation_without_GUI': not bool(App.GuiUp),
            'saved_without_GUI': not bool(App.GuiUp),
            'serialized_FCStd_readback_checked': readback_checked,
            'saved_GUI_visibility_verified': False,
            'GUI_preview_captured_in_this_run': False,
            'GUI_preview_verified': False,
            'requires_GUI_visibility_finalize': True}


def frame_interface(source):
    holes = []
    for face in source.Faces:
        cylinder = face.Surface
        if (isinstance(cylinder, Part.Cylinder) and abs(cylinder.Radius-3.3) < 1e-6
                and abs(abs(cylinder.Axis.z)-1) < 1e-6):
            holes.append([cylinder.Center.x, cylinder.Center.y, face.BoundBox.ZLength])
    holes.sort()
    assert len(holes) == 2 and abs(holes[0][2]-holes[1][2]) < 1e-6
    return {'frame_holes_x_y_material_length_mm': holes,
            'frame_hole_pitch_mm': holes[1][0]-holes[0][0],
            'flange_thickness_mm': holes[0][2]}


def update_guide(selection, dimensions, interface):
    path = OUT / 'PRINT_GUIDE.ja.md'
    text = path.read_text(encoding='utf-8')
    start, end = '<!-- selected-mock:start -->', '<!-- selected-mock:end -->'
    assert text.count(start) == 1 and text.count(end) == 1
    record = (f'選択候補：**{selection["candidate"]}**。元STEP：`{os.path.relpath(selection["source"], OUT)}`。\n\n'
              f'本体外形：**{"×".join(f"{v:g}" for v in dimensions)} mm**。'
              f'フランジ厚：**{interface["flange_thickness_mm"]:g} mm**。'
              f'M6穴ピッチ：**{interface["frame_hole_pitch_mm"]:g} mm**。'
              '寸法は選択STEPの形状から取得。確認片は24×29×17 mm。')
    before = text.split(start, 1)[0]
    after = text.split(end, 1)[1]
    path.write_text(before + start + '\n' + record + '\n' + end + after, encoding='utf-8')


def main(selection_path=None):
    if App is None:
        raise RuntimeError('Generate meshes with FreeCADCmd; only refresh_bundle_after_gui is available in system Python.')
    started = time.time()
    selection = read_selection(selection_path)
    source_path = selection['source']
    if not (OUT / 'PRINT_GUIDE.ja.md').is_file():
        raise FileNotFoundError('PRINT_GUIDE.ja.md is required in the printable bundle.')
    OUT.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source_path)
    source = Part.read(str(source_path))
    assert source.isValid() and len(source.Solids) == 1
    width = source.BoundBox.XLength
    assert width >= 24
    dimensions = [width, 30, 34]
    assert_dimensions(source, dimensions)
    assert all(abs(x) < 1e-6 for x in [source.BoundBox.XMin, source.BoundBox.YMin, source.BoundBox.ZMin])

    # Frame contact face local z=34 goes onto the print bed.
    full = print_orientation(source, 180)
    reversed_full = full.copy()
    reversed_full.translate(V(0, -30, -34))
    reversed_full.rotate(V(0, 0, 0), V(1, 0, 0), -180)
    common_volume = source.common(reversed_full).Volume
    assert abs(common_volume - source.Volume) < 1e-4

    # Retain the complete seat/holes/throat, depth 9 and rear wall 8. No flange.
    center_x = width/2
    crop_origin = [center_x-12, 10, 0]
    crop = Part.makeBox(24, 17, 29, V(*crop_origin))
    coupon_source = source.common(crop).removeSplitter()
    assert coupon_source.isValid() and len(coupon_source.Solids) == 1
    assert_dimensions(coupon_source, [24, 17, 29])
    comparison = compare_coupon(coupon_source, crop, center_x)
    # Motor-seat opening y=27 faces +print Z; rear face y=10 sits on the bed.
    coupon = print_orientation(coupon_source, 90)
    results = [export_and_check(full, FULL_STL, dimensions),
               export_and_check(coupon, COUPON_STL, [24, 29, 17])]
    document = save_preview_document(full, coupon, selection, source_hash)
    interface = frame_interface(source)
    update_guide(selection, dimensions, interface)
    assert source_hash == digest(source_path)
    report = {
        'design': 'A5', 'candidate': selection['candidate'],
        'candidate_step_stem': source_path.stem,
        'selection_file': os.path.relpath(selection['selection_path'], OUT),
        'selection_sha256': selection['selection_sha256'],
        'selection_sha256_at_generation': selection['selection_sha256'],
        'build_started_unix_s': started,
        'purpose': 'PLA hand-fit geometry mock only; no load test or loaded driving',
        'source_step': os.path.relpath(source_path, OUT), 'source_sha256': source_hash,
        'source_dimensions_mm': bbox(source), 'source_valid_solid_count': 1,
        'nominal_full_mount_matches_candidate_STEP': True,
        'inverse_transform_common_volume_mm3': common_volume,
        'no_fit_compensation_added': True,
        'coupon_source_box_origin_mm': crop_origin,
        'coupon_source_box_size_mm': [24, 17, 29],
        'coupon_pocket_depth_mm': 9, 'coupon_rear_wall_mm': 8,
        'coupon_pocket_opening_direction': '+print Z',
        'coupon_comparison_to_A4': comparison,
        'frame_interface': interface,
        'coupon_volume_fraction_of_full_solid': coupon.Volume / source.Volume,
        'mesh_linear_deflection_mm': 0.02, 'mesh_angular_deflection_rad': 0.08,
        'files': results, 'preview_document': document, 'GUI_evidence': [],
        'sliced': False, 'physical_print_tested': False, 'load_testing_permitted': False,
        'print_duration_filament_mass_and_cost': None,
        'note': 'Import unitless STL as mm at 100%. FDM fit cannot certify metal +/-0.05mm tolerances, motor revision, load capacity or SF2.',
    }
    write_bundle(report)
    if App.GuiUp:
        report = finalize_gui_preview(App.getDocument(NAME))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__' or any(
        arg.endswith('.py') and Path(arg).resolve() == Path(__file__).resolve()
        for arg in sys.argv[1:]):
    # FreeCADCmd imports a positional .py under its stem, not '__main__'.
    main()

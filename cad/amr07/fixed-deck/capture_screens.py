"""Real FreeCAD GUI screenshots. Configure and capture in separate RPC calls."""
from pathlib import Path
import json
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

HERE = Path(__file__).resolve().parent
NAME = 'AMR01_FixedDeck_D69'
doc = App.listDocuments().get(NAME) or App.openDocument(str(HERE / (NAME+'.FCStd')))
App.setActiveDocument(doc.Name)
Gui.activateWorkbench('PartWorkbench')
Gui.Selection.clearSelection()
w = Gui.getMainWindow()
w.resize(1600, 1050)
for dock in w.findChildren(QtWidgets.QDockWidget):
    dock.hide()
view = Gui.activeDocument().activeView()
view.setCameraType('Orthographic')
g = json.loads((HERE / 'geometry.json').read_text())
objects = [o for o in doc.Objects if hasattr(o, 'MaterialBasis')]
original = {o.Name: App.Placement(o.Placement) for o in objects}
statuses = {
    'overall': 'D6.9 FIXED DECK | 6 x M6x12: 3 PER SIDE | NO HINGES OR ADAPTERS | 300 x 300 x 4 mm',
    'top': 'D6.9 TOP | 6 ORANGE M6 FIXINGS | 36 GRID HOLES | head height 6 mm; cargo seat inside fixing rows',
    'fixings': 'D6.9 SUPPORT | 3 M6x12 + HNTT6-6 PER RAIL | deck transparent for fastener visibility | NO SPACERS',
    'battery-service': 'D6.9 BATTERY SERVICE | DECK REMAINS FIXED | disconnect / release belt / lift 8 mm / withdraw rearward 220 mm',
    'deck-removal': 'D6.9 MAINTENANCE | unload / power off / remove 6 bolts / lift deck 120 mm | exploded service position',
}


def normal():
    for o in objects:
        o.Placement = original[o.Name]
        o.ViewObject.Visibility = o.MaterialBasis != 'reference' or o.Name.startswith(('Battery', 'Reserved_', 'Computer', 'Supervisor', 'EStop_X', 'ARM_', 'MainPower_'))
        o.ViewObject.Transparency = 0
        o.ViewObject.DisplayMode = 'Flat Lines'
        o.ViewObject.LineColor = (.12, .14, .16)
        color = {'aluminum': (.74, .78, .82), 'steel': (.43, .47, .51), 'PLA': (.23, .55, .59), 'rubber': (.16, .17, .19)}.get(o.MaterialBasis, (.28, .40, .52))
        if o.Name.startswith('RearStop') and o.MaterialBasis == 'PLA': color = (.97, .77, .10)
        if o.Name.startswith('RearPower') and o.MaterialBasis == 'PLA': color = (.23, .29, .34)
        if o.Name.startswith('DeckBolt'): color = (.95, .47, .06)
        if o.Name == 'EStop_XA1E_BV302R': color = (.91, .07, .06)
        if o.Name.startswith(('ARM_', 'MainPower_')): color = (.10, .11, .12)
        if o.Name.startswith('Reserved_'): o.ViewObject.Transparency = 20
        if o.Name == 'BatteryBL1860B': color = (.12, .16, .17)
        if o.Name == 'BatteryAdapter03': color = (.04, .55, .58)
        if o.Name == 'ComputerBarrierPLA': color = (.94, .85, .61)
        if 'Belt' in o.Name or 'Buckle' in o.Name: color = (.84, .41, .12)
        o.ViewObject.ShapeColor = color
        o.ViewObject.DiffuseColor = [color]
    doc.getObject('CargoEnvelopeD3').ViewObject.Visibility = False


def rear_view():
    z = App.Vector(-1.4, -1, 1.1); z.normalize()
    x = App.Vector(0, 0, 1).cross(z); x.normalize(); y = z.cross(x)
    view.setCameraOrientation(App.Rotation(x, y, z, 'ZXY').Q)


def configure(kind):
    normal()
    if kind == 'top':
        view.viewTop()
    elif kind == 'fixings':
        for o in objects:
            o.ViewObject.Visibility = o.Name.startswith(('AluminumDeck', 'UpperRail3030', 'DeckBolt', 'DeckSlotNut'))
        doc.getObject('AluminumDeckD3').ViewObject.Transparency = 75
        for o in objects:
            if o.Name.startswith('UpperRail3030'): o.ViewObject.Transparency = 40
        rear_view()
    elif kind == 'battery-service':
        prior = json.loads((HERE.parent / 'two-story/validation.json').read_text())
        for name in prior['moving_parts']:
            p = App.Placement(original[name]); p.Base += App.Vector(-220, 0, 8)
            doc.getObject(name).Placement = p
        for name in prior['released_before_service']:
            doc.getObject(name).ViewObject.Visibility = False
        rear_view()
    elif kind == 'deck-removal':
        for name in g['moving_deck_parts']:
            p = App.Placement(original[name]); p.Base += App.Vector(0, 0, 120)
            doc.getObject(name).Placement = p
        for name in g['released_before_deck_removal']:
            doc.getObject(name).ViewObject.Visibility = False
        rear_view()
    else:
        rear_view()
    view.fitAll()
    w.statusBar().showMessage(statuses[kind], 0)
    doc.recompute(); view.redraw(); Gui.updateGui()


def capture(kind):
    w.statusBar().showMessage(statuses[kind], 0)
    QtWidgets.QApplication.processEvents()
    assert w.grab().save(str(HERE / ('cad-screen-'+kind+'.png')))


def save_normal():
    configure('overall')
    doc.recompute(); doc.save()


if __name__ == '__main__':
    configure('overall')

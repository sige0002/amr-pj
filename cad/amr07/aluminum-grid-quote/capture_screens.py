"""Run in FreeCAD GUI after building; keep STEP/PDF quote files unchanged."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

ROOT = Path(__file__).resolve().parent
for tag in ('T4', 'C45'):
    name = 'AMR_GridDeck_' + tag + '_Q1'
    doc = App.getDocument(name) if name in App.listDocuments() else App.openDocument(str(ROOT / (name + '.FCStd')))
    App.setActiveDocument(doc.Name)
    obj = doc.GridDeck
    obj.ViewObject.Visibility = True
    obj.ViewObject.ShapeColor = (.75, .78, .82)
    obj.ViewObject.LineColor = (.15, .18, .23)
    obj.ViewObject.DisplayMode = 'Flat Lines'
    doc.recompute()
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    doc.save()
Gui.Selection.clearSelection()
Gui.updateGui()


def capture_grid_quote_screen():
    view = Gui.activeDocument().activeView()
    view.fitAll()
    view.saveImage(str(ROOT / 'viewport-isometric.png'), 1600, 1200, 'White')
    Gui.getMainWindow().grab().save(str(ROOT / 'cad-screen-isometric.png'))
    print('Saved visible quotation plate and FreeCAD screen.')


QtCore.QTimer.singleShot(1000, capture_grid_quote_screen)

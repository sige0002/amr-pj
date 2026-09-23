"""Compose actual, constant-camera FreeCAD captures made by capture_screens.py."""
from pathlib import Path
import argparse
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--frames',type=Path,default=Path('/tmp/amr-hatch-cad-frames'))
args = parser.parse_args()
here = Path(__file__).resolve().parent
frames = [Image.open(args.frames/f'{i:02d}.png').convert('RGB') for i in range(10)]
# Preserve the complete GUI window; resize uniformly for a practical repository GIF.
frames = [im.resize((1120,770),Image.Resampling.LANCZOS) for im in frames]
sequence = frames + frames[-2:0:-1]
durations = [1400]+[180]*8+[1800]+[180]*8
sequence[0].save(here/'cad-opening.gif',save_all=True,append_images=sequence[1:],
                 duration=durations,loop=0,optimize=True,disposal=2)
print('Saved actual FreeCAD opening GIF; CAD motion only, not a physics test.')

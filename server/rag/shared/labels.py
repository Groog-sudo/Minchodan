# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KICKBOARD = "kickboard"
BOLLARD = "bollard"
BRAILLE_DAMAGED = "braille_damaged"
STAIRS = "stairs"
CROSSWALK = "crosswalk"
MANHOLE = "manhole"
GRATING = "grating"

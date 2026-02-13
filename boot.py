import sys
import hardware_setup
import gc
from gui.core.ugui import Screen, quiet
from badge.games.cyberslayer import SlayerIntro

quiet()
gc.collect()
Screen.change(SlayerIntro)

# Prevent frozen main.py from running
sys.modules["main"] = type(sys)("main")
sys.modules["__main__"] = sys.modules["main"]

import hardware_setup  # ALWAYS FIRST
import gc
from gui.core.ugui import Screen, quiet
from badge.games.cyberslayer import SlayerIntro

quiet()
gc.collect()
Screen.change(SlayerIntro)
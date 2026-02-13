import hardware_setup as hardware_setup  # ALWAYS FIRST

import asyncio
import json
import os
import gc
import random
from machine import Pin
from neopixel import NeoPixel
from micropython import const
from hardware_setup import LED_PIN, LED_ACTIVATE_PIN

from gui.core.ugui import Screen, ssd
from gui.widgets import Label, Button
from gui.core.writer import CWriter
from gui.fonts import arial35, font10
import gui.fonts.arial10 as arial10
from gui.core.colors import WHITE, BLACK, GREEN, RED, D_GREEN, D_PINK


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

SAVE_FILE = "cyberslayer.json"
NUM_LEVELS = const(10)
PLAYER_START_HP = const(100)
NMAP_START = const(6)
META_START = const(2)

DMG_PING = const(8)
DMG_NMAP = const(15)
DMG_META = const(30)


# ---------------------------------------------------------
# LEVEL DATA
# ---------------------------------------------------------

WEAK_HINTS = {
    "ping": "Trace the network!",
    "nmap": "Scan its ports!",
    "meta": "Exploit it!",
}

LEVELS = (
    {"name": "Guest WiFi", "enemy": "Script Kiddie", "hp": 12, "atk": 3, "special": None, "weak": "ping"},
    {"name": "DMZ", "enemy": "Trojan", "hp": 20, "atk": 5, "special": None, "weak": "nmap"},
    {"name": "Web Server", "enemy": "Worm", "hp": 25, "atk": 4, "special": "replicate", "weak": "ping"},
    {"name": "Email GW", "enemy": "Phisher", "hp": 22, "atk": 6, "special": None, "weak": "nmap"},
    {"name": "File Server", "enemy": "Ransomware", "hp": 35, "atk": 7, "special": "encrypt", "weak": "meta"},
    {"name": "Active Dir", "enemy": "Rootkit", "hp": 38, "atk": 5, "special": None, "weak": "meta"},
    {"name": "Database", "enemy": "SQLi Worm", "hp": 32, "atk": 6, "special": "replicate", "weak": "nmap"},
    {"name": "SCADA", "enemy": "Zero-Day", "hp": 35, "atk": 7, "special": None, "weak": "meta"},
    {"name": "C-Suite", "enemy": "Social Eng", "hp": 28, "atk": 8, "special": "encrypt", "weak": "ping"},
    {"name": "Core Router", "enemy": "APT", "hp": 55, "atk": 8, "special": "adapt", "weak": "meta"},
)

VICTORY_QUOTES = (
    "The network bows to you.",
    "All your base are belong to us.",
    "root@victory:~# cat flag.txt",
    "Hack the planet!",
    "Access granted. Welcome home.",
    "You are the firewall now.",
    "Zero threats remaining. GG.",
    "They never stood a chance.",
    "Breached, cleared, secured.",
    "sudo rm -rf /threats/*",
)

DEFEAT_QUOTES = (
    "Segfault in your defenses.",
    "Connection terminated by host.",
    "Try harder.",
    "The firewall won this round.",
    "You got 0wn3d.",
    "Kernel panic - not syncing.",
    "rm -rf /your/hopes",
    "418 I'm a teapot. You're toast.",
    "Have you tried turning it off?",
    "Skill issue detected.",
)

RANKS = (
    (0, "Script Kiddie"),
    (2, "Packet Pusher"),
    (4, "Shell Jockey"),
    (6, "Root Rider"),
    (8, "Zero-Day Hunter"),
    (10, "Digital Oracle"),
)


def get_rank(level):
    rank = RANKS[0][1]
    for threshold, name in RANKS:
        if level >= threshold:
            rank = name
    return rank


# ---------------------------------------------------------
# SAVE / LOAD
# ---------------------------------------------------------

def load_save():
    try:
        if SAVE_FILE in os.listdir():
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"high_level": 0, "kills": 0, "games": 0}


def write_save(data):
    try:
        tmp = "cyberslayer.tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.rename(tmp, SAVE_FILE)
    except Exception:
        pass


# ---------------------------------------------------------
# LED HELPERS
# ---------------------------------------------------------

def turn_off_leds(np, led_power):
    if np:
        try:
            for i in range(len(np)):
                np[i] = (0, 0, 0)
            np.write()
        except Exception:
            pass
    if led_power:
        try:
            led_power.value(0)
        except Exception:
            pass


# ---------------------------------------------------------
# INTRO SCREEN
# ---------------------------------------------------------

class SlayerIntro(Screen):
    def __init__(self):
        super().__init__()

        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wri_big = CWriter(ssd, arial35, D_PINK, BLACK, verbose=False)

        Label(wri, 5, 2, 316,
              justify=Label.CENTRE, fgcolor=D_GREEN
              ).value("[ C Y B E R S L A Y E R ]")

        Label(wri_big, 30, 2, 316,
              justify=Label.CENTRE).value("SLAY")

        save = load_save()
        high = save.get("high_level", 0)
        kills = save.get("kills", 0)
        games = save.get("games", 0)
        rank = get_rank(high)

        Label(wri, 75, 2, 316,
              justify=Label.CENTRE, fgcolor=D_GREEN
              ).value(f"Rank: {rank}")

        Label(wri, 95, 2, 316,
              justify=Label.CENTRE, fgcolor=D_GREEN
              ).value(f"Best: Lv{high} | Kills: {kills} | Runs: {games}")

        Button(
            wri, 130, 100, width=120, height=26,
            text="Breach In",
            fgcolor=D_GREEN, textcolor=D_GREEN,
            callback=lambda *_: self.start_game(),
        )

    def start_game(self):
        Screen.change(SlayerBattle, mode=Screen.REPLACE)


# ---------------------------------------------------------
# BATTLE SCREEN
# ---------------------------------------------------------

class SlayerBattle(Screen):
    def __init__(self):
        super().__init__()

        # Player state
        self.level = 0
        self.player_hp = PLAYER_START_HP
        self.nmap_ammo = NMAP_START
        self.meta_ammo = META_START
        self.shield = 0
        self.kills = 0
        self.locked = False

        # Enemy state
        self.enemy_hp = 0
        self.enemy_atk = 0
        self.enemy_special = None
        self.enemy_weak = None
        self.enemy_name = ""
        self.turn_count = 0
        self.last_weapon = None
        self.weapon_encrypted = False

        # LED setup
        self.led_power = LED_ACTIVATE_PIN
        self.led_power.value(1)
        self.np = NeoPixel(LED_PIN, 10)
        for i in range(10):
            self.np[i] = (0, 0, 0)
        self.np.write()

        # UI writers
        self.wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wri_btn = CWriter(ssd, arial10, GREEN, BLACK, verbose=False)

        # Labels
        self.level_label = Label(
            self.wri, 2, 2, 316, justify=Label.CENTRE, fgcolor=D_GREEN
        )
        self.enemy_label = Label(
            self.wri, 20, 2, 316, justify=Label.CENTRE, fgcolor=D_PINK
        )
        self.enemy_hp_label = Label(
            self.wri, 40, 2, 150, fgcolor=RED
        )
        self.player_hp_label = Label(
            self.wri, 40, 170, 146, fgcolor=GREEN
        )
        self.info_label = Label(
            self.wri, 60, 2, 316, justify=Label.CENTRE, fgcolor=WHITE
        )
        self.info2_label = Label(
            self.wri, 80, 2, 316, justify=Label.CENTRE, fgcolor=D_GREEN
        )

        # Weapon buttons (3 buttons = 3 badge buttons)
        Button(
            wri_btn, 110, 5, width=95, height=30,
            text="Ping",
            fgcolor=GREEN, textcolor=WHITE,
            callback=lambda *_: self.attack("ping"),
        )
        Button(
            wri_btn, 110, 110, width=95, height=30,
            text="Nmap",
            fgcolor=GREEN, textcolor=WHITE,
            callback=lambda *_: self.attack("nmap"),
        )
        Button(
            wri_btn, 110, 215, width=95, height=30,
            text="Msploit",
            fgcolor=GREEN, textcolor=WHITE,
            callback=lambda *_: self.attack("meta"),
        )

        self.spawn_enemy()

    # ---------- ENEMY MANAGEMENT ----------

    def spawn_enemy(self):
        lvl = LEVELS[self.level]
        self.enemy_name = lvl["enemy"]
        self.enemy_hp = lvl["hp"]
        self.enemy_atk = lvl["atk"]
        self.enemy_special = lvl["special"]
        self.enemy_weak = lvl.get("weak")
        self.turn_count = 0
        self.last_weapon = None
        self.weapon_encrypted = False

        self.level_label.value(f"Lv{self.level + 1}: {lvl['name']}")
        self.enemy_label.value(f">> {self.enemy_name} <<")
        self.update_bars()
        hint = WEAK_HINTS.get(self.enemy_weak, "Choose your weapon!")
        self.info_label.value(f"Hint: {hint}")
        self.update_ammo_label()

    def update_bars(self):
        self.enemy_hp_label.value(f"Enemy: {self.enemy_hp}")
        hp_str = f"HP: {self.player_hp}"
        if self.shield > 0:
            hp_str += f" +{self.shield}sh"
        self.player_hp_label.value(hp_str)

    def update_ammo_label(self):
        self.info2_label.value(
            f"Ping:inf  Nmap:{self.nmap_ammo}  Msploit:{self.meta_ammo}"
        )

    # ---------- COMBAT ----------

    def attack(self, weapon):
        if self.locked:
            return
        self.locked = True

        # Check ammo
        if weapon == "nmap" and self.nmap_ammo <= 0:
            self.info_label.value("No Nmap ammo!")
            self.locked = False
            return
        if weapon == "meta" and self.meta_ammo <= 0:
            self.info_label.value("No Metasploit ammo!")
            self.locked = False
            return

        # Calculate damage
        dmg = DMG_PING
        if weapon == "nmap":
            dmg = DMG_NMAP
            self.nmap_ammo -= 1
        elif weapon == "meta":
            dmg = DMG_META
            self.meta_ammo -= 1

        # Weakness bonus (2x damage)
        is_crit = (self.enemy_weak == weapon)
        if is_crit:
            dmg = dmg * 2

        # Ransomware encrypted weapons (halves damage)
        if self.weapon_encrypted:
            dmg = dmg // 2
            self.weapon_encrypted = False

        # APT adapts to repeated weapon
        if self.enemy_special == "adapt" and weapon == self.last_weapon:
            dmg = dmg // 3

        self.last_weapon = weapon
        self.turn_count += 1

        # Apply damage
        self.enemy_hp -= dmg
        if is_crit:
            hit_text = f"CRIT! {dmg} to {self.enemy_name}!"
        else:
            hit_text = f"Hit {self.enemy_name} for {dmg}!"

        if self.enemy_hp <= 0:
            self.enemy_hp = 0
            self.kills += 1
            self.reg_task(self._on_enemy_killed(hit_text), True)
        else:
            self.reg_task(self._on_enemy_turn(hit_text), True)

    async def _on_enemy_turn(self, hit_text):
        self.info_label.value(hit_text)
        self.update_bars()

        await self._flash_led((255, 0, 0), 0.2)
        await asyncio.sleep(0.4)

        # Enemy attacks
        atk = self.enemy_atk

        # Worm replicates every 3 turns
        special_msg = ""
        if self.enemy_special == "replicate" and self.turn_count % 3 == 0:
            atk = int(atk * 1.5)
            special_msg = "Worm replicated! Extra dmg!"

        # Ransomware encrypts weapons every 2 turns
        if self.enemy_special == "encrypt" and self.turn_count % 2 == 0:
            self.weapon_encrypted = True
            special_msg = "Weapons encrypted! Next halved!"

        # Shield absorbs first
        if self.shield > 0:
            absorbed = min(self.shield, atk)
            self.shield -= absorbed
            atk -= absorbed

        self.player_hp -= atk

        if self.player_hp <= 0:
            self.player_hp = 0
            self.update_bars()
            self.info_label.value(f"{self.enemy_name} hits you for {self.enemy_atk}!")
            await asyncio.sleep(0.8)
            self._game_over()
        else:
            self.update_bars()
            self.info_label.value(f"{self.enemy_name} hits for {self.enemy_atk}!")
            if special_msg:
                self.info2_label.value(special_msg)
            else:
                self.update_ammo_label()
            self.locked = False

    async def _on_enemy_killed(self, hit_text):
        self.info_label.value(hit_text)
        self.update_bars()

        zone_name = LEVELS[self.level]["name"]
        self.level += 1

        if self.level >= NUM_LEVELS:
            self.enemy_label.value(">> DEFEATED <<")
            self.info_label.value("ALL THREATS ELIMINATED!")
            await self._celebrate_leds(self.level)
            await asyncio.sleep(0.5)
            self._game_over(victory=True)
        else:
            # Celebrate the cleared level
            self.enemy_label.value(f"** {zone_name} SECURED **")
            self.info_label.value(f"Zone {self.level}/{NUM_LEVELS} cleared!")
            self.info2_label.value(f"{self.enemy_name} destroyed!")
            await self._celebrate_leds(self.level)

            # Show loot and continue
            self._apply_loot()
            self.info_label.value(f"+loot! Next: Lv{self.level + 1}")
            self.update_ammo_label()
            await asyncio.sleep(0.8)
            self.spawn_enemy()
            self.locked = False

    async def _celebrate_leds(self, cleared):
        """LED celebration for clearing a level."""
        try:
            n = min(cleared, 10)
            # Flash cleared LEDs bright green twice
            for _ in range(2):
                for i in range(n):
                    self.np[9 - i] = (0, 255, 0)
                self.np.write()
                await asyncio.sleep(0.15)
                for i in range(n):
                    self.np[9 - i] = (0, 0, 0)
                self.np.write()
                await asyncio.sleep(0.1)

            # Cascade fill from first to latest cleared
            for i in range(n):
                self.np[9 - i] = (0, 200, 0)
                self.np.write()
                await asyncio.sleep(0.08)

            await asyncio.sleep(0.2)

            # Settle to dim green (persistent progress)
            for i in range(n):
                self.np[9 - i] = (0, 40, 0)
            self.np.write()
        except Exception:
            pass

    def _apply_loot(self):
        # Heal between levels
        heal = 15 + self.level * 3
        self.player_hp = min(self.player_hp + heal, PLAYER_START_HP)

        # Nmap resupply every level
        self.nmap_ammo += 2

        # Metasploit at levels 3, 5, 8
        if self.level in (2, 4, 7):
            self.meta_ammo += 1

        # Shield at levels 3, 5, 7, 9
        if self.level in (2, 4, 6, 8):
            self.shield += 10

    # ---------- GAME END ----------

    def _game_over(self, victory=False):
        save = load_save()
        if self.level > save.get("high_level", 0):
            save["high_level"] = self.level
        save["kills"] = save.get("kills", 0) + self.kills
        save["games"] = save.get("games", 0) + 1
        write_save(save)

        Screen.change(
            SlayerEnd,
            mode=Screen.REPLACE,
            kwargs={
                "level": self.level,
                "kills": self.kills,
                "victory": victory,
            },
        )

    # ---------- LED FX ----------

    async def _flash_led(self, color, duration):
        try:
            idx = 9 - self.level
            if 0 <= idx < 10:
                old = self.np[idx]
                self.np[idx] = color
                self.np.write()
                await asyncio.sleep(duration)
                self.np[idx] = old
                self.np.write()
        except Exception:
            pass

    def on_hide(self):
        turn_off_leds(self.np, self.led_power)
        gc.collect()


# ---------------------------------------------------------
# END SCREEN
# ---------------------------------------------------------

class SlayerEnd(Screen):
    def __init__(self, *args, **kwargs):
        super().__init__()

        level = kwargs.get("level", 0)
        kills = kwargs.get("kills", 0)
        victory = kwargs.get("victory", False)

        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wri_big = CWriter(ssd, arial35, D_PINK, BLACK, verbose=False)

        if victory:
            Label(wri, 5, 2, 316,
                  justify=Label.CENTRE, fgcolor=D_GREEN
                  ).value("NETWORK SECURED!")
            Label(wri_big, 25, 2, 316,
                  justify=Label.CENTRE).value("VICTORY")
        else:
            Label(wri, 5, 2, 316,
                  justify=Label.CENTRE, fgcolor=RED
                  ).value("SYSTEM COMPROMISED")
            Label(wri_big, 25, 2, 316,
                  justify=Label.CENTRE).value("PWNED")

        rank = get_rank(level)
        Label(wri, 70, 2, 316,
              justify=Label.CENTRE, fgcolor=D_GREEN
              ).value(f"Rank: {rank}")
        Label(wri, 90, 2, 316,
              justify=Label.CENTRE, fgcolor=D_GREEN
              ).value(f"Cleared: {level}/{NUM_LEVELS} | Kills: {kills}")

        quote = random.choice(VICTORY_QUOTES if victory else DEFEAT_QUOTES)
        Label(wri, 110, 2, 316,
              justify=Label.CENTRE, fgcolor=WHITE
              ).value(quote)

        # LED animations
        self.led_power = LED_ACTIVATE_PIN
        self.led_power.value(1)
        self.np = NeoPixel(LED_PIN, 10)

        if victory:
            self.reg_task(self._victory_leds(), False)
        else:
            self.reg_task(self._death_leds(level), False)

        Button(
            wri, 130, 30, width=120, height=26,
            text="Menu",
            fgcolor=D_GREEN, textcolor=D_GREEN,
            callback=lambda *_: self.go_menu(),
        )
        Button(
            wri, 130, 170, width=120, height=26,
            text="Again",
            fgcolor=D_GREEN, textcolor=D_GREEN,
            callback=lambda *_: Screen.change(
                SlayerBattle, mode=Screen.REPLACE),
        )

    def go_menu(self):
        turn_off_leds(self.np, self.led_power)
        Screen.change(SlayerIntro, mode=Screen.REPLACE)

    async def _victory_leds(self):
        try:
            colors = [(0, 255, 0), (0, 0, 255), (255, 0, 255)]
            idx = 0
            for _ in range(20):
                for i in range(10):
                    self.np[i] = colors[(idx + i) % len(colors)]
                self.np.write()
                idx += 1
                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            pass

    async def _death_leds(self, level):
        try:
            # Show cleared levels in dim green
            for i in range(10):
                if i < level:
                    self.np[9 - i] = (0, 40, 0)
                else:
                    self.np[9 - i] = (0, 0, 0)
            self.np.write()
            await asyncio.sleep(0.5)

            # Red flash
            for i in range(10):
                self.np[i] = (80, 0, 0)
            self.np.write()
            await asyncio.sleep(0.3)

            # Cascade dark
            for i in range(10):
                self.np[i] = (0, 0, 0)
                self.np.write()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    def on_hide(self):
        turn_off_leds(self.np, self.led_power)


# ---------------------------------------------------------
# GAME CONFIG
# ---------------------------------------------------------

def badge_game_config():
    return {
        "con_id": 6,
        "title": "CyberSlayer",
        "screen_class": SlayerIntro,
        "screen_args": (),
        "multiplayer": False,
        "description": "Breach the network. Slay the threats.",
    }

#-*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 4.3 (Never-Miss Edition, built on v4.2)
#  Author: reali22
#  Description: Smart Category Sorting, Strict Adult Filter, Zero Lag.
# ============================================================================

import os
import time
import json
import random
import glob
import re
from sys import version_info
from urllib.parse import quote
from collections import OrderedDict
import threading
import subprocess
import shutil
import ssl
import urllib.request as _urlrequest

# --- Enigma2 Imports ---
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
try:
    from Screens.VirtualKeyBoard import VirtualKeyBoard
    HAVE_VIRTUAL_KEYBOARD = True
except Exception:
    HAVE_VIRTUAL_KEYBOARD = False

try:
    from Components.ScrollLabel import ScrollLabel
except Exception:
    from Components.Label import Label as ScrollLabel

try:
    from RecordTimer import RecordTimerEntry, parseEvent
    from ServiceReference import ServiceReference
    HAVE_RECORDTIMER = True
except Exception:
    HAVE_RECORDTIMER = False

try:
    from twisted.internet import reactor
except Exception:
    reactor = None

from Components.ActionMap import ActionMap, NumberActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress
from Components.ConfigList import ConfigListScreen
from Components.config import (
    config,
    ConfigSubsection,
    ConfigText,
    ConfigYesNo,
    ConfigSelection,
    getConfigListEntry,
    configfile
)
from enigma import (
    eEPGCache,
    eServiceReference,
    eServiceCenter,
    eListboxPythonMultiContent,
    gFont,
    RT_HALIGN_LEFT,
    RT_VALIGN_CENTER,
    RT_HALIGN_RIGHT,
    RT_HALIGN_CENTER,
    loadPNG,
    quitMainloop,
    eTimer,
    ePicLoad,
    getDesktop
)
try:
    from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO
    PICON_SCALE_FLAGS = BT_SCALE | BT_KEEP_ASPECT_RATIO
except Exception:
    PICON_SCALE_FLAGS = 1 | 2

from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

# --- Configuration ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.api_key = ConfigText(default="", visible_width=50, fixed_size=False)
config.plugins.WhatToWatch.enable_ai = ConfigYesNo(default=False)
config.plugins.WhatToWatch.transparent_bg = ConfigYesNo(default=False)
config.plugins.WhatToWatch.discovery_mode = ConfigYesNo(default=False)
config.plugins.WhatToWatch.discovery_interval = ConfigSelection(
    default="15",
    choices=[
        ("1", "1 minute"),
        ("3", "3 minutes"),
        ("5", "5 minutes"),
        ("10", "10 minutes"),
        ("15", "15 minutes"),
        ("30", "30 minutes"),
        ("60", "60 minutes")
    ]
)
config.plugins.WhatToWatch.discovery_duration = ConfigSelection(
    default="8",
    choices=[
        ("5", "5 seconds"),
        ("8", "8 seconds"),
        ("10", "10 seconds"),
        ("15", "15 seconds")
    ]
)
DISCOVERY_SAT_CHOICES = [
    ("all", "All Satellites / All Sources"),
    ("13.0E", "Hotbird (13.0°E)"),
    ("16.0E", "Eutelsat 16 (16.0°E)"),
    ("19.2E", "Astra 19 (19.2°E)"),
    ("7.0W", "Nilesat (7.0°W / 7.3°W)"),
    ("26.0E", "Badr / Es'hail (26.0°E)"),
    ("28.2E", "Astra 28 (28.2°E)"),
    ("42.0E", "Türksat (42.0°E)"),
    ("30.0W", "Hispasat (30.0°W)"),
    ("0.8W", "Thor / Intelsat (0.8°W)"),
    ("4.0W", "Amos (4.0°W)"),
    ("5.0W", "Eutelsat 5 (5.0°W)"),
    ("7.0E", "Eutelsat 7 (7.0°E)"),
    ("9.0E", "Eutelsat 9 (9.0°E)"),
    ("10.0E", "Eutelsat 10 (10.0°E)"),
    ("21.6E", "Eutelsat 21 (21.6°E)"),
    ("23.5E", "Astra 23 (23.5°E)"),
    ("39.0E", "Hellas Sat (39.0°E)"),
    ("52.0E", "Yahsat (52.0°E)"),
    ("IPTV", "IPTV Streams"),
    ("DVB-T/C", "Terrestrial / Cable (DVB-T/C)")
]
config.plugins.WhatToWatch.discovery_sat = ConfigSelection(
    default="all",
    choices=DISCOVERY_SAT_CHOICES
)
DISCOVERY_CAT_CHOICES = [
    ("all", "All Categories"),
    ("News", "News"),
    ("Sports", "Sports"),
    ("Movies", "Movies"),
    ("Series", "Series"),
    ("Kids", "Kids"),
    ("Music", "Music"),
    ("Documentary", "Documentary"),
    ("Religious", "Religious"),
    ("General", "General")
]
DISCOVERY_POS_CHOICES = [
    ("top_left", "Top-Left Corner (Default)"),
    ("top_right", "Top-Right Corner"),
    ("bottom_left", "Bottom-Left Corner"),
    ("bottom_right", "Bottom-Right Corner"),
    ("top_center", "Top-Center")
]
DISCOVERY_TRANS_CHOICES = [
    ("10", "Solid / High Contrast (Recommended)"),
    ("25", "Slightly Transparent"),
    ("40", "Medium Transparent"),
    ("60", "Glass / Highly Transparent")
]
config.plugins.WhatToWatch.discovery_category = ConfigSelection(
    default="all",
    choices=DISCOVERY_CAT_CHOICES
)
config.plugins.WhatToWatch.discovery_position = ConfigSelection(
    default="top_left",
    choices=DISCOVERY_POS_CHOICES
)
config.plugins.WhatToWatch.discovery_transparency = ConfigSelection(
    default="10",
    choices=DISCOVERY_TRANS_CHOICES
)
config.plugins.WhatToWatch.discovery_sound = ConfigYesNo(default=False)
config.plugins.WhatToWatch.adult_filter = ConfigYesNo(default=True)
config.plugins.WhatToWatch.use_dvb_genre = ConfigYesNo(default=True)
config.plugins.WhatToWatch.default_lead_time = ConfigSelection(
    default="0",
    choices=[
        ("0", "At start"),
        ("300", "5 minutes before"),
        ("900", "15 minutes before"),
        ("1800", "30 minutes before")
    ]
)
config.plugins.WhatToWatch.sort_mode = ConfigSelection(
    default="category",
    choices=[
        ("category", "Category & Time"),
        ("channel", "Channel Name"),
        ("time", "Start Time")
    ]
)

config.plugins.WhatToWatch.follow_enabled = ConfigYesNo(default=True)

# --- Constants ---
VERSION = "4.3"
AUTHOR = "reali22"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")
SOUND_FILE = os.path.join(PLUGIN_PATH, "pop.mp3")
PINNED_FILE = "/etc/enigma2/wtw_pinned.json"
WATCHLIST_FILE = "/etc/enigma2/wtw_watchlist.json"
OVERRIDES_FILE = "/etc/enigma2/wtw_overrides.json"
FOLLOW_FILE = "/etc/enigma2/wtw_follow.json"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- PICON PATHS ---
PICON_PATHS = [
    "/omb/picon/",
    "/share/enigma2/Fury-FHD/piconProv/",
    "/usr/share/enigma2/picon/",
    "/picon/",
    "/media/usb/picon/",
    "/media/hdd/picon/",
    "/media/mmc/picon/",
    "/media/ba/picon/",
    "/media/sda1/picon/",
    "/media/sdb1/picon/",
    "/data/picon/",
    "/usr/share/enigma2/picon_50x30/",
    "/media/usb/picon_50x30/",
    "/media/hdd/picon_50x30/"
]

# --- SATELLITE REGISTRY ---
KNOWN_SATELLITES = {
    "13.0E": "Hotbird (13.0°E)",
    "16.0E": "Eutelsat 16 (16.0°E)",
    "19.2E": "Astra 19 (19.2°E)",
    "7.0W":  "Nilesat (7.0°W)",
    "7.3W":  "Eutelsat 7W / Nilesat (7.3°W)",
    "26.0E": "Badr / Es'hail (26.0°E)",
    "28.2E": "Astra 28 (28.2°E)",
    "42.0E": "Türksat (42.0°E)",
    "30.0W": "Hispasat (30.0°W)",
    "0.8W":  "Thor / Intelsat (0.8°W)",
    "4.0W":  "Amos (4.0°W)",
    "5.0W":  "Eutelsat 5 (5.0°W)",
    "7.0E":  "Eutelsat 7 (7.0°E)",
    "9.0E":  "Eutelsat 9 (9.0°E)",
    "10.0E": "Eutelsat 10 (10.0°E)",
    "21.6E": "Eutelsat 21 (21.6°E)",
    "23.5E": "Astra 23 (23.5°E)",
    "39.0E": "Hellas Sat (39.0°E)",
    "52.0E": "Yahsat (52.0°E)",
    "52.5E": "Yahsat 1A (52.5°E)",
    "IPTV":   "IPTV Streams",
    "DVB-T/C": "Terrestrial / Cable (DVB-T/C)"
}

def get_sat_display_name(sat_pos):
    if not sat_pos:
        return "Unknown"
    clean = str(sat_pos).strip()
    if clean in KNOWN_SATELLITES:
        return KNOWN_SATELLITES[clean]
    norm = clean.replace(".0", "")
    for k, v in KNOWN_SATELLITES.items():
        if k.replace(".0", "") == norm:
            return v
    return f"Sat {clean}"

def sat_matches(sat_val, filter_val):
    if not filter_val or filter_val == "all":
        return True
    if not sat_val:
        return False
    if sat_val == filter_val:
        return True

    s = str(sat_val).upper().strip()
    f = str(filter_val).upper().strip()
    if s == f:
        return True

    # Hotbird tolerances (13.0°E, 13E, 13.1°E, 13.2°E, 12.9°E)
    if f in ("13.0E", "13E") and s in ("13.0E", "13E", "13.1E", "13.2E", "12.9E", "12.8E"):
        return True

    # Nilesat tolerances (7.0°W, 7W, 7.2°W, 7.3°W, 8.0°W)
    if f in ("7.0W", "7W") and s in ("7.0W", "7W", "7.2W", "7.3W", "8.0W", "6.8W"):
        return True

    # Astra 19.2 tolerances (19.2°E, 19E, 19.0°E, 19.1°E)
    if f in ("19.2E", "19E") and s in ("19.2E", "19E", "19.0E", "19.1E", "19.3E"):
        return True

    # Eutelsat 16 tolerances (16.0°E, 16E, 15.8°E, 16.1°E)
    if f in ("16.0E", "16E") and s in ("16.0E", "16E", "15.8E", "16.1E", "16.2E"):
        return True

    # Astra 28 tolerances (28.2°E, 28E, 28.4°E, 28.5°E)
    if f in ("28.2E", "28E") and s in ("28.2E", "28E", "28.4E", "28.5E"):
        return True

    # Badr 26 tolerances (26.0°E, 26E, 25.5°E, 25.8°E)
    if f in ("26.0E", "26E") and s in ("26.0E", "26E", "25.5E", "25.8E", "26.1E"):
        return True

    # Türksat 42 tolerances (42.0°E, 42E, 41.9°E, 42.1°E)
    if f in ("42.0E", "42E") and s in ("42.0E", "42E", "41.9E", "42.1E"):
        return True

    # Yahsat 52 tolerances (52.0°E, 52.5°E, 52E)
    if f in ("52.0E", "52.5E", "52E") and s in ("52.0E", "52.5E", "52E", "51.5E"):
        return True

    # Generic degree proximity check (within 0.35 degrees)
    try:
        if (s.endswith("E") and f.endswith("E")) or (s.endswith("W") and f.endswith("W")):
            val_s = float(s[:-1])
            val_f = float(f[:-1])
            if abs(val_s - val_f) <= 0.35:
                return True
    except Exception:
        pass

    return False

SAT_SHORT_NAMES = {
    "13.0E": "Hotbird 13.0°E",
    "16.0E": "Eutelsat 16°E",
    "19.2E": "Astra 19.2°E",
    "7.0W":  "Nilesat 7.0°W",
    "7.3W":  "Nilesat 7.3°W",
    "26.0E": "Badr 26.0°E",
    "28.2E": "Astra 28.2°E",
    "42.0E": "Türksat 42.0°E",
    "30.0W": "Hispasat 30.0°W",
    "0.8W":  "Thor 0.8°W",
    "4.0W":  "Amos 4.0°W",
    "5.0W":  "Eutelsat 5.0°W",
    "7.0E":  "Eutelsat 7.0°E",
    "9.0E":  "Eutelsat 9.0°E",
    "10.0E": "Eutelsat 10.0°E",
    "21.6E": "Eutelsat 21.6°E",
    "23.5E": "Astra 23.5°E",
    "39.0E": "Hellas Sat 39.0°E",
    "52.0E": "Yahsat 52.0°E",
    "52.5E": "Yahsat 52.5°E",
    "IPTV":   "IPTV",
    "DVB-T/C": "DVB-T/C"
}

def get_sat_short_name(sat_pos):
    if not sat_pos:
        return ""
    clean = str(sat_pos).strip()
    if clean in SAT_SHORT_NAMES:
        return SAT_SHORT_NAMES[clean]
    norm = clean.replace(".0", "")
    for k, v in SAT_SHORT_NAMES.items():
        if k.replace(".0", "") == norm:
            return v
    return f"Sat {clean}"

# --- COMPREHENSIVE CHANNEL CATEGORY DATABASE ---
# Direct channel name -> category lookup (research-backed, 500+ channels)
# Names are matched after normalization: lowercase, strip HD/SD/FHD/4K/UHD/+1/+2
CHANNEL_CATEGORY_MAP = {
    # ==================== SPORTS ====================
    # beIN Sports
    "bein sports": "Sports", "bein sports 1": "Sports", "bein sports 2": "Sports",
    "bein sports 3": "Sports", "bein sports 4": "Sports", "bein sports 5": "Sports",
    "bein sports 6": "Sports", "bein sports 7": "Sports", "bein sports 8": "Sports",
    "bein sports 9": "Sports", "bein sports news": "News",
    "bein sports 1 en": "Sports", "bein sports 2 en": "Sports", "bein sports 3 en": "Sports",
    "bein sports 1 fr": "Sports", "bein sports 2 fr": "Sports",
    "bein sports xtra 1": "Sports", "bein sports xtra 2": "Sports",
    "bein sports xtra 3": "Sports", "bein sports xtra 4": "Sports",
    "bein sports max 1": "Sports", "bein sports max 2": "Sports",
    "bein sports max 3": "Sports", "bein sports max 4": "Sports",
    "bein sports max 5": "Sports", "bein sports max 6": "Sports",
    "bein sports 1 afc": "Sports", "bein sports 2 afc": "Sports", "bein sports 3 afc": "Sports",
    "bein 4k": "Sports", "bein sports haber": "Sports",
    # SSC
    "ssc 1": "Sports", "ssc 2": "Sports", "ssc 3": "Sports", "ssc 4": "Sports", "ssc 5": "Sports",
    "ssc extra 1": "Sports", "ssc extra 2": "Sports", "ssc extra 3": "Sports", "ssc news": "News",
    # Abu Dhabi & Dubai Sports
    "abu dhabi sports 1": "Sports", "abu dhabi sports 2": "Sports", "abu dhabi sports": "Sports",
    "ad sports 1": "Sports", "ad sports 2": "Sports",
    "ad sports premium 1": "Sports", "ad sports premium 2": "Sports",
    "yas sports": "Sports", "yas": "Sports",
    "dubai sports 1": "Sports", "dubai sports 2": "Sports", "dubai sports 3": "Sports", "dubai sports": "Sports",
    "dubai racing 1": "Sports", "dubai racing 2": "Sports", "dubai racing 3": "Sports", "dubai racing": "Sports",
    # Egyptian Sports
    "on time sports 1": "Sports", "on time sports 2": "Sports", "on time sports 3": "Sports",
    "on time sports": "Sports", "on sport": "Sports", "nile sport": "Sports",
    "al ahly": "Sports", "zamalek": "Sports",
    # Qatar & Gulf Sports
    "alkass": "Sports", "alkass 1": "Sports", "alkass 2": "Sports", "alkass 3": "Sports",
    "alkass 4": "Sports", "alkass 5": "Sports", "alkass 6": "Sports", "alkass 7": "Sports", "alkass 8": "Sports",
    "sharjah sport": "Sports", "sharjah sports": "Sports",
    "kuwait sport": "Sports", "kuwait sports": "Sports",
    "ksa sport 1": "Sports", "ksa sport 2": "Sports", "ksa sports": "Sports",
    "bahrain sport": "Sports", "oman sport": "Sports", "iraq sport": "Sports",
    "arryadia": "Sports", "arryadia tnt": "Sports",
    # Sky Sports (UK)
    "sky sports main event": "Sports", "sky sports premier league": "Sports",
    "sky sports football": "Sports", "sky sports cricket": "Sports",
    "sky sports golf": "Sports", "sky sports f1": "Sports",
    "sky sports tennis": "Sports", "sky sports action": "Sports",
    "sky sports arena": "Sports", "sky sports racing": "Sports",
    "sky sports mix": "Sports", "sky sports news": "News",
    # Sky Sport (Italy)
    "sky sport uno": "Sports", "sky sport calcio": "Sports", "sky sport football": "Sports",
    "sky sport arena": "Sports", "sky sport tennis": "Sports", "sky sport f1": "Sports",
    "sky sport motogp": "Sports", "sky sport nba": "Sports", "sky sport golf": "Sports",
    "sky sport max": "Sports", "sky sport 24": "News",
    # Sky Sport (Germany)
    "sky sport bundesliga": "Sports", "sky sport top event": "Sports",
    "sky sport news": "News",
    # European Sports
    "eurosport 1": "Sports", "eurosport 2": "Sports", "eurosport 4k": "Sports",
    "polsat sport 1": "Sports", "polsat sport 2": "Sports", "polsat sport 3": "Sports",
    "polsat sport fight": "Sports", "polsat sport premium 1": "Sports",
    "polsat sport premium 2": "Sports", "polsat sport extra": "Sports",
    "canal+ sport": "Sports", "canal+ sport 2": "Sports", "canal+ sport 3": "Sports",
    "canal+ sport 4": "Sports", "canal+ sport 5": "Sports", "canal+ foot": "Sports",
    "eleven sports 1": "Sports", "eleven sports 2": "Sports",
    "eleven sports 3": "Sports", "eleven sports 4": "Sports",
    "tnt sports 1": "Sports", "tnt sports 2": "Sports", "tnt sports 3": "Sports", "tnt sports 4": "Sports",
    "premier sports 1": "Sports", "premier sports 2": "Sports",
    "boxnation": "Sports", "racing tv": "Sports",
    "rai sport": "Sports", "supertennis": "Sports", "tvp sport": "Sports",
    "sport1": "Sports", "equidia": "Sports",
    "nova sports prime": "Sports", "nova sports 1": "Sports", "nova sports 2": "Sports",
    "sport klub 1": "Sports", "sport klub 2": "Sports", "sport klub 3": "Sports",
    "arena sport 1": "Sports", "arena sport 2": "Sports", "arena sport 3": "Sports",
    "supersport 1": "Sports", "supersport 2": "Sports", "supersport 3": "Sports",
    "espn": "Sports", "dazn": "Sports",
    # Turkish Sports
    "trt spor": "Sports", "trt spor yildiz": "Sports",
    "a spor": "Sports", "s sport": "Sports", "s sport 2": "Sports",
    "tv8.5": "Sports", "sports tv": "Sports",
    "fb tv": "Sports", "gs tv": "Sports",
    "bein sports 1 tr": "Sports", "bein sports 2 tr": "Sports",
    # Spanish Sports
    "teledeporte": "Sports", "gol play": "Sports",
    "real madrid tv": "Sports", "barca tv": "Sports",
    "l'equipe": "Sports", "rmc sport 1": "Sports", "rmc sport 2": "Sports",
    # Club Channels
    "lfctv": "Sports", "mutv": "Sports",

    # ==================== NEWS ====================
    # Pan-Arab News
    "al jazeera": "News", "al jazeera arabic": "News", "al jazeera english": "News",
    "al jazeera mubasher": "News", "al jazeera balkans": "News",
    "al arabiya": "News", "alarabiya": "News",
    "al hadath": "News", "sky news arabia": "News",
    "asharq news": "News", "cnbc arabiya": "News",
    "al ekhbariya": "News", "ekhbariya": "News",
    "france 24 arabic": "News", "france 24": "News",
    "dw arabic": "News", "dw": "News",
    "rt arabic": "News", "trt arabi": "News", "trt world": "News",
    "al ghad": "News", "alghad": "News",
    "al araby": "News", "al mayadeen": "News",
    "al hurra": "News", "rudaw": "News", "kurdistan 24": "News",
    "i24 news": "News", "palestine news": "News",
    # Egyptian News
    "extra news": "News", "extra live": "News",
    "al qahera news": "News", "al qahera wal nas": "General",
    # International News
    "bbc news": "News", "bbc world": "News", "bbc arabic": "News", "bbc persian": "News",
    "bbc parliament": "News",
    "sky news": "News", "sky tg24": "News",
    "cnn": "News", "cnn international": "News", "cnn turk": "News",
    "euronews": "News", "bloomberg": "News", "cnbc": "News",
    "fox news": "News", "msnbc": "News",
    "nhk world": "News", "cgtn": "News",
    "gb news": "News", "talktv": "News",
    # Turkish News
    "trt haber": "News", "a haber": "News", "haberturk": "News",
    "ntv": "News", "halk tv": "News", "tele1": "News",
    "sozcu tv": "News", "szc tv": "News", "bloomberg ht": "News",
    "haber global": "News",
    # European News
    "tagesschau24": "News", "phoenix": "News", "n-tv": "News", "welt": "News",
    "bfm tv": "News", "cnews": "News", "lci": "News", "franceinfo": "News",
    "tvn24": "News", "tvn24 bis": "News", "polsat news": "News",
    "tvp info": "News", "wydarzenia 24": "News",
    "rai news 24": "News", "tgcom24": "News",
    "n1": "News", "al jazeera balkans": "News",
    # Algerian News
    "echorouk news": "News", "ennahar tv": "News", "al24 news": "News", "el bilad": "News",

    # ==================== MOVIES ====================
    # MBC Movies
    "mbc 2": "Movies", "mbc max": "Movies", "mbc action": "Movies", "mbc bollywood": "Movies",
    # Rotana Movies
    "rotana cinema": "Movies", "rotana cinema ksa": "Movies", "rotana cinema masr": "Movies",
    "rotana classic": "Movies", "rotana comedy": "Movies",
    # beIN Movies
    "bein movies 1": "Movies", "bein movies 1 premiere": "Movies",
    "bein movies 2": "Movies", "bein movies 2 action": "Movies",
    "bein movies 3": "Movies", "bein movies 3 drama": "Movies",
    "bein movies 4": "Movies", "bein movies 4 family": "Movies",
    "bein movies turk": "Movies",
    # OSN Movies
    "osntv movies premiere": "Movies", "osntv movies hollywood": "Movies",
    "osntv movies action": "Movies", "osntv movies comedy": "Movies",
    "osntv movies family": "Movies", "osntv movies horror": "Movies",
    "osntv pop up": "Movies", "osntv yahala aflam": "Movies", "osn movies": "Movies",
    # ART & Alfa Movies
    "art aflam 1": "Movies", "art aflam 2": "Movies", "art cinema": "Movies",
    "alfa cinema 1": "Movies", "alfa cinema 2": "Movies",
    # South Asian Movies
    "zee aflam": "Movies", "zee cinema": "Movies", "b4u movies": "Movies", "b4u aflam": "Movies",
    "colors cineplex": "Movies", "sony max": "Movies", "star gold": "Movies",
    # Egyptian / Nilesat Cinema
    "al nahar cinema": "Movies", "dubai one": "Movies",
    "mix hollywood": "Movies", "scare tv": "Movies", "scare": "Movies",
    "c1 action": "Movies", "spider action": "Movies",
    "top movies": "Movies", "imagine movies": "Movies", "toktok cima": "Movies",
    # Sky Cinema (UK)
    "sky cinema premiere": "Movies", "sky cinema select": "Movies", "sky cinema hits": "Movies",
    "sky cinema greats": "Movies", "sky cinema animation": "Movies",
    "sky cinema family": "Movies", "sky cinema action": "Movies",
    "sky cinema comedy": "Movies", "sky cinema thriller": "Movies",
    "sky cinema sci-fi & horror": "Movies", "sky cinema drama": "Movies",
    # Sky Cinema (Italy)
    "sky cinema uno": "Movies", "sky cinema due": "Movies", "sky cinema collection": "Movies",
    "sky cinema suspense": "Movies", "sky cinema romance": "Movies",
    # Sky Cinema (Germany)
    "sky cinema classics": "Movies", "sky cinema highlights": "Movies",
    # European Movies
    "canal+ cinema": "Movies", "canal+ film": "Movies", "canal+ premium": "Movies",
    "canal+ box office": "Movies", "canal+ grand ecran": "Movies",
    "cine+ premier": "Movies", "cine+ frisson": "Movies", "cine+ emotion": "Movies",
    "cine+ family": "Movies", "cine+ festival": "Movies", "cine+ classic": "Movies",
    "film4": "Movies", "5action": "Movies",
    "great! movies": "Movies", "great! action": "Movies", "great! romance": "Movies",
    "legend": "Movies", "talking pictures tv": "Movies",
    "hbo": "Movies", "hbo 2": "Movies", "hbo 3": "Movies",
    "cinemax": "Movies", "cinemax 2": "Movies",
    "ale kino+": "Movies", "kino polska": "Movies", "polsat film": "Movies", "stopklatka": "Movies",
    "filmbox extra": "Movies", "filmbox premium": "Movies", "filmbox family": "Movies",
    "filmbox action": "Movies", "filmbox arthouse": "Movies",
    "rai movie": "Movies", "iris": "Movies", "cine34": "Movies",
    "warner tv film": "Movies", "kinowelt tv": "Movies", "tele 5": "Movies",
    # Spanish Movies
    "canal hollywood": "Movies", "tcm": "Movies", "dark": "Movies", "somos": "Movies",
    "paramount network": "Movies",
    # Turkish Movies
    "sinema tv": "Movies", "sinema tv 2": "Movies", "sinema tv aile": "Movies",
    "sinema tv aksiyon": "Movies", "sinema tv komedi": "Movies",
    "moviesmart premium": "Movies", "moviesmart platin": "Movies",
    "moviesmart action": "Movies", "moviesmart classic": "Movies",
    "moviesmart family": "Movies", "moviesmart turk": "Movies",
    # Balkan Movies
    "cinestar tv 1": "Movies", "cinestar tv 2": "Movies",
    "cinestar tv premiere 1": "Movies", "cinestar tv premiere 2": "Movies",
    "pink film": "Movies", "pink movies": "Movies", "pink action": "Movies",

    # ==================== SERIES / DRAMA ====================
    # MBC Series
    "mbc drama": "Series", "mbc drama+": "Series", "mbc 4": "Series",
    # Rotana
    "rotana drama": "Series",
    # beIN Series
    "bein series 1": "Series", "bein series 2": "Series",
    "bein drama": "Series", "bein drama 1": "Series",
    # OSN Series
    "osntv showcase": "Series", "osntv showcase classics": "Series",
    "osntv comedy": "Series", "osntv crime": "Series",
    "osntv iqiyi": "Series", "osntv yahala bil arabi": "Series",
    "alfa series": "Series",
    # ART Series
    "art hekayat": "Series", "art hekayat 2": "Series",
    # Egyptian Drama
    "cbc drama": "Series", "dmc drama": "Series", "on drama": "Series",
    "al hayah drama": "Series", "al nahar drama": "Series",
    "sada el balad drama": "Series", "panorama drama": "Series", "panorama drama 2": "Series",
    "mix belaraby": "Series", "mix drama": "Series", "drama alwan": "Series",
    # South Asian Series
    "zee alwan": "Series", "zee tv": "Series", "colors": "Series", "colors rishtey": "Series",
    "sony entertainment": "Series", "sony sab": "Series", "sony pal": "Series",
    "star plus": "Series", "star bharat": "Series", "b4u plus": "Series",
    # Sky Series
    "sky atlantic": "Series", "sky serie": "Series", "sky witness": "Series",
    "sky sci-fi": "Series", "sky crime": "Documentary",
    # UK Series
    "bbc first": "Series", "bbc drama": "Series",
    "itv3": "Series", "5usa": "Series",
    "alibi": "Series", "u&drama": "Series", "great! tv": "Series",
    # European Series
    "warner tv serie": "Series", "warner tv comedy": "Series",
    "13th street": "Series", "syfy": "Series", "universal tv": "Series",
    "canal+ series": "Series", "polar+": "Series",
    "axn": "Series", "fox": "Series",
    "tf1 series films": "Series", "cherie 25": "Series",
    "nova series": "Series", "pink serije": "Series",
    # Turkish Series
    "dizismart max": "Series", "dizismart premium": "Series",
    "fx turkiye": "Series",
    # Spanish Series
    "axn espana": "Series", "calle 13": "Series", "cosmo": "Series",
    "divinity": "Series", "energy": "Series", "fdf": "Series", "nova": "Series",
    # Italian Series
    "rai 4": "Series", "rai premium": "Series", "top crime": "Series",
    "giallo": "Series", "warner tv italia": "Series",
    "sky investigation": "Series",
    # General Entertainment → Series
    "show tv": "Series", "star tv": "Series", "atv": "Series",
    "kanal d": "Series",

    # ==================== KIDS ====================
    # Arabic Kids
    "spacetoon": "Kids", "spacetoon english": "Kids",
    "mbc 3": "Kids", "majid": "Kids", "majid tv": "Kids",
    "baraem": "Kids", "jeem": "Kids", "jeem tv": "Kids",
    "toyor al janah": "Kids", "toyor baby": "Kids",
    "karameesh": "Kids", "kooki kids": "Kids",
    "semsem": "Kids", "koogi tv": "Kids", "sanabel kids": "Kids",
    "rotana kids": "Kids",
    # International Kids
    "cartoon network": "Kids", "cn arabia": "Kids", "cn english": "Kids",
    "cartoonito": "Kids", "boomerang": "Kids",
    "nickelodeon": "Kids", "nick jr": "Kids", "nick jr.": "Kids",
    "nicktoons": "Kids", "teennick": "Kids",
    "disney channel": "Kids", "disney junior": "Kids", "disney xd": "Kids",
    "cbeebies": "Kids", "cbbc": "Kids",
    "baby tv": "Kids", "babytv": "Kids", "duck tv": "Kids",
    "dreamworks": "Kids",
    # European Kids
    "kika": "Kids", "super rtl": "Kids", "toggo": "Kids", "toggo plus": "Kids",
    "ric tv": "Kids",
    "gulli": "Kids", "piwi+": "Kids", "teletoon+": "Kids",
    "canal j": "Kids", "tiji": "Kids", "canal+ kids": "Kids",
    "rai yoyo": "Kids", "rai gulp": "Kids",
    "boing": "Kids", "frisbee": "Kids", "k2": "Kids",
    "dea kids": "Kids", "dea junior": "Kids", "super!": "Kids",
    "tvp abc": "Kids", "minimini+": "Kids", "teletoon+ hd": "Kids",
    "4fun kids": "Kids",
    "clan": "Kids", "clan tve": "Kids", "boing espana": "Kids",
    "pop": "Kids", "tiny pop": "Kids", "pop max": "Kids",
    "sky kids": "Kids",
    # Turkish Kids
    "trt cocuk": "Kids", "minika cocuk": "Kids", "minika go": "Kids",
    "zarok tv": "Kids",

    # ==================== MUSIC ====================
    # Arabic Music
    "rotana clip": "Music", "rotana mousica": "Music",
    "mazzika": "Music", "melody hits": "Music", "melody": "Music",
    "wanasah": "Music", "aghani aghani": "Music", "aghani": "Music",
    "arabica tv": "Music", "hawas tv": "Music",
    "alfa fann": "Music", "alfa music now": "Music",
    # International Music
    "mtv live": "Music", "mtv hits": "Music", "mtv 80s": "Music",
    "mtv 90s": "Music", "mtv 00s": "Music", "club mtv": "Music",
    "vh1": "Music", "trace urban": "Music", "trace latina": "Music",
    "nrj hits": "Music", "cstar": "Music",
    "mezzo": "Music", "mezzo live": "Music",
    # Polish Music
    "4fun.tv": "Music", "4fun tv": "Music", "4fun dance": "Music",
    "stars.tv": "Music", "polo tv": "Music", "disco polo music": "Music",
    "eska tv": "Music", "eska tv extra": "Music",
    "vox music tv": "Music", "kino polska muzyka": "Music", "music box polska": "Music",
    # Italian Music
    "radio italia tv": "Music", "rtl 102.5 tv": "Music",
    "radio freccia": "Music", "radio zeta": "Music",
    "radio kiss kiss tv": "Music", "radio norba tv": "Music", "deejay tv": "Music",
    # German Music
    "deluxe music": "Music", "schlager deluxe": "Music",
    # Turkish Music
    "trt muzik": "Music", "power tv": "Music", "power turk tv": "Music",
    "dream tv": "Music", "dream turk": "Music",
    "kral tv": "Music", "kral pop": "Music",
    "number one tv": "Music", "number one turk tv": "Music",
    # Balkan Music
    "grand tv": "Music", "pink folk": "Music", "pink music": "Music",
    "dm sat": "Music", "cmc": "Music",
    # UK Music
    "now 70s": "Music", "now 80s": "Music", "now 90s": "Music", "now rock": "Music",
    "clubland tv": "Music", "box hits": "Music", "kerrang": "Music", "magic": "Music",
    "sol musica": "Music",

    # ==================== DOCUMENTARY ====================
    # Discovery Networks
    "discovery channel": "Documentary", "discovery science": "Documentary",
    "discovery turbo": "Documentary", "discovery history": "Documentary",
    "investigation discovery": "Documentary", "id": "Documentary",
    "animal planet": "Documentary", "dmax": "Documentary", "motor trend": "Documentary",
    "tlc": "General",
    "food network": "General", "hgtv": "General", "travel channel": "Documentary",
    # National Geographic
    "national geographic": "Documentary", "nat geo": "Documentary",
    "nat geo wild": "Documentary", "national geographic abu dhabi": "Documentary",
    # BBC Factual
    "bbc earth": "Documentary", "bbc four": "Documentary", "bbc two": "Documentary",
    "sky documentaries": "Documentary", "sky nature": "Documentary",
    "sky history": "Documentary", "sky history2": "Documentary",
    "sky arte": "Documentary",
    # History
    "history channel": "Documentary", "history": "Documentary", "history 2": "Documentary",
    "crime+investigation": "Documentary", "true crime": "Documentary",
    # French Documentary
    "planete+": "Documentary", "planete+ crime": "Documentary",
    "planete+ aventure": "Documentary", "ushuaia tv": "Documentary",
    "histoire tv": "Documentary", "toute l'histoire": "Documentary",
    "science & vie tv": "Documentary", "rmc decouverte": "Documentary",
    "rmc story": "Documentary",
    # Italian/European
    "rai 5": "Documentary", "rai storia": "Documentary", "rai scuola": "Documentary",
    "focus": "Documentary", "arte": "Documentary", "zdfinfo": "Documentary",
    "ard-alpha": "Documentary",
    "5select": "Documentary", "more4": "Documentary",
    "u&yesterday": "Documentary", "eden": "Documentary",
    # Al Jazeera Documentary
    "al jazeera documentary": "Documentary", "al jazeera doc": "Documentary",
    # Spanish Documentary
    "odisea": "Documentary", "canal historia": "Documentary",
    "canal cocina": "General", "canal decasa": "General",
    # Turkish Documentary
    "trt belgesel": "Documentary", "yaban tv": "Documentary",

    # ==================== RELIGIOUS ====================
    # Islamic
    "saudi quran": "Religious", "quran": "Religious", "saudi sunnah": "Religious", "sunnah": "Religious",
    "misr quran kareem": "Religious",
    "al majd": "Religious", "al majd quran": "Religious", "al majd hadith": "Religious",
    "iqraa": "Religious", "iqraa international": "Religious",
    "al resalah": "Religious", "resalah": "Religious",
    "al nas": "Religious", "al rahma": "Religious", "al fath": "Religious",
    "ahl al quran": "Religious", "al huda tv": "Religious",
    "peace tv": "Religious", "huda tv": "Religious",
    "karbala tv": "Religious", "karbala": "Religious",
    "al kafeel": "Religious", "al maaref": "Religious",
    "al anwar": "Religious", "al kawthar": "Religious",
    "noor dubai": "Religious", "al nahar noor": "Religious",
    # Christian
    "ctv coptic": "Religious", "aghapy tv": "Religious", "aghapy": "Religious",
    "me sat": "Religious", "al horreya tv": "Religious",
    "al karma tv": "Religious", "al hayat christian": "Religious",
    "noursat": "Religious", "tele lumiere": "Religious",
    "koogi tv": "Religious",
    # European Religious
    "tv2000": "Religious", "padre pio tv": "Religious", "telepace": "Religious",
    "kto": "Religious", "ewtn": "Religious", "tbn": "Religious",
    "god tv": "Religious", "daystar": "Religious",
    "bibel tv": "Religious", "k-tv": "Religious", "hope tv": "Religious",
    "revelation tv": "Religious", "faith world tv": "Religious",
    "islam channel": "Religious", "british muslim tv": "Religious", "ahlulbayt tv": "Religious",
    # Turkish Religious
    "diyanet tv": "Religious", "trt diyanet": "Religious",
    "semerkand tv": "Religious", "dost tv": "Religious",
    "lalegul tv": "Religious", "hilal tv": "Religious",
    "rehber tv": "Religious",

    # ==================== GENERAL ENTERTAINMENT ====================
    # MBC General
    "mbc 1": "General", "mbc 5": "General", "mbc masr": "General", "mbc masr 2": "General",
    "mbc iraq": "General", "mbc persia": "General", "mbc+ variety": "General",
    # OSN General
    "osntv one": "General", "osntv now": "General", "osntv mezze": "General",
    "osntv yahala": "General",
    # Gulf General
    "abu dhabi tv": "General", "emarat tv": "General",
    "dubai tv": "General", "sama dubai": "General",
    "rotana khalijia": "General",
    "lbc": "General", "lbc sat": "General",
    "alfa al yawm": "General",
    "bein gourmet": "General",
    # Egyptian General
    "cbc": "General", "cbc sofra": "General",
    "dmc": "General", "al hayah 1": "General",
    "on e": "General", "on tv": "General",
    "al nahar": "General", "sada el balad": "General",
    "ten tv": "General", "al mehwar": "General",
    # UK General
    "bbc one": "General", "bbc three": "General",
    "itv": "General", "itv1": "General", "itv2": "General", "itvbe": "General",
    "channel 4": "General", "e4": "General", "channel 5": "General", "5star": "General",
    "sky one": "General", "sky comedy": "General", "sky arts": "General", "sky mix": "General",
    "gold": "General", "comedy central": "General",
    # German General
    "das erste": "General", "ard": "General", "zdf": "General",
    "rtl": "General", "sat.1": "General", "prosieben": "General", "vox": "General",
    "kabel eins": "General", "rtl zwei": "General", "3sat": "General",
    # French General
    "tf1": "General", "france 2": "General", "france 3": "General",
    "m6": "General", "c8": "General", "w9": "General",
    "tv5 monde": "General",
    # Spanish General
    "la 1": "General", "antena 3": "General", "cuatro": "General",
    "telecinco": "General", "la sexta": "General",
    # Italian General
    "rai 1": "General", "rai 2": "General", "rai 3": "General",
    "canale 5": "General", "italia 1": "General", "rete 4": "General",
    "la7": "General", "tv8": "General", "nove": "General",
    "sky uno": "General",
    # Turkish General
    "trt 1": "General", "kanal 7": "General", "tv8": "General",
    "now tv": "General", "teve2": "General", "360": "General",
    # French Documentary -> General
    "france 5": "Documentary", "la 2": "Documentary",
}

# Normalize channel name for lookup: lowercase, strip HD/SD/FHD/4K/UHD and "+1" timeshift suffixes.
# "TV" is kept on the first pass (so "Show TV", "Racing TV", "Majid TV" stay reachable) and only
# dropped on a second, exact-match pass.
import re as _re
_STRIP_QUALITY = _re.compile(r'(?<![a-z0-9])(?:hd|sd|fhd|uhd|4k|8k|hevc|h\.?265|h\.?264)(?![a-z0-9])', _re.IGNORECASE)
_STRIP_TIMESHIFT = _re.compile(r'\s\+[0-9]{1,2}$')
_STRIP_TV = _re.compile(r'(?<![a-z0-9])tv(?![a-z0-9])')

def normalize_arabic(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    for c in ["َ", "ُ", "ِ", "ّ", "ْ", "ً", "ٌ", "ٍ"]:
        text = text.replace(c, "")
    return text

_ACCENT_MAP = {
    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a',
    'ó': 'o', 'ò': 'o', 'ô': 'o',
    'ú': 'u', 'ù': 'u', 'û': 'u',
    'í': 'i', 'ì': 'i', 'î': 'i',
    'ñ': 'n', 'ł': 'l', 'ć': 'c', 'ś': 's', 'ź': 'z', 'ż': 'z',
}

def _normalize_channel_for_lookup(name, strip_tv=False):
    """Normalize channel name for CHANNEL_CATEGORY_MAP lookup."""
    n = str(name or "").strip().lower()
    n = normalize_arabic(n)
    for a, b in _ACCENT_MAP.items():
        if a in n:
            n = n.replace(a, b)
    n = _STRIP_QUALITY.sub(" ", n)
    n = _STRIP_TIMESHIFT.sub("", n.strip())
    if strip_tv:
        n = _STRIP_TV.sub(" ", n)
    n = " ".join(n.split())
    return n.rstrip(" .")

# The database keys go through the same normalizer as the channel names, so a key such as
# "bein 4k" or "racing tv" can never drift out of reach of the lookup again.
_DB_EXACT = {}
_DB_NOTV = {}
for _k, _v in CHANNEL_CATEGORY_MAP.items():
    _nk = _normalize_channel_for_lookup(_k)
    if _nk:
        _DB_EXACT[_nk] = _v
for _k, _v in CHANNEL_CATEGORY_MAP.items():
    _nk = _normalize_channel_for_lookup(_k, strip_tv=True)
    if _nk and _nk not in _DB_EXACT:
        _DB_NOTV.setdefault(_nk, _v)

_MINOR_TOKENS = frozenset([
    "en", "ar", "fr", "tr", "de", "it", "es", "uk", "us", "int", "intl", "international",
    "arabic", "arabia", "english", "east", "west", "mena", "ksa", "uae"
])

def _is_minor_token(tok):
    return tok.isdigit() or len(tok) <= 2 or tok in _MINOR_TOKENS

def lookup_channel_category(channel_name):
    """Look up channel category from the comprehensive database. Returns category or None."""
    norm = _normalize_channel_for_lookup(channel_name)
    if not norm:
        return None
    hit = _DB_EXACT.get(norm)
    if hit:
        return hit
    notv = _normalize_channel_for_lookup(channel_name, strip_tv=True)
    if notv:
        hit = _DB_EXACT.get(notv) or _DB_NOTV.get(notv)
        if hit:
            return hit
    # Longest prefix match (for channels like "Sky Sport Bundesliga 3 HD").
    # A one-word prefix only counts when what follows is a number / region tag, so that
    # "HBO 2" -> "hbo" works but "Fox Sports" does not become "fox" (Series).
    parts = norm.split()
    for i in range(len(parts) - 1, 0, -1):
        hit = _DB_EXACT.get(" ".join(parts[:i]))
        if hit and (i >= 2 or all(_is_minor_token(t) for t in parts[i:])):
            return hit
    return None


# --- KEYWORD FALLBACK CATEGORIZATION ---
CATEGORIES_DATA = {
    "News": (0x808080,
        ["bbc news", "bbc world", "bbc arabic", "bbc persian", "bbc parliament", "cnn",
         "al jazeera", "alarabiya", "al arabiya", "skynews", "sky news", "cnbc", "bloomberg",
         "france 24", "dw ", "al hadath", "al hurra", "rudaw", "kurdistan",
         "ekhbariya", "al araby", "alghad", "i24", "euronews", "lci", "cnews", "bfm", "msnbc", "fox news",
         "rt arabic", "nhk", "cgtn", "tagesschau", "n-tv", "welt", "trt haber", "a haber",
         "haberturk", "ntv ", "halk tv", "tele1", "sozcu", "szc ", "phoenix",
         "tvn24", "polsat news", "tvp info", "wydarzenia", "rai news",
         "tgcom24", "n1 ", "extra news", "extra live", "al qahera news",
         "asharq news", "sky news arabia", "al mayadeen", "gb news", "talktv",
         "haber global", "echorouk news", "ennahar", "al24 news", "el bilad",
         "ssc news", "sky sport 24", "sky sports news", "sky sport news",
         "bein sports news", "polsat sport news", "franceinfo"],
        ["journal", "report", "briefing", "update", "headline", "breaking", "bulletin", "politics", "news",
         "interview", "debate", "parliament", "weather forecast",
         "نشرة", "الاخبار", "موجز", "الحصاد", "المسائية", "تقرير", "حوار", "لقاء خاص", "الحدث", "اخبار",
         "haber", "bulten", "nachrichten", "notizie", "telediario", "wiadomosci", "actualite"]),

    "Sports": (0xFF0000,
        ["sport", "bein ", "eurosport", "dazn", "ssc ", "alkass",
         "nba", "racing", "motogp", "formula 1", "wwe", "ufc", "fight", "arena sport",
         "canal+ sport", "canal+ foot", "eleven sport", "polsat sport",
         "ad sport", "abu dhabi sport", "dubai sport", "sharjah sport",
         "ksa sport", "kuwait sport", "yas ", "al ahly", "zamalek",
         "match", "espn", "on time sport", "nile sport",
         "sky sport", "sky sports", "tnt sport", "premier sport",
         "trt spor", "a spor", "s sport", "tv8.5",
         "supersport", "sport klub", "nova sport", "arena sport",
         "lfctv", "mutv", "fb tv", "gs tv", "boxnation", "racing tv",
         "supertennis", "rai sport", "tvp sport", "sport1",
         "equidia", "teledeporte", "gol play", "l'equipe",
         "rmc sport", "real madrid", "barca tv"],
        ["match", "vs ", "vs.", "league", "cup", "final", "premier", "bundesliga", "laliga", "serie a", "champion",
         "derby", "racing", "grand prix", "tournament", "olymp", "qualifier",
         "kick off", "half time", "halftime", "penalty", "goal", "offside",
         "مباراة", "الدوري", "كأس", "نهائي", "البطولة", "مباشر", "ستوديو", "الجولة", "ملخص", "كورة", "اهداف",
         "mac", "kupa", "lig", "futbol", "calcio", "fussball", "partita", "partido"]),

    "Movies": (0x0000FF,
        ["movie", "film", "cinema", "cine", "kino", "aflam",
         "hbo", "mbc 2", "mbc max", "mbc action", "mbc bollywood",
         "rotana cinema", "rotana classic", "rotana comedy",
         "zee aflam", "zee cinema", "b4u movies", "b4u aflam",
         "osn movies", "osntv movies", "bein movies",
         "art aflam", "alfa cinema", "dubai one",
         "sky cinema", "canal+ cinema", "canal+ film", "canal+ premium",
         "cine+", "filmbox", "cinemax",
         "great! movies", "great! action", "great! romance",
         "paramount", "tcm", "amc", "mgm",
         "scare", "imagine movies", "top movies", "c1 action",
         "mix hollywood", "toktok cima", "star cinema",
         "sinema tv", "moviesmart", "cinestar",
         "5action", "film4", "legend", "talking pictures",
         "iris", "cine34", "rai movie", "warner tv film",
         "ale kino", "kino polska", "polsat film", "stopklatka",
         "canal hollywood", "dark ", "somos"],
        ["starring", "directed by", "thriller", "horror", "sci-fi", "romance",
         "blockbuster", "cinema", "feature film",
         "فيلم", "سهرة سينمائية", "سينما", "افلام", "بطولة", "عرض اول",
         "sinema", "pelicula", "filme"]),

    "Series": (0xFFA500,
        ["drama", "series", "serial", "mosalsalat", "hikaya",
         "mbc drama", "mbc 4", "rotana drama",
         "bein series", "bein drama", "osn series", "osntv showcase", "osntv crime",
         "alfa series", "art hekayat",
         "cbc drama", "dmc drama", "on drama", "al hayah drama",
         "al nahar drama", "sada el balad drama", "panorama drama",
         "zee alwan", "zee tv", "colors", "sony entertainment", "star plus",
         "sky atlantic", "sky serie", "sky witness", "sky sci-fi",
         "bbc first", "bbc drama", "itv3", "5usa", "alibi",
         "canal+ series", "polar+", "axn", "13th street", "syfy",
         "warner tv serie", "universal tv",
         "tf1 series", "cherie 25", "divinity", "cosmo",
         "nova series", "pink serije",
         "show tv", "star tv", "atv ", "kanal d", "dizismart",
         "fx turkiye", "giallo", "top crime",
         "rai 4", "rai premium", "sky investigation",
         "novela", "dizi"],
        ["episode", "season", "series", "soap", "telenovela", "sitcom", "chapter",
         "s01", "s02", "e01", "e02", "pilot", "finale",
         "مسلسل", "حلقة", "موسم", "الجزء", "سلسلة", "دراما", "حكايات",
         "dizi", "bolum", "sezon", "staffel", "folge", "puntata", "odcinek", "episodio", "temporada"]),

    "Kids": (0x00FF00,
        ["cartoon", "cn ", "nickelodeon", "nick jr", "nicktoons", "disney", "boomerang",
         "spacetoon", "mbc 3", "majid", "dreamworks", "baby tv", "babytv",
         "kika", "gulli", "clan", "baraem", "jeem", "cbeebies", "cbbc",
         "semsem", "toggolino", "super rtl", "toggo", "duck tv", "cartoonito",
         "teletoon", "tvp abc", "minimini", "top kids", "junior",
         "toon", "animax", "anime",
         "toyor al janah", "toyor baby", "karameesh", "kooki kids",
         "sanabel kids", "rotana kids",
         "rai yoyo", "rai gulp", "boing", "frisbee",
         "dea kids", "dea junior", "super!",
         "piwi+", "canal j", "tiji", "canal+ kids",
         "4fun kids", "pop", "tiny pop", "pop max",
         "trt cocuk", "minika", "zarok tv",
         "sky kids", "ric tv", "teennick"],
        ["animation", "anime", "sponge", "patrol", "tom and jerry", "princess", "lego", "toon",
         "kids", "tales", "dragon", "pokemon", "peppa", "bluey", "paw patrol",
         "كرتون", "رسوم متحركة", "اطفال", "مغامرات", "ابطال", "براعم",
         "animasyon", "cizgi", "cocuk", "cartoni", "dibujos"]),

    "Music": (0xFF69B4,
        ["music", "mtv ", "mtv live", "mtv hits", "mtv 80s", "mtv 90s", "club mtv",
         "vh1", "melody", "mazzika", "rotana clip", "rotana mousica",
         "wanasah", "aghani", "arabica tv",
         "4fun", "eska", "polo tv", "disco polo",
         "mezzo", "trace", "box hits", "kerrang", "magic",
         "nrj", "cstar",
         "radio italia", "rtl 102.5", "radio freccia", "radio zeta",
         "radio kiss kiss", "radio norba", "deejay tv",
         "kral tv", "kral pop", "power tv", "power turk",
         "dream tv", "dream turk", "number one tv",
         "trt muzik", "alfa fann", "alfa music",
         "grand tv", "pink folk", "pink music", "dm sat", "cmc",
         "now 70s", "now 80s", "now 90s", "now rock", "clubland",
         "sol musica", "deluxe music", "schlager deluxe",
         "hawas", "free tv"],
        ["concert", "videoclip", "hits", "playlist", "songs", "top 10", "top 20",
         "live performance", "feat.", "remix", "unplugged",
         "حفل", "اغاني", "كليب", "طرب", "جلسات", "موسيقى", "فيديو كليب",
         "konser", "sarki", "klip", "muzik", "musica", "konzert"]),

    "Documentary": (0x800080,
        ["bbc earth", "discovery", "nat geo", "national geographic",
         "history", "animal planet", "wild", "planet",
         "science", "investigation", "arte", "geographic",
         "explorer", "viasat", "quest",
         "al jazeera doc", "dw doc", "fatafeat", "travel",
         "dmax", "motor trend", "ushuaia",
         "planete", "rmc decouverte", "rmc story", "focus",
         "nasa", "space", "eden",
         "sky documentaries", "sky nature", "sky history", "sky arte",
         "bbc four", "bbc two", "france 5",
         "rai 5", "rai storia", "rai scuola", "zdfinfo", "ard-alpha",
         "5select", "more4", "u&yesterday",
         "true crime", "crime+investigation",
         "odisea", "canal historia",
         "trt belgesel", "yaban tv",
         "histoire tv", "toute l'histoire", "science & vie"],
        ["documentary", "wildlife", "expedition", "universe", "factory", "engineering", "survival",
         "ancient", "nature", "safari", "space", "science", "world war",
         "archaeology", "civilization", "discovery",
         "وثائقي", "عالم الحيوان", "براري", "كواكب", "اسرار", "استكشاف", "تاريخ", "حضارة",
         "belgesel", "doku", "documentario", "documentaire"]),

    "Religious": (0xFFFFFF,
        ["quran", "sunnah", "iqraa", "resalah", "majd", "miracle", "ctv coptic", "mesat", "aghapy",
         "noursat", "god tv", "ewtn", "peace tv", "huda", "al nas", "al rahama", "al insan", "karbala",
         "al kafeel", "al maaref", "al kawthar", "al majarrah", "al nadah", "al fath", "nour",
         "catholic", "islam channel", "church", "holy",
         "tv2000", "padre pio", "telepace", "kto", "tbn", "daystar",
         "bibel tv", "k-tv", "hope tv", "revelation tv",
         "diyanet", "semerkand", "lalegul", "hilal tv", "rehber tv",
         "al hayat christian", "al horreya", "al karma", "koogi",
         "faith world", "british muslim", "ahlulbayt",
         "noor dubai", "al nahar noor", "al safwa"],
        ["prayer", "mass", "worship", "gospel", "recitation", "bible", "quran", "sheikh", "church",
         "khutbah", "sermon", "psalm", "liturgy", "rosary",
         "القران", "صلاة", "خطبة", "دعاء", "حديث", "تفسير", "ابتهالات", "اذكار", "فتاوى", "تلاوة", "قداس",
         "namaz", "dua", "vaaz", "kuran", "preghiera", "messe", "gottesdienst", "misa"]),
    "General": (0xA0A0A0, [], [])
}

CATEGORIES_ORDER = ["News", "Sports", "Movies", "Series", "Kids", "Music", "Documentary", "Religious", "General"]
DETECTION_PRIORITY = ["Kids", "Sports", "Documentary", "Religious", "Music", "News", "Movies", "Series"]

# --- LRU CACHE ---
class LRU(OrderedDict):
    def __init__(self, cap=1000):
        super().__init__()
        self.cap = cap

    def get(self, k, default=None):
        if k in self:
            self.move_to_end(k)
            return self[k]
        return default

    def put(self, k, v):
        OrderedDict.__setitem__(self, k, v)
        self.move_to_end(k)
        while len(self) > self.cap:
            self.popitem(last=False)

    def __setitem__(self, k, v):
        self.put(k, v)

# --- DUAL TUPLE / DICT EVENT ITEM ---
class WTWEventItem(tuple):
    def __new__(cls, cat, name, sat, evt, ref, start, dur, desc=""):
        return super(WTWEventItem, cls).__new__(cls, (cat, name, sat, evt, ref, start, dur, desc))

    def __getitem__(self, key):
        if isinstance(key, str):
            key_map = {
                "cat": 0, "name": 1, "sat": 2, "evt": 3,
                "ref": 4, "start": 5, "dur": 6, "desc": 7, "nib": 0
            }
            if key in key_map:
                return super().__getitem__(key_map[key])
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

# --- GLOBAL HELPERS & CACHES ---
PICON_CACHE = LRU(600)
CLASSIFICATION_CACHE = LRU(4000)
TRANSLATE_CACHE = LRU(300)
USER_OVERRIDES = {}      # channel name (lowercase) -> category, set from the Options menu
FOLLOWED = []            # keywords that create reminders automatically
PINNED_CHANNELS = []
WATCHLIST = []
GLOBAL_SERVICE_LIST = []
_ACTIVE_PICON_PATHS = None

# --- UI SCALE (layout is designed at 1080p and scaled to the real desktop) ---
_UI_SCALE = None

def ui_scale():
    global _UI_SCALE
    if _UI_SCALE is None:
        try:
            h = int(getDesktop(0).size().height())
        except Exception:
            h = 1080
        _UI_SCALE = max(0.6, min(2.0, h / 1080.0))
    return _UI_SCALE

def _s(v):
    return int(round(v * ui_scale()))

def _p(x, y):
    return f"{_s(x)},{_s(y)}"

# --- BACKGROUND HTTP (never blocks the Enigma2 main loop) ---
def _to_main(fn, *args):
    """Run fn on the Enigma2 main loop. Worker threads must never touch UI objects."""
    if reactor is not None:
        try:
            reactor.callFromThread(fn, *args)
            return
        except Exception:
            pass
    fn(*args)

def http_get_async(url, callback, timeout=8, allow_unverified=False):
    """Fetch url in a worker thread, then call callback(data_bytes or None, error_text or None)
    on the main loop."""
    def _fetch(ctx):
        req = _urlrequest.Request(url, headers={"User-Agent": "Mozilla/5.0 (WhatToWatch Enigma2)"})
        if ctx is not None:
            return _urlrequest.urlopen(req, timeout=timeout, context=ctx).read()
        return _urlrequest.urlopen(req, timeout=timeout).read()

    def _worker():
        data, err = None, None
        try:
            data = _fetch(None)
        except Exception as e:
            err = str(e) or e.__class__.__name__
            if allow_unverified and ("CERTIFICATE" in err.upper() or "SSL" in err.upper()):
                try:
                    data = _fetch(ssl._create_unverified_context())
                    err = None
                except Exception as e2:
                    err = str(e2) or e2.__class__.__name__
        _to_main(callback, data, err)

    t = threading.Thread(target=_worker)
    t.daemon = True
    t.start()

def translate_async(text, callback, target_lang='en'):
    """callback(translated_text). Falls back to the original text on any failure."""
    if not text:
        callback("")
        return
    key = (text, target_lang)
    cached = TRANSLATE_CACHE.get(key)
    if cached is not None:
        callback(cached)
        return
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=%s&dt=t&q=%s"
           % (target_lang, quote(text[:1800])))

    def _done(data, err):
        out = text
        if data:
            try:
                parsed = json.loads(data.decode("utf-8", "replace"))
                joined = "".join(seg[0] for seg in (parsed[0] or []) if seg and seg[0])
                if joined:
                    out = joined
                    TRANSLATE_CACHE.put(key, out)
            except Exception:
                pass
        callback(out)

    # Translation text is not code, so an image with a stale CA bundle may fall back to unverified TLS.
    http_get_async(url, _done, timeout=6, allow_unverified=True)

def translate_text(text, target_lang='en'):
    """Kept for compatibility: returns a cached translation or the original text. Never blocks."""
    cached = TRANSLATE_CACHE.get((text, target_lang))
    return cached if cached is not None else (text or "")

def play_chime(volume=0.8):
    if not os.path.exists(SOUND_FILE):
        return
    try:
        subprocess.Popen(
            ["gst-launch-1.0", "playbin", "uri=file://" + SOUND_FILE, "audio-sink=alsasink", "volume=%s" % volume],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True
        )
    except Exception:
        pass

def _get_active_picon_paths():
    global _ACTIVE_PICON_PATHS
    if _ACTIVE_PICON_PATHS is None or len(_ACTIVE_PICON_PATHS) != len(PICON_PATHS):
        _ACTIVE_PICON_PATHS = [p for p in PICON_PATHS if os.path.isdir(p)]
    return _ACTIVE_PICON_PATHS


def get_header_image_path():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "header.png") if '__file__' in globals() else "",
        "/usr/lib/enigma2/python/Plugins/Extensions/WhatToWatch/header.png",
        "/usr/lib/enigma2/python/Plugins/Extensions/WhattoWhatch/header.png",
        "header.png",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""


def _atomic_json_write(filepath, data):
    tmp = f"{filepath}.tmp.{os.getpid()}"
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(filepath):
            os.replace(tmp, filepath)
        else:
            os.rename(tmp, filepath)
        return True
    except Exception:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


def _safe_json_read(filepath, default=None):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_json_as(filepath, kind):
    data = _safe_json_read(filepath, None)
    return data if isinstance(data, kind) else kind()

def load_data():
    global PINNED_CHANNELS, WATCHLIST, USER_OVERRIDES, FOLLOWED
    PINNED_CHANNELS = [x for x in _load_json_as(PINNED_FILE, list) if isinstance(x, str)]
    WATCHLIST = [x for x in _load_json_as(WATCHLIST_FILE, list) if isinstance(x, dict) and x.get('ref')]
    USER_OVERRIDES = dict(
        (str(k).strip().lower(), v) for k, v in _load_json_as(OVERRIDES_FILE, dict).items()
        if v in CATEGORIES_DATA
    )
    FOLLOWED = [str(x).strip() for x in _load_json_as(FOLLOW_FILE, list) if str(x).strip()]

def save_pinned():
    _atomic_json_write(PINNED_FILE, PINNED_CHANNELS)

def save_watchlist():
    _atomic_json_write(WATCHLIST_FILE, WATCHLIST)

def save_overrides():
    _atomic_json_write(OVERRIDES_FILE, USER_OVERRIDES)

def save_followed():
    _atomic_json_write(FOLLOW_FILE, FOLLOWED)

load_data()

def toggle_pin(ref):
    if ref in PINNED_CHANNELS:
        PINNED_CHANNELS.remove(ref)
        res = "Unpinned"
    else:
        PINNED_CHANNELS.append(ref)
        res = "Pinned (Top)"
    save_pinned()
    return res

def set_channel_override(channel_name, category):
    """category=None removes the override. Returns True when something changed."""
    key = str(channel_name or "").strip().lower()
    if not key:
        return False
    if category:
        USER_OVERRIDES[key] = category
    elif key in USER_OVERRIDES:
        del USER_OVERRIDES[key]
    else:
        return False
    save_overrides()
    clear_classification_caches()
    return True

# --- REMINDERS ---
def find_reminder(ref, start_time):
    for w in WATCHLIST:
        if w.get('ref') == ref and w.get('start_time') == start_time:
            return w
    return None

def default_lead_time():
    try:
        return int(config.plugins.WhatToWatch.default_lead_time.value)
    except Exception:
        return 0

def add_reminder_entry(item, type_code="notify", lead=0, auto_keyword=None):
    """item is a WTWEventItem / 7+ tuple. Returns the stored entry."""
    entry = {
        "ref": item[4],
        "name": item[1],
        "evt": item[3],
        "start_time": int(item[5]),
        "notify_at": int(item[5]) - int(lead or 0),
        "type": type_code,
        "repeat": (type_code == "notify_week")
    }
    if auto_keyword:
        entry["auto"] = auto_keyword
    WATCHLIST.append(entry)
    return entry

def reminder_choices():
    lead = default_lead_time()
    opts = [
        ("Notification at start", ("notify", 0)),
        ("Notification 5 min before", ("notify", 300)),
        ("Notification 15 min before", ("notify", 900)),
        ("Notification 30 min before", ("notify", 1800)),
    ]
    opts.sort(key=lambda o: 0 if o[1][1] == lead else 1)   # the user's default lead time comes first
    opts.append(("Auto-Tune at start", ("zap", 0)))
    opts.append(("Weekly repeat reminder", ("notify_week", lead)))
    return opts

def fmt_duration(seconds):
    seconds = max(0, int(seconds))
    h, m = seconds // 3600, (seconds % 3600) // 60
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{max(1, m)} min"

# --- EPG ACCESS ---
def fetch_event(ref, start_time=0, duration=0):
    """Return the eServiceEvent for a list row (needed for descriptions, genre and recording)."""
    epg = eEPGCache.getInstance()
    if not epg or not ref:
        return None
    t = -1
    if start_time:
        t = int(start_time) + max(30, min(int(duration or 0) // 2, 600))
    for r in get_epg_refs(ref):
        try:
            ev = epg.lookupEventTime(eServiceReference(r), t)
            if ev and ev.getEventName():
                return ev
        except Exception:
            continue
    return None

def epg_search(query, limit=200, future_only=True):
    """Title search across the whole EPG cache. Returns WTWEventItems sorted by start time."""
    epg = eEPGCache.getInstance()
    query = str(query or "").strip()
    if not epg or not query:
        return []
    variants = [query]
    nq = _norm(query)
    if nq and nq != query:
        variants.append(nq)
    mode = getattr(eEPGCache, "PARTIAL_TITLE_SEARCH", 2)
    rows, seen = [], set()
    for q in variants:
        try:
            res = epg.search(("RIBDTSN", limit, mode, q, 1)) or []
        except Exception:
            res = []
        for row in res:
            try:
                key = (str(row[0]), row[1])
            except Exception:
                continue
            if key not in seen:
                seen.add(key)
                rows.append(row)
    now = int(time.time())
    out = []
    for row in rows:
        try:
            s_ref, evt_id, begin_t, dur, title, short_desc, s_name = row[:7]
            title, s_name, s_ref = str(title or ""), str(s_name or ""), str(s_ref or "")
            begin_t, dur = int(begin_t or 0), int(dur or 0)
            if not title or (future_only and begin_t + dur <= now):
                continue
            cat = classify_enhanced(s_name, title)
            if not cat:
                continue
            out.append(WTWEventItem(cat, s_name, get_sat_position(s_ref), title, s_ref, begin_t, dur, str(short_desc or "")))
        except Exception:
            continue
    out.sort(key=lambda x: (x[5], x[1].lower()))
    return out

# --- RECORDING ---
def record_event(session, item):
    """Create a real record timer for a list row. Returns (ok, message)."""
    if not HAVE_RECORDTIMER:
        return (False, "Record timers are not available on this image.")
    ev = fetch_event(item[4], item[5], item[6])
    if not ev:
        return (False, "No EPG data for this programme, so a timer cannot be created.")
    try:
        parsed = parseEvent(ev)
        begin, end, name, description, eit = parsed[:5]
        entry = RecordTimerEntry(ServiceReference(eServiceReference(item[4])), begin, end, name, description, eit)
        conflicts = session.nav.RecordTimer.record(entry)
    except Exception as e:
        return (False, f"Could not create the timer: {e}")
    if conflicts:
        names = ", ".join(str(getattr(c, "name", "?")) for c in conflicts[:3] if c is not entry)
        return (False, "Timer conflict" + (f" with: {names}" if names else "") + ".\nNothing was recorded.")
    return (True, f"Recording scheduled:\n{item[3]}\n{item[1]} • {time.strftime('%a %H:%M', time.localtime(item[5]))}")

# --- OVERLAYS (toasts and reminders that never take the remote control away) ---
_OVERLAYS = {}

def show_overlay(kind, session, screen_class, *args, **kwargs):
    """Show screen_class as a non-modal overlay: it does not get key focus, so OK / EXIT / zapping
    keep working underneath. One overlay per kind; the previous one is disposed first."""
    old = _OVERLAYS.pop(kind, None)
    if old is not None:
        try:
            old.hide()
            session.deleteDialog(old)
        except Exception:
            pass
    try:
        dlg = session.instantiateDialog(screen_class, *args, **kwargs)
        dlg.show()
        _OVERLAYS[kind] = dlg
        return dlg
    except Exception:
        try:
            kwargs["modal"] = True
            return session.open(screen_class, *args, **kwargs)
        except Exception:
            return None


def _make_picon_entry(pos, size, png):
    if not png:
        return MultiContentEntryText(pos=(0, 0), size=(0, 0), text="")
    try:
        return MultiContentEntryPixmapAlphaTest(pos=pos, size=size, png=png, flags=PICON_SCALE_FLAGS)
    except Exception:
        try:
            return MultiContentEntryPixmapAlphaTest(pos=pos, size=size, png=png)
        except Exception:
            return MultiContentEntryText(pos=(0, 0), size=(0, 0), text="")


def get_picon_resized(service_ref, channel_name, width=50, height=30):
    channel_name = str(channel_name or "")
    ref_clean = str(service_ref or "").strip().replace(":", "_").rstrip("_")
    cache_key = f"{ref_clean}_{width}_{height}"
    cached = PICON_CACHE.get(cache_key)
    if cached is not None:
        if cached is False:
            return None
        return cached
    
    found_path = None
    candidates = [
        ref_clean + ".png",
        ref_clean.lower() + ".png",
        ref_clean.replace("1_0_19", "1_0_1") + ".png",
        ref_clean.lower().replace("1_0_19", "1_0_1") + ".png",
        ref_clean.replace("4097_0_", "1_0_") + ".png",
        channel_name.strip() + ".png",
        channel_name.strip().lower() + ".png",
        # picons-by-name sets: "beIN Sports 1 HD" -> beinsports1hd.png
        re.sub(r'[^a-z0-9]', '', channel_name.lower().replace("+", "plus").replace("&", "and")) + ".png"
    ]
    parts = ref_clean.split("_")
    if len(parts) > 10:
        candidates.append("_".join(parts[:10]) + ".png")

    active = _get_active_picon_paths()
    for path in active:
        for name in candidates:
            full_path = os.path.join(path, name)
            if os.path.exists(full_path):
                found_path = full_path
                break
        if found_path:
            break
    
    if found_path:
        # 1. ePicLoad primary path — properly rescales to requested width x height
        try:
            sc = ePicLoad()
            sc.setPara((width, height, 1, 1, False, 1, "#00000000"))
            if sc.startDecode(found_path, 0, 0, False) == 0:
                ptr = sc.getData()
                if ptr:
                    PICON_CACHE.put(cache_key, ptr)
                    return ptr
        except Exception:
            pass
        # 2. loadPNG fallback — loads at native size (caller must handle scaling)
        try:
            px = loadPNG(found_path)
            if px:
                PICON_CACHE.put(cache_key, px)
                return px
        except Exception:
            pass
    
    PICON_CACHE.put(cache_key, False)
    return None


get_picon_cached = get_picon_resized

def _norm(text):
    if not text:
        return ""
    n = normalize_arabic(str(text).lower()).strip()
    for a, b in _ACCENT_MAP.items():
        if a in n:
            n = n.replace(a, b)
    return n

def _matches(text, pattern):
    p = str(pattern or "").strip().lower()
    t = str(text or "").strip().lower()
    if not p or not t:
        return False
    regex = r'(?<![a-zA-Z0-9])' + re.escape(p) + r'(?![a-zA-Z0-9])'
    return bool(re.search(regex, t))

def _cfg(name, default=True):
    try:
        return getattr(config.plugins.WhatToWatch, name).value
    except Exception:
        return default

# --- KEYWORD ENGINE (pre-compiled, word-boundary aware) ---
# Stems that are safe to match anywhere inside a CHANNEL name ("Eurosport", "Sportitalia", "Kinowelt").
_KW_STEMS = frozenset(["sport", "cinema", "movie", "kino", "aflam", "news", "music", "cartoon", "quran", "drama"])

# Extra raw patterns for event titles that a plain keyword cannot express.
_EVT_EXTRA = {
    "Series": [
        r'(?<![a-z0-9])s[0-9]{1,2}\s?e[0-9]{1,3}(?![0-9])',
        r'(?<![a-z])(?:ep|episode|folge|bolum|odcinek|حلقه)\.?\s?[0-9]{1,4}(?![0-9])'
    ]
}

def _kw_pattern(kw, allow_stem):
    k = _norm(kw).strip()
    if not k:
        return None
    esc = re.escape(k)
    if allow_stem and k in _KW_STEMS:
        return esc
    first, last = k[0], k[-1]
    left = r'(?<![a-z0-9])' if (first.isascii() and first.isalnum()) else ''
    if last.isascii() and last.isdigit():
        right = r'(?![a-z0-9])'
    elif last.isascii() and last.isalpha():
        right = r's?(?![a-z])'
    else:
        right = ''
    return left + esc + right

def _compile_keywords(keywords, allow_stem, extra=None):
    alts = []
    for kw in sorted(set(keywords), key=lambda x: -len(x)):
        p = _kw_pattern(kw, allow_stem)
        if p:
            alts.append(p)
    alts.extend(extra or [])
    return re.compile("|".join(alts)) if alts else None

_CHAN_RX = {}
_EVT_RX = {}
for _cat in DETECTION_PRIORITY:
    _CHAN_RX[_cat] = _compile_keywords(CATEGORIES_DATA[_cat][1], True)
    _EVT_RX[_cat] = _compile_keywords(CATEGORIES_DATA[_cat][2], False, _EVT_EXTRA.get(_cat))

def _best_category(rx_table, text):
    """Longest keyword wins; ties go to DETECTION_PRIORITY order."""
    best, best_len = None, 0
    if not text:
        return None
    for cat in DETECTION_PRIORITY:
        rx = rx_table.get(cat)
        if not rx:
            continue
        for m in rx.finditer(text):
            ln = m.end() - m.start()
            if ln > best_len:
                best, best_len = cat, ln
    return best

# --- DVB GENRE HELPERS ---
def genre_levels(g):
    """Return (level1, level2) content nibbles from whatever this image hands back:
    an eGenreData object, a list of them, a (l1, l2) tuple, an int, or an event."""
    try:
        if g is None or g == 0:
            return (0, 0)
        if hasattr(g, "getGenreData") and not hasattr(g, "getLevel1"):
            g = g.getGenreData()
            if g is None:
                return (0, 0)
        if hasattr(g, "getLevel1"):
            return (int(g.getLevel1()) & 0xF, int(g.getLevel2()) & 0xF)
        if isinstance(g, (tuple, list)):
            if not g:
                return (0, 0)
            if isinstance(g[0], (tuple, list)) or hasattr(g[0], "getLevel1"):
                return genre_levels(g[0])
            return (int(g[0]) & 0xF, (int(g[1]) & 0xF) if len(g) > 1 else 0)
        v = int(g)
        if v > 0xF:
            return ((v >> 4) & 0xF, v & 0xF)
        return (v & 0xF, 0)
    except Exception:
        return (0, 0)

_GENRE_MAP = {0x1: "Movies", 0x2: "News", 0x4: "Sports", 0x5: "Kids", 0x6: "Music", 0x9: "Documentary"}

# --- ADULT FILTER (three tiers) ---
# Tier 1: brand names, matched as whole words ("Max 1" is not "X1", "Fox Movies" is not "XMO").
_ADULT_BRANDS = [
    "private tv", "private hd", "private gold", "private spice", "private class", "private lounge",
    "hustler", "blue hustler", "brazzers", "dorcel", "redlight", "red light", "sct", "teleitalia",
    "dxtv", "vivid", "penthouse", "playboy", "pinko", "pink o", "passion xxx", "centoxcento",
    "evil angel", "babes tv", "pure babes", "daring tv", "man x", "leo tv",
    "extasy", "exstasy", "ecstasy",
    "super one", "vixen", "blacked", "tushy", "erox", "eroxxx", "french lover",
    "free x tv", "freex", "xmo", "x dream", "television x", "tvx", "babestation", "studio 66",
    "beate uhse", "jasmin tv", "candy tv", "barely legal", "blue movie", "venus", "exotic tv",
    "secret circle", "flash tv", "x plus", "pornhub", "youporn", "xvideos", "bang bros",
    "naughty america", "reality kings", "sexto senso", "hot pleasure", "hot club", "dusk tv",
    "stars xxx", "sexy sat", "diablo tv"
]
_ADULT_BRAND_RX = re.compile(
    r'(?<![a-z0-9])(?:' + "|".join(
        r'\s*'.join(re.escape(tok) for tok in b.split())
        for b in sorted(_ADULT_BRANDS, key=lambda x: -len(x))
    ) + r')(?![a-z])'
)
_ADULT_XNAME_RX = re.compile(r'^(x{1,4}[0-9]{0,2}|private)$')
# Tier 2: explicit words. Enough on their own in a channel name.
_ADULT_STRONG_RX = re.compile(
    r'xxx|18\s?\+|\+\s?18|(?<![a-z])(?:porn|porno|erotic|erotica|erotik|hardcore|striptease|escort|sex|sexy|babe|babes|uncensored|adults? only)(?![a-z])'
    r'|(?<![a-z])adult(?![a-z])(?! swim)'
)
# Tier 3: ordinary words. Never enough alone; two of them together in a channel name are.
_ADULT_WEAK_RX = re.compile(r'(?<![a-z])(?:hot|club|night|girls|lovers|naughty)(?![a-z])')
# Event titles: explicit markers only. "Saturday Night Live" and "Powerpuff Girls" are not adult.
_ADULT_EVENT_RX = re.compile(r'xxx|18\s?\+|\+\s?18|(?<![a-z])(?:porn|porno|erotic|erotica|erotik|adults? only)(?![a-z])')

_ADULT_CHANNEL_CACHE = LRU(8000)

def _is_adult_channel(channel_name):
    key = str(channel_name or "")
    hit = _ADULT_CHANNEL_CACHE.get(key)
    if hit is not None:
        return hit
    ch = _norm(key)
    for sep in ("-", "_", ".", "/", "|"):
        ch = ch.replace(sep, " ")
    ch = " ".join(ch.split())
    bare = _STRIP_QUALITY.sub(" ", ch)
    bare = "".join(_STRIP_TV.sub(" ", bare).split())
    res = False
    if _ADULT_XNAME_RX.match(bare):
        res = True
    elif _ADULT_BRAND_RX.search(ch):
        res = True
    elif _ADULT_STRONG_RX.search(ch):
        res = True
    elif len(set(_ADULT_WEAK_RX.findall(ch))) >= 2:
        res = True
    _ADULT_CHANNEL_CACHE.put(key, res)
    return res

def is_adult_content(channel_name, event_name="", genre_nib=0):
    if not _cfg("adult_filter", True):
        return False
    l1, l2 = genre_levels(genre_nib)
    if l1 == 0x1 and l2 == 0x8:      # DVB content descriptor 0x18: adult movie/drama
        return True
    if _is_adult_channel(channel_name):
        return True
    if event_name and _ADULT_EVENT_RX.search(_norm(event_name)):
        return True
    return False

# --- CLASSIFIER ---
_ADULT = "\x00adult"            # cache sentinel (None cannot be cached)
_CHANNEL_CAT_CACHE = LRU(8000)  # channel name -> (database category, channel keyword category)

def _channel_categories(channel_name):
    key = str(channel_name or "")
    hit = _CHANNEL_CAT_CACHE.get(key)
    if hit is None:
        db_cat = lookup_channel_category(key)
        kw_cat = None if db_cat else _best_category(_CHAN_RX, _norm(key))
        hit = (db_cat, kw_cat)
        _CHANNEL_CAT_CACHE.put(key, hit)
    return hit

def clear_classification_caches():
    CLASSIFICATION_CACHE.clear()
    _CHANNEL_CAT_CACHE.clear()
    _ADULT_CHANNEL_CACHE.clear()

def classify_enhanced(channel_name, event_name="", genre_nib=0, **kwargs):
    """Returns a category name, or None when the adult filter hides the entry."""
    l1, l2 = genre_levels(genre_nib or kwargs.get("genre_nibble", 0))
    ch_raw = str(channel_name or "").strip()
    if USER_OVERRIDES:
        ov = USER_OVERRIDES.get(ch_raw.lower())
        if ov:
            return ov

    cache_key = (ch_raw, event_name or "", l1, l2)
    cached = CLASSIFICATION_CACHE.get(cache_key)
    if cached is not None:
        return None if cached == _ADULT else cached

    if is_adult_content(ch_raw, event_name, genre_nib=(l1, l2)):
        CLASSIFICATION_CACHE.put(cache_key, _ADULT)
        return None

    res = None
    db_cat, kw_cat = _channel_categories(ch_raw)
    evt_clean = _norm(event_name) if event_name else ""

    # 1. Dedicated channel from the database
    if db_cat and db_cat != "General":
        res = db_cat
    # 2. Broadcaster DVB genre. Many muxes flag every drama as 0x1 "movie/drama",
    #    so a title that reads like an episode stays a series.
    if not res and l1 in _GENRE_MAP and _cfg("use_dvb_genre", True):
        res = _GENRE_MAP[l1]
        if l1 == 0x1 and evt_clean and _EVT_RX["Series"] and _EVT_RX["Series"].search(evt_clean):
            res = "Series"
    # 3. Channel-name keywords (unknown channels only; a database "General" channel is mixed by definition)
    if not res and kw_cat:
        res = kw_cat
    # 4. Event-title keywords
    if not res and evt_clean:
        res = _best_category(_EVT_RX, evt_clean)
    if not res:
        res = "General"
    CLASSIFICATION_CACHE.put(cache_key, res)
    return res

classify_channel_and_event = classify_enhanced

def get_epg_refs(s_ref):
    """Service references worth asking the EPG cache about, cheapest first.
    The EPG is keyed on sid/tsid/onid/namespace, so a DVB reference needs no variants;
    an IPTV reference (4097/5001/5002...) is tried as its 1:0:1 twin first."""
    if not s_ref:
        return []
    clean = str(s_ref).strip()
    if clean.startswith("1:0:"):
        return [clean]
    parts = clean.split(":")
    if len(parts) >= 10:
        return ["1:0:1:" + ":".join(parts[3:10]) + ":", clean]
    return [clean]

def _ref_key(ref):
    return ":".join(str(ref or "").split(":")[:10]).upper()


def get_sat_position(ref_str):
    if not ref_str:
        return ""
    clean = str(ref_str)
    if clean.startswith("4097:") or clean.startswith("5001:") or "http" in clean:
        return "IPTV"
    try:
        parts = clean.split(":")
        if len(parts) > 6 and parts[6]:
            ns_val = int(parts[6], 16)
            high_word = (ns_val >> 16) & 0xFFFF
            if high_word in (0xFFFF, 0xEEEE):
                return "DVB-T/C"
            # In Enigma2 dvb_namespace, bits 28-31 are system/transponder flags.
            # Orbital position in tenths of a degree is stored in bits 16-27 (12 bits: 0-3600).
            orb_pos = (ns_val >> 16) & 0x0FFF
            if orb_pos == 0:
                low_pos = ns_val & 0x0FFF
                if low_pos in (130, 192, 160, 70, 260, 282, 420):
                    orb_pos = low_pos
                else:
                    return ""
            if orb_pos > 1800:
                return f"{(3600 - orb_pos)/10.0:.1f}W"
            else:
                return f"{orb_pos/10.0:.1f}E"
    except Exception:
        pass
    return ""


# --- SELF-UPDATE (verified download, atomic swap, rollback copy) ---
def version_tuple(v):
    try:
        return tuple(int(x) for x in re.findall(r'\d+', str(v))[:4]) or (0,)
    except Exception:
        return (0,)

def verify_update_payload(data, current_version=None):
    """Checks a downloaded plugin.py before it is allowed anywhere near the plugin folder.
    Returns (ok, message, new_version)."""
    if not data or len(data) < 20000:
        return (False, "Download incomplete (file too small).", None)
    try:
        text = data.decode("utf-8")
    except Exception:
        return (False, "Downloaded file is not valid UTF-8 text.", None)
    if "WhatToWatch" not in text or "def Plugins(" not in text:
        return (False, "Downloaded file is not the What to Watch plugin.", None)
    m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    new_ver = m.group(1) if m else None
    if not new_ver:
        return (False, "Downloaded file has no version number.", None)
    if version_tuple(new_ver) <= version_tuple(current_version or VERSION):
        return (False, f"Downloaded file is v{new_ver}, not newer than v{current_version or VERSION}.", new_ver)
    try:
        compile(text, "plugin.py", "exec")
    except Exception as e:
        return (False, f"Downloaded file does not compile on this image: {e}", new_ver)
    return (True, "ok", new_ver)

def install_update_payload(data, plugin_dir=None):
    """Writes next to plugin.py, keeps plugin.py.bak, then swaps atomically. Returns (ok, message)."""
    plugin_dir = plugin_dir or PLUGIN_PATH
    target = os.path.join(plugin_dir, "plugin.py")
    tmp = target + ".new"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        if os.path.getsize(tmp) != len(data):
            raise IOError("short write (flash full?)")
        if os.path.exists(target):
            shutil.copy2(target, target + ".bak")
        os.replace(tmp, target)
    except Exception as e:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return (False, f"Could not install the update: {e}\nThe current version is untouched.")
    # Stale bytecode would keep the old version running after the restart.
    for stale in [target + "c", target + "o"] + glob.glob(os.path.join(plugin_dir, "__pycache__", "plugin.*.pyc")):
        try:
            os.remove(stale)
        except Exception:
            pass
    return (True, "Update installed. Restart the GUI to apply.\nThe previous version was kept as plugin.py.bak.")


# --- DISCOVERY TOAST ---
class DiscoveryToast(Screen):
    skin = """
        <screen position="30,30" size="580,130" title="Discovery" flags="wfNoBorder" backgroundColor="#00000000" zPosition="100">
            <eLabel position="0,0" size="580,130" backgroundColor="#10101520" zPosition="100" />
            <eLabel position="0,0" size="6,130" backgroundColor="#00E5FF" zPosition="101" />
            <widget name="picon" position="18,35" size="60,36" scale="1" alphatest="on" transparent="1" zPosition="102" />
            <widget name="header" position="18,6" size="545,24" font="Regular;18" halign="left" foregroundColor="#CCCCCC" backgroundColor="#10101520" transparent="1" zPosition="102" />
            <widget name="channel" position="88,35" size="475,36" font="Regular;25" halign="left" foregroundColor="#FFD700" backgroundColor="#10101520" transparent="1" zPosition="102" />
            <widget name="event" position="18,78" size="545,44" font="Regular;21" halign="left" foregroundColor="#FFFFFF" backgroundColor="#10101520" transparent="1" zPosition="102" />
        </screen>
    """

    def __init__(self, session, mode, category, channel_name, event_name, start_time=None, sat_name=None, service_ref=None, raw_channel_name="", modal=False):
        if sat_name and f"({sat_name})" not in str(channel_name):
            display_ch = f"{channel_name} ({sat_name})"
        else:
            display_ch = str(channel_name)

        if mode == "now":
            accent = "#FF0000"
            header = f"NOW SHOWING • {category}"
            title_col = "#FFD700"
        elif mode == "next":
            accent = "#00FF00"
            t_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time else ""
            header = f"COMING NEXT • {t_str}"
            title_col = "#90EE90"
        elif mode == "tonight":
            accent = "#1E90FF"
            t_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time else ""
            header = f"TONIGHT • {t_str}"
            title_col = "#87CEFA"
        else:
            accent = "#00E5FF"
            header = f"DISCOVERY • {category}"
            title_col = "#FFFFFF"

        # Less transparent background (In Enigma2 ARGB, 00 is opaque, FF is transparent)
        try:
            trans_alpha = config.plugins.WhatToWatch.discovery_transparency.value
        except Exception:
            trans_alpha = "10"
        bg_hex = f"#{trans_alpha}101520"

        # Position calculation based on user setting
        try:
            pos_mode = config.plugins.WhatToWatch.discovery_position.value
        except Exception:
            pos_mode = "top_left"

        try:
            desk = getDesktop(0)
            dw = int(desk.size().width())
            dh = int(desk.size().height())
        except Exception:
            dw, dh = 1920, 1080
        tw, th = 580, 130

        if pos_mode == "top_right":
            x, y = dw - tw - 30, 30
        elif pos_mode == "bottom_left":
            x, y = 30, dh - th - 30
        elif pos_mode == "bottom_right":
            x, y = dw - tw - 30, dh - th - 30
        elif pos_mode == "top_center":
            x, y = (dw - tw) // 2, 30
        else: # top_left
            x, y = 30, 30

        # Picon detection and dynamic positioning
        clean_ch = str(raw_channel_name or channel_name)
        if "(" in clean_ch and clean_ch.endswith(")"):
            clean_ch = clean_ch[:clean_ch.rfind("(")].strip()

        self.picon_pixmap = get_picon_resized(service_ref, clean_ch, width=60, height=36)
        has_picon = self.picon_pixmap is not None

        if has_picon:
            picon_xml = '<widget name="picon" position="18,35" size="60,36" scale="1" alphatest="on" transparent="1" zPosition="102" />'
            ch_x, ch_w = 88, 475
        else:
            picon_xml = '<widget name="picon" position="0,0" size="0,0" scale="1" alphatest="on" transparent="1" zPosition="102" />'
            ch_x, ch_w = 18, 545

        # Set self.skin BEFORE calling Screen.__init__ so GUI widgets render reliably!
        self.skin = f"""
            <screen position="{x},{y}" size="{tw},{th}" title="Discovery" flags="wfNoBorder" backgroundColor="#00000000" zPosition="100">
                <eLabel position="0,0" size="{tw},{th}" backgroundColor="{bg_hex}" zPosition="100" />
                <eLabel position="0,0" size="6,{th}" backgroundColor="{accent}" zPosition="101" />
                <widget name="header" position="18,6" size="545,24" font="Regular;18" halign="left" foregroundColor="#CCCCCC" backgroundColor="{bg_hex}" transparent="1" zPosition="102" />
                {picon_xml}
                <widget name="channel" position="{ch_x},35" size="{ch_w},36" font="Regular;25" halign="left" foregroundColor="{title_col}" backgroundColor="{bg_hex}" transparent="1" zPosition="102" />
                <widget name="event" position="18,78" size="545,44" font="Regular;21" halign="left" foregroundColor="#FFFFFF" backgroundColor="{bg_hex}" transparent="1" zPosition="102" />
            </screen>
        """

        Screen.__init__(self, session)

        self["header"] = Label(header)
        self["picon"] = Pixmap()
        self["channel"] = Label(display_ch)
        self["event"] = Label(event_name)

        if has_picon and hasattr(self["picon"], "setPixmap"):
            try:
                self["picon"].setPixmap(self.picon_pixmap)
            except Exception:
                pass

        self.onLayoutFinish.append(self._apply_picon)

        # Shown through show_overlay(): no ActionMap, so the remote keeps working underneath.
        # Only the modal fallback takes keys, and then OK / EXIT close it.
        self._modal = modal
        if modal:
            self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close, "ok": self.close}, -1)
        self.timer = eTimer()
        self.timer.callback.append(self._expire)
        try:
            dur = int(config.plugins.WhatToWatch.discovery_duration.value)
        except Exception:
            dur = 8
        self.timer.start(dur * 1000, True)

    def _apply_picon(self):
        if self.picon_pixmap:
            try:
                inst = None
                if hasattr(self["picon"], "instance") and self["picon"].instance:
                    inst = self["picon"].instance
                    # Enable widget-level scaling so picon fits the 60x36 bounds
                    try:
                        inst.setScale(2)  # 2 = BT_SCALE | BT_KEEP_ASPECT_RATIO
                    except Exception:
                        try:
                            inst.setScale(1)  # 1 = BT_SCALE only
                        except Exception:
                            pass
                    inst.setPixmap(self.picon_pixmap)
                elif hasattr(self["picon"], "setPixmap"):
                    self["picon"].setPixmap(self.picon_pixmap)
                self["picon"].show()
            except Exception:
                pass
        else:
            try:
                self["picon"].hide()
            except Exception:
                pass

    def _expire(self):
        if self._modal:
            self.close()
        else:
            self.hide()


# --- NOTIFICATIONS ---
class WTWNotification(Screen):
    skin = """
        <screen position="center,30" size="1000,100" title="Reminder" flags="wfNoBorder" backgroundColor="#40000000" zPosition="100">
            <eLabel position="0,0" size="1000,100" backgroundColor="#20101010" zPosition="-1" />
            <eLabel text="!" position="20,20" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="#FFFF00" backgroundColor="#20101010" transparent="1" />
            <widget name="message" position="100,10" size="880,80" font="Regular;28" valign="center" halign="left" foregroundColor="#FFFFFF" backgroundColor="#20101010" transparent="1" />
        </screen>
    """
    def __init__(self, session, message, timeout=5, modal=False):
        Screen.__init__(self, session)
        self["message"] = Label(message)
        self._modal = modal
        if modal:
            self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close, "ok": self.close}, -1)
        self.timer = eTimer()
        self.timer.callback.append(self._expire)
        self.timer.start(timeout * 1000, True)

    def _expire(self):
        if self._modal:
            self.close()
        else:
            self.hide()


def is_menu_or_plugin_active(session):
    """
    Check if user is currently inside any menu, channel list, setup screen,
    or plugin, so background discovery toasts do not interrupt the user.
    Returns True if a menu/plugin screen is active, False if watching live TV / media.
    """
    if not session:
        return False

    cd = getattr(session, "current_dialog", None)
    if cd is None:
        # Full-screen live TV with no active modal or overlay dialog
        return False

    name = cd.__class__.__name__
    mod = getattr(cd.__class__, "__module__", "")

    # 1. Non-menu, live TV, or media playback screens
    if name == "DiscoveryToast":
        return False

    # Check if this is an InfoBar, media player, volume or other standard OSD widget
    live_tv_indicators = (
        "InfoBar", "MoviePlayer", "DVDPlayer", "MediaPlayer", "EMC", 
        "PVRState", "Timeshift", "Volume", "Mute", "UnhandledKey", "Subtitle"
    )
    if any(k in name for k in live_tv_indicators):
        return False

    # 2. Check if this is a plugin screen (e.g. Plugins.Extensions.*, Plugins.SystemPlugins.*)
    if mod.startswith("Plugins.") and name != "DiscoveryToast":
        return True

    # 3. Check if this is an Enigma2 menu, setup, channel list, EPG, or modal dialog
    menu_indicators = (
        "Menu", "Setup", "Config", "ChannelSelection", "Bouquet", 
        "EPG", "ChoiceBox", "MessageBox", "VirtualKeyBoard", "Wizard", "Browser"
    )
    if any(k in name for k in menu_indicators):
        return True

    # 4. Check if the screen explicitly declares itself modal
    if getattr(cd, "is_modal", False):
        return True

    # 5. Inspect dialog stack only for modal screens
    stack = getattr(session, "dialog_stack", None)
    if stack:
        for item in stack:
            dlg = item[0] if isinstance(item, (tuple, list)) else item
            is_modal = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else getattr(dlg, "is_modal", False)
            if dlg is None or not is_modal:
                continue
            d_name = dlg.__class__.__name__
            d_mod = getattr(dlg.__class__, "__module__", "")
            if d_name == "DiscoveryToast":
                continue
            if d_mod.startswith("Plugins."):
                return True
            if any(k in d_name for k in menu_indicators):
                return True

    return False


# --- MONITOR ---
class WTWMonitor:
    FOLLOW_INTERVAL_MS = 30 * 60 * 1000   # how often followed keywords are re-checked against the EPG
    FOLLOW_HORIZON = 24 * 3600            # auto-reminders are created for the next 24 hours
    FOLLOW_MAX_PER_KEYWORD = 6

    def __init__(self, session):
        self.session = session
        self.timer = eTimer()
        self.timer.callback.append(self.check_reminders)
        self.timer.start(30000, False)

        self.discovery_timer = eTimer()
        self.discovery_timer.callback.append(self.discovery_tick)
        self.discovery_cat_idx = 0

        self.scan_timer = eTimer()
        self.scan_timer.callback.append(self.build_cache)
        self.scan_timer.start(5000, True)

        # Followed keywords: one keyword per step so a long list never stalls the box.
        self.follow_queue = []
        self.follow_added = 0
        self.follow_done_cb = None
        self.follow_timer = eTimer()
        self.follow_timer.callback.append(self.follow_scan)
        self.follow_step_timer = eTimer()
        self.follow_step_timer.callback.append(self._follow_step)
        self.follow_timer.start(90000, True)

        self.restart_discovery_timer()

    def restart_discovery_timer(self):
        self.discovery_timer.stop()
        if config.plugins.WhatToWatch.discovery_mode.value:
            try:
                mins = int(config.plugins.WhatToWatch.discovery_interval.value)
            except Exception:
                mins = 15
            self.discovery_timer.start(max(1, mins) * 60 * 1000, False)

    def build_cache(self):
        global GLOBAL_SERVICE_LIST
        try:
            service_handler = eServiceCenter.getInstance()
            ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
            bouquet_root = eServiceReference(ref_str)
            bouquet_list = service_handler.list(bouquet_root)
            if not bouquet_list:
                ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
                bouquet_root = eServiceReference(ref_str)
                bouquet_list = service_handler.list(bouquet_root)
                if not bouquet_list:
                    return

            bouquet_content = bouquet_list.getContent("SN", True)
            if not bouquet_content:
                ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
                bouquet_root = eServiceReference(ref_str)
                bouquet_list = service_handler.list(bouquet_root)
                if bouquet_list:
                    bouquet_content = bouquet_list.getContent("SN", True)
                if not bouquet_content:
                    return

            temp_list = []
            for bouquet_entry in bouquet_content:
                if not bouquet_entry or not bouquet_entry[0]:
                    continue
                services = service_handler.list(eServiceReference(bouquet_entry[0]))
                if services:
                    items = services.getContent("SN", True)
                    if items:
                        for it in items:
                            if it and it[0] and not str(it[0]).startswith("1:64:"):
                                temp_list.append(it)
                                if len(temp_list) > 6000:
                                    break
                elif not str(bouquet_entry[0]).startswith("1:64:"):
                    temp_list.append(bouquet_entry)
                if len(temp_list) > 6000:
                    break
            if temp_list:
                GLOBAL_SERVICE_LIST = temp_list
        except Exception:
            pass

    # ---------------------------------------------------------------- discovery
    def _discover(self, epg_cache, pool, mode, now, wanted, allowed, sat_filter):
        """One pass over a random pool. Returns the item for the wanted category, else any allowed one."""
        if mode == "next":
            q_time = now + 3600
        elif mode == "tonight":
            q_time = now + 14400
        else:
            q_time = -1
        spare = None
        for entry in pool:
            try:
                s_ref, s_name = str(entry[0]), str(entry[1])
                if "::" in s_ref or is_adult_content(s_name):
                    continue
                sat_pos = get_sat_position(s_ref)
                if sat_filter and sat_filter != "all" and not sat_matches(sat_pos, sat_filter):
                    continue
                event = None
                for r in get_epg_refs(s_ref):
                    event = epg_cache.lookupEventTime(eServiceReference(r), q_time)
                    if event:
                        break
                if not event:
                    continue
                event_name = event.getEventName()
                if not event_name:
                    continue
                cat = classify_enhanced(s_name, event_name, genre_nib=genre_levels(event))
                if not cat or cat not in allowed:
                    continue
                sat_short = get_sat_short_name(sat_pos)
                display_name = f"{s_name} ({sat_short})" if sat_short else s_name
                item = (mode, cat, display_name, event_name, event.getBeginTime(), s_ref, s_name)
                if cat == wanted:
                    return item
                if spare is None:
                    spare = item
            except Exception:
                continue
        return spare

    def discovery_tick(self):
        if not config.plugins.WhatToWatch.discovery_mode.value:
            self.discovery_timer.stop()
            return

        # Do not pop toast if user is navigating menus or in other plugins
        if is_menu_or_plugin_active(self.session):
            return

        if not GLOBAL_SERVICE_LIST:
            self.build_cache()
            if not GLOBAL_SERVICE_LIST:
                return

        epg_cache = eEPGCache.getInstance()
        if not epg_cache:
            return

        sat_filter = config.plugins.WhatToWatch.discovery_sat.value
        candidate_services = GLOBAL_SERVICE_LIST
        if sat_filter and sat_filter != "all":
            matched = [
                s for s in GLOBAL_SERVICE_LIST
                if s and s[0] and sat_matches(get_sat_position(str(s[0])), sat_filter)
            ]
            if matched:
                candidate_services = matched

        try:
            cat_pref = config.plugins.WhatToWatch.discovery_category.value
        except Exception:
            cat_pref = "all"
        if cat_pref and cat_pref != "all" and cat_pref in CATEGORIES_DATA:
            allowed = [cat_pref]
        else:
            allowed = list(CATEGORIES_ORDER)
        wanted = allowed[self.discovery_cat_idx % len(allowed)]
        self.discovery_cat_idx = (self.discovery_cat_idx + 1) % len(allowed)

        now = int(time.time())
        roll = random.randint(1, 10)
        mode = "now"
        if roll > 8:
            mode = "tonight" if time.localtime(now).tm_hour < 22 else "next"
        elif roll > 5:
            mode = "next"

        # A single bounded pass (at most 160 channels), instead of up to 16 x 50 lookups plus a retry of 120.
        pool = random.sample(candidate_services, min(160, len(candidate_services)))
        found_item = self._discover(epg_cache, pool, mode, now, wanted, allowed, sat_filter)
        if not found_item and mode != "now":
            found_item = self._discover(epg_cache, pool, "now", now, wanted, allowed, sat_filter)

        if found_item:
            if config.plugins.WhatToWatch.discovery_sound.value:
                play_chime(0.5)
            show_overlay(
                "toast", self.session, DiscoveryToast,
                found_item[0], found_item[1], found_item[2], found_item[3], found_item[4],
                service_ref=found_item[5], raw_channel_name=found_item[6]
            )

    # ---------------------------------------------------------------- reminders
    def check_reminders(self):
        now = int(time.time())
        dirty = False
        to_remove = []
        for item in list(WATCHLIST):
            start = int(item.get('start_time', 0) or 0)
            target = int(item.get('notify_at', start) or start)
            # Fire from the notify time until 5 minutes into the programme, so a reminder that came
            # due while the box was busy or just waking up is still delivered (marked as late).
            if target <= now < max(target + 120, start + 300):
                self.trigger_event(item, late=(now - start) if now > start + 90 else 0)
                if item.get('repeat', False):
                    item['start_time'] = start + 604800
                    item['notify_at'] = target + 604800
                    dirty = True
                else:
                    to_remove.append(item)
            elif now > start + 7200:
                if item.get('repeat', False):
                    # Box was off over the slot: roll the weekly reminder forward instead of losing it.
                    item['start_time'] = start
                    item['notify_at'] = target
                    while item['start_time'] + 300 < now:
                        item['start_time'] += 604800
                        item['notify_at'] += 604800
                    dirty = True
                else:
                    to_remove.append(item)
        for item in to_remove:
            if item in WATCHLIST:
                WATCHLIST.remove(item)
                dirty = True
        if dirty:
            save_watchlist()

    def trigger_event(self, item, late=0):
        play_chime(0.8)
        start = int(item.get('start_time', 0) or 0)
        now = int(time.time())
        if late:
            when = f"started {fmt_duration(late)} ago"
        elif start - now > 45:
            when = f"starts in {fmt_duration(start - now)}"
        else:
            when = "starting now"
        msg = f"{item.get('evt', '')}\n{item.get('name', '')} • {when}"
        if item.get('auto'):
            msg += f" • following \"{item['auto']}\""
        if item.get('type') == 'zap':
            show_overlay("notify", self.session, WTWNotification, msg + " • Auto-Tuning...", timeout=6)
            try:
                self.session.nav.playService(eServiceReference(item['ref']))
            except Exception:
                pass
        else:
            show_overlay("notify", self.session, WTWNotification, msg, timeout=10)

    # ---------------------------------------------------------------- followed keywords
    def follow_scan(self, done_cb=None):
        """Check every followed keyword against the EPG and create reminders for new matches."""
        self.follow_timer.stop()
        self.follow_timer.start(self.FOLLOW_INTERVAL_MS, True)
        self.follow_done_cb = done_cb
        self.follow_added = 0
        if not FOLLOWED or not _cfg("follow_enabled", True):
            self._follow_finish()
            return
        self.follow_queue = list(FOLLOWED)
        self.follow_step_timer.start(200, True)

    def _follow_step(self):
        if not self.follow_queue:
            self._follow_finish()
            return
        kw = self.follow_queue.pop(0)
        try:
            self.follow_added += self.follow_keyword(kw)
        except Exception:
            pass
        if self.follow_queue:
            self.follow_step_timer.start(1500, True)
        else:
            self._follow_finish()

    def _follow_finish(self):
        if self.follow_added:
            save_watchlist()
        cb, self.follow_done_cb = self.follow_done_cb, None
        if cb:
            try:
                cb(self.follow_added)
            except Exception:
                pass

    def follow_keyword(self, kw):
        """Returns how many reminders were created for one keyword."""
        now = int(time.time())
        lead = default_lead_time()
        have_ref = set((w.get('ref'), w.get('start_time')) for w in WATCHLIST)
        # The same programme usually sits on several channels / satellites at once:
        # one reminder per (title, start time) is enough.
        have_evt = set((str(w.get('evt', '')).lower(), w.get('start_time')) for w in WATCHLIST)
        existing = sum(1 for w in WATCHLIST if w.get('auto') == kw)
        pinned = set(PINNED_CHANNELS)
        matches = [
            it for it in epg_search(kw, limit=150)
            if now + 60 < it[5] <= now + self.FOLLOW_HORIZON
        ]
        matches.sort(key=lambda it: (it[5], 0 if it[4] in pinned else 1))
        added = 0
        for it in matches:
            if existing + added >= self.FOLLOW_MAX_PER_KEYWORD:
                break
            k_ref, k_evt = (it[4], it[5]), (it[3].lower(), it[5])
            if k_ref in have_ref or k_evt in have_evt:
                continue
            add_reminder_entry(it, "notify", lead, auto_keyword=kw)
            have_ref.add(k_ref)
            have_evt.add(k_evt)
            added += 1
        return added

def follow_add(keyword):
    kw = str(keyword or "").strip()
    if not kw or kw.lower() in [k.lower() for k in FOLLOWED]:
        return False
    FOLLOWED.append(kw)
    save_followed()
    return True

def follow_remove(keyword):
    """Stops following a keyword and drops the reminders it created."""
    kw = str(keyword or "").strip().lower()
    hit = [k for k in FOLLOWED if k.lower() == kw]
    if not hit:
        return False
    for k in hit:
        FOLLOWED.remove(k)
    save_followed()
    stale = [w for w in WATCHLIST if str(w.get('auto', '')).lower() == kw]
    for w in stale:
        WATCHLIST.remove(w)
    if stale:
        save_watchlist()
    return True

def is_followed(keyword):
    kw = str(keyword or "").strip().lower()
    return bool(kw) and kw in [k.lower() for k in FOLLOWED]

# --- LIST BUILDER ---
def setup_event_list(menulist):
    menulist.l.setFont(0, gFont("Regular", _s(24)))
    menulist.l.setFont(1, gFont("Regular", _s(20)))
    menulist.l.setFont(2, gFont("Regular", _s(18)))
    menulist.l.setFont(3, gFont("Regular", _s(15)))
    menulist.l.setItemHeight(_s(80))

def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, start_time, duration, short_desc="", *_extra):
    """Builds one row. Registered with setBuildFunc, so it only runs for rows that are on screen."""
    now = int(time.time())
    icon_pixmap = get_picon_resized(service_ref, channel_name, _s(50), _s(30))
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    end_str = time.strftime("- %H:%M", time.localtime(start_time + duration)) if (start_time > 0 and duration > 0) else ""

    display_name = f"{channel_name} ({sat_info})" if sat_info else channel_name
    is_pinned = service_ref in PINNED_CHANNELS
    reminder = find_reminder(service_ref, start_time)

    name_color = 0xFFFFFF
    edge_color = None
    if reminder:
        name_color = 0x00FF7F
        edge_color = 0x00FF7F
    elif is_pinned:
        name_color = 0xFFFF00
        edge_color = 0xFFFF00
        display_name = f"★ {display_name}"

    cat_color = CATEGORIES_DATA.get(category_name, (0x808080, [], []))[0]

    # Right column: what the viewer needs to decide - how much is left, or how long until it starts.
    progress_val = 0
    state_txt, state_col = "", 0x9090A0
    if duration > 0 and start_time <= now < (start_time + duration):
        progress_val = min(100, max(1, int(((now - start_time) / float(duration)) * 100)))
        state_txt = f"{fmt_duration(start_time + duration - now)} left"
    elif start_time > now:
        state_txt = f"in {fmt_duration(start_time - now)}"
        state_col = 0x00E5FF
    elif start_time > 0 and duration > 0:
        state_txt = "ended"
    if reminder:
        tag = "Auto-tune" if reminder.get('type') == 'zap' else "Reminder"
        state_txt = f"{tag} • {state_txt}" if state_txt else tag
        state_col = 0x00FF7F
    if progress_val >= 85:
        bar_color = 0xFF5050      # nearly over
    elif progress_val >= 50:
        bar_color = 0xFFC000
    else:
        bar_color = 0x00FF7F      # just started

    row_w, row_h = _s(840), _s(80)
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration, short_desc),
        MultiContentEntryText(pos=(_s(2), 0), size=(_s(8), row_h), font=0, flags=RT_HALIGN_LEFT, text="", backcolor=cat_color, backcolor_sel=cat_color),
        MultiContentEntryText(pos=(_s(15), _s(8)), size=(_s(62), _s(24)), font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryText(pos=(_s(15), _s(52)), size=(_s(62), _s(20)), font=3, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=end_str, color=0x708090, color_sel=0x90A0B0),
        _make_picon_entry(pos=(_s(80), _s(15)), size=(_s(50), _s(30)), png=icon_pixmap),
        MultiContentEntryText(pos=(_s(135), _s(4)), size=(_s(480), _s(26)), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=display_name, color=name_color, color_sel=name_color),
        MultiContentEntryText(pos=(_s(135), _s(30)), size=(_s(480), _s(24)), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(_s(135), _s(55)), size=(_s(480), _s(20)), font=3, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=short_desc or "", color=0x808088, color_sel=0xA8A8B0),
        MultiContentEntryText(pos=(_s(630), _s(4)), size=(_s(190), _s(24)), font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(_s(600), _s(52)), size=(_s(220), _s(20)), font=3, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=state_txt, color=state_col, color_sel=state_col),
    ]
    if progress_val > 0:
        res.append(MultiContentEntryProgress(pos=(_s(700), _s(36)), size=(_s(120), _s(8)), percent=progress_val, borderWidth=1, foreColor=bar_color))
    if edge_color is not None:
        res.append(MultiContentEntryText(pos=(row_w - _s(8), 0), size=(_s(4), row_h), font=0, flags=RT_HALIGN_LEFT, text="", backcolor=edge_color, backcolor_sel=edge_color))
    return res


# --- DEDICATED DISCOVERY SETUP SCREEN ---
class WTWDiscoverySetup(Screen, ConfigListScreen):
    skin = """
        <screen position="center,center" size="880,500" title="Discovery Notifications Settings">
            <widget name="title" position="25,15" size="830,32" font="Regular;24" foregroundColor="#00E5FF" transparent="1" />
            <widget name="hint" position="25,50" size="830,36" font="Regular;16" foregroundColor="#AAAAAA" transparent="1" />
            <widget name="config" position="25,95" size="830,330" scrollbarMode="showOnDemand" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="25,450" size="25,25" alphatest="on" />
            <widget name="key_red" position="55,450" size="140,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="220,450" size="25,25" alphatest="on" />
            <widget name="key_green" position="250,450" size="140,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="410,450" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="440,450" size="280,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [], session=session)
        self.session = session
        self["title"] = Label("Discovery Notifications Settings")
        self["hint"] = Label("Discreet live preview popup with satellite, position, picon and theme options.")
        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Save")
        self["key_yellow"] = Label("Preview Toast")

        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.cancel,
            "green": self.save,
            "yellow": self.test_toast,
            "cancel": self.cancel,
            "ok": self.save
        }, -2)

        self.list = [
            getConfigListEntry("Enable Discovery Notifications", config.plugins.WhatToWatch.discovery_mode),
            getConfigListEntry("Popup Interval (Minutes)", config.plugins.WhatToWatch.discovery_interval),
            getConfigListEntry("Popup Display Duration", config.plugins.WhatToWatch.discovery_duration),
            getConfigListEntry("Satellite / Source Filter", config.plugins.WhatToWatch.discovery_sat),
            getConfigListEntry("Category Filter", config.plugins.WhatToWatch.discovery_category),
            getConfigListEntry("Screen Position", config.plugins.WhatToWatch.discovery_position),
            getConfigListEntry("Background Transparency", config.plugins.WhatToWatch.discovery_transparency),
            getConfigListEntry("Play Audio Chime", config.plugins.WhatToWatch.discovery_sound),
        ]
        self["config"].list = self.list
        self["config"].setList(self.list)

    def test_toast(self):
        sat_filter = config.plugins.WhatToWatch.discovery_sat.value
        cat_pref = config.plugins.WhatToWatch.discovery_category.value
        sat_short = get_sat_short_name(sat_filter) if sat_filter != "all" else "Hotbird 13.0°E"
        cat_lbl = cat_pref if cat_pref != "all" else "Movies"

        sample_ref = None
        sample_ch = "Demo Cinema HD"
        sample_evt = "Interstellar (2014) • Sci-Fi Thriller"

        # Try to find a real channel and real EPG event from GLOBAL_SERVICE_LIST if available
        if GLOBAL_SERVICE_LIST:
            candidates = GLOBAL_SERVICE_LIST
            if sat_filter and sat_filter != "all":
                m = [s for s in GLOBAL_SERVICE_LIST if s and s[0] and sat_matches(get_sat_position(str(s[0])), sat_filter)]
                if m:
                    candidates = m
            
            epg_cache = eEPGCache.getInstance()
            for s in candidates[:20]:
                try:
                    s_ref, s_name = s[0], s[1]
                    if is_adult_content(s_name):
                        continue
                    candidate_ref = str(s_ref)
                    candidate_ch = str(s_name)
                    if epg_cache:
                        for r in get_epg_refs(candidate_ref):
                            evt = epg_cache.lookupEventTime(eServiceReference(r), -1)
                            if evt and evt.getEventName():
                                sample_ref = candidate_ref
                                sample_ch = candidate_ch
                                sample_evt = evt.getEventName()
                                break
                    if sample_ref:
                        break
                except Exception:
                    continue

        sat_pos = get_sat_position(sample_ref) if sample_ref else (sat_filter if sat_filter != "all" else "13.0E")
        sat_tag = get_sat_short_name(sat_pos) or sat_short

        if config.plugins.WhatToWatch.discovery_sound.value:
            play_chime(0.5)

        show_overlay(
            "toast", self.session, DiscoveryToast,
            "now",
            cat_lbl,
            f"{sample_ch} ({sat_tag})",
            sample_evt,
            int(time.time()),
            service_ref=sample_ref,
            raw_channel_name=sample_ch
        )

    def save(self):
        for x in self["config"].list:
            x[1].save()
        configfile.save()
        config.plugins.WhatToWatch.save()

        if monitor:
            monitor.restart_discovery_timer()

        sat_val = config.plugins.WhatToWatch.discovery_sat.value
        sat_name = get_sat_display_name(sat_val) if sat_val != "all" else "All Sats"
        status = f"Active ({config.plugins.WhatToWatch.discovery_interval.value}m • {sat_name})" if config.plugins.WhatToWatch.discovery_mode.value else "Disabled"
        self.session.open(MessageBox, f"Discovery Notifications: {status}", MessageBox.TYPE_INFO, timeout=2)
        self.close()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()


# --- SHARED EVENT ACTIONS (main list, search results, details) ---
class WTWEventActions(object):
    list_widget = "event_list"

    def _cur(self):
        """Selected row as a plain data tuple, whichever way the list was filled."""
        try:
            cur = self[self.list_widget].getCurrent()
        except Exception:
            return None
        if not cur:
            return None
        if isinstance(cur[0], (tuple, list)):
            cur = cur[0]
        return cur if len(cur) >= 7 else None

    def _refresh_rows(self):
        pass

    def _note(self, text, error=False, timeout=3):
        self.session.open(MessageBox, text, type=MessageBox.TYPE_ERROR if error else MessageBox.TYPE_INFO, timeout=timeout)

    def act_zap(self, item):
        try:
            self.session.nav.playService(eServiceReference(item[4]))
            return True
        except Exception:
            return False

    def act_remind(self, item):
        """Toggle: removes an existing reminder, otherwise asks how to be reminded."""
        existing = find_reminder(item[4], item[5])
        if existing:
            WATCHLIST.remove(existing)
            save_watchlist()
            self._refresh_rows()
            self._note("Reminder removed.", timeout=2)
            return
        if item[5] <= int(time.time()):
            self._note("This programme has already started!", error=True)
            return
        self.session.openWithCallback(lambda c: self._save_reminder(c, item), ChoiceBox, title="Set Reminder", list=reminder_choices())

    def _save_reminder(self, choice, item):
        if not choice:
            return
        type_code, offset = choice[1]
        add_reminder_entry(item, type_code, offset)
        save_watchlist()
        self._refresh_rows()
        self._note("Reminder saved.", timeout=2)

    def act_record(self, item):
        ok, msg = record_event(self.session, item)
        self._note(msg, error=not ok, timeout=5)

    def act_details(self, item):
        self.session.openWithCallback(lambda *a: self._refresh_rows(), WTWEventDetail, item)

# --- EVENT DETAILS ---
class WTWEventDetail(Screen, WTWEventActions):
    skin = """
        <screen position="center,center" size="900,600" title="Programme Details">
            <widget name="channel" position="25,12" size="850,30" font="Regular;22" foregroundColor="#00E5FF" transparent="1" />
            <widget name="title" position="25,46" size="850,72" font="Regular;28" foregroundColor="#FFFFFF" transparent="1" />
            <widget name="when" position="25,122" size="850,28" font="Regular;20" foregroundColor="#FFD700" transparent="1" />
            <eLabel position="25,156" size="850,2" backgroundColor="#00E5FF" />
            <widget name="desc" position="25,168" size="850,366" font="Regular;21" foregroundColor="#D0D0D0" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="25,556" size="25,25" alphatest="on" />
            <widget name="key_red" position="55,556" size="150,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="215,556" size="25,25" alphatest="on" />
            <widget name="key_green" position="245,556" size="200,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="455,556" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="485,556" size="190,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="685,556" size="25,25" alphatest="on" />
            <widget name="key_blue" position="715,556" size="170,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" />
        </screen>"""

    def __init__(self, session, item):
        Screen.__init__(self, session)
        self.session = session
        self.item = item
        self._alive = True
        self._original = ""
        self._translated = None
        self._showing_translation = False

        sat = get_sat_short_name(item[2]) if item[2] else ""
        self["channel"] = Label(f"{item[1]}  •  {sat}  •  {item[0]}" if sat else f"{item[1]}  •  {item[0]}")
        self["title"] = Label(item[3])
        self["when"] = Label("")
        self["desc"] = ScrollLabel("")
        self["key_red"] = Label("Close")
        self["key_green"] = Label("")
        self["key_yellow"] = Label("Translate")
        self["key_blue"] = Label("Record" if HAVE_RECORDTIMER else "")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.zap_and_close,
            "cancel": self.close,
            "red": self.close,
            "green": lambda: self.act_remind(self.item),
            "yellow": self.toggle_translation,
            "blue": lambda: self.act_record(self.item),
            "up": self.page_up,
            "left": self.page_up,
            "down": self.page_down,
            "right": self.page_down,
        }, -1)
        self.onLayoutFinish.append(self._fill)
        self.onClose.append(self._on_close)

    def _on_close(self):
        self._alive = False

    def _refresh_rows(self):
        item, now = self.item, int(time.time())
        start, dur = int(item[5] or 0), int(item[6] or 0)
        when = time.strftime("%a %d %b  %H:%M", time.localtime(start)) if start else ""
        if start and dur:
            when += time.strftime(" - %H:%M", time.localtime(start + dur)) + f"  ({fmt_duration(dur)})"
            if start <= now < start + dur:
                when += f"  •  {fmt_duration(start + dur - now)} left"
            elif start > now:
                when += f"  •  in {fmt_duration(start - now)}"
        self["when"].setText(when)
        if find_reminder(item[4], start):
            self["key_green"].setText("Remove reminder")
        else:
            self["key_green"].setText("Remind me" if start > now else "")

    def _fill(self):
        self._refresh_rows()
        item = self.item
        parts = []
        short = str(item[7] if len(item) > 7 else "" or "")
        try:
            ev = fetch_event(item[4], item[5], item[6])
            if ev:
                short = ev.getShortDescription() or short
                ext = ev.getExtendedDescription() or ""
                if short and short != item[3]:
                    parts.append(short)
                if ext and ext != short:
                    parts.append(ext)
            elif short:
                parts.append(short)
        except Exception:
            if short:
                parts.append(short)
        self._original = "\n\n".join(parts) or "No description in the EPG for this programme."
        self["desc"].setText(self._original)

    def page_up(self):
        try:
            self["desc"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            self["desc"].pageDown()
        except Exception:
            pass

    def zap_and_close(self):
        self.act_zap(self.item)
        self.close()

    def toggle_translation(self):
        if self._showing_translation:
            self._showing_translation = False
            self["title"].setText(self.item[3])
            self["desc"].setText(self._original)
            self["key_yellow"].setText("Translate")
            return
        if self._translated is not None:
            self._show_translation()
            return
        self["key_yellow"].setText("Translating...")
        text = self.item[3] + "\n\n" + self._original
        translate_async(text, self._on_translated)

    def _on_translated(self, out):
        if not self._alive:
            return
        self._translated = out or ""
        self._show_translation()

    def _show_translation(self):
        head, _, body = (self._translated or "").partition("\n\n")
        self._showing_translation = True
        self["title"].setText(head.strip() or self.item[3])
        self["desc"].setText(body.strip() or self._original)
        self["key_yellow"].setText("Original")


# --- SEARCH SCREEN ---
class WTWSearchScreen(Screen, WTWEventActions):
    list_widget = "results_list"

    def __init__(self, session, initial_query=""):
        Screen.__init__(self, session)
        self.session = session
        self.initial_query = initial_query
        self.query = ""
        self.skin = f"""
        <screen position="center,center" size="{_p(880, 620)}" title="Search EPG">
            <widget name="search_label" position="{_p(20, 12)}" size="{_p(840, 34)}" font="Regular;{_s(22)}" foregroundColor="#00E5FF" transparent="1" />
            <widget name="results_list" position="{_p(20, 55)}" size="{_p(840, 480)}" scrollbarMode="showOnDemand" />
            <widget name="hint" position="{_p(20, 540)}" size="{_p(840, 24)}" font="Regular;{_s(16)}" halign="center" foregroundColor="#888899" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="{_p(20, 578)}" size="25,25" alphatest="on" />
            <widget name="key_red" position="{_p(52, 576)}" size="{_p(150, 28)}" font="Regular;{_s(20)}" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="{_p(215, 578)}" size="25,25" alphatest="on" />
            <widget name="key_green" position="{_p(247, 576)}" size="{_p(150, 28)}" font="Regular;{_s(20)}" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="{_p(410, 578)}" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="{_p(442, 576)}" size="{_p(230, 28)}" font="Regular;{_s(20)}" foregroundColor="#FFFFFF" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="{_p(685, 578)}" size="25,25" alphatest="on" />
            <widget name="key_blue" position="{_p(717, 576)}" size="{_p(150, 28)}" font="Regular;{_s(20)}" foregroundColor="#FFFFFF" transparent="1" />
        </screen>"""
        self["search_label"] = Label("Enter search query...")
        self["hint"] = Label("OK: Zap / Remind / Record • INFO: Details")
        self["key_red"] = Label("New Search")
        self["key_green"] = Label("Remind")
        self["key_yellow"] = Label("Follow keyword")
        self["key_blue"] = Label("Record" if HAVE_RECORDTIMER else "")
        self["results_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        setup_event_list(self["results_list"])
        self["results_list"].l.setBuildFunc(build_list_entry)

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.ok_pressed,
            "cancel": self.close,
            "red": self.prompt_query,
            "green": self.remind_pressed,
            "yellow": self.toggle_follow,
            "blue": self.record_pressed,
            "info": self.info_pressed,
        }, -1)

        self.results = []
        self.onLayoutFinish.append(self.start_initial_search)

    def start_initial_search(self):
        if self.initial_query:
            self.execute_search(self.initial_query)

    def prompt_query(self):
        if HAVE_VIRTUAL_KEYBOARD:
            self.session.openWithCallback(self.execute_search, VirtualKeyBoard, title="Search EPG Events:", text=self.query)
        else:
            self.execute_search("")

    def execute_search(self, query):
        query = str(query or "").strip()
        if not query:
            return
        self.query = query
        if not eEPGCache.getInstance():
            self["search_label"].setText("EPG Cache unavailable.")
            return
        self.results = epg_search(query, limit=300)
        self._refresh_rows()

    def _refresh_rows(self):
        self["results_list"].setList([tuple(r) for r in self.results])
        n = len(self.results)
        self["search_label"].setText(f"{n} upcoming event{'' if n == 1 else 's'} for: '{self.query}'" if self.query else "Enter search query...")
        self["key_yellow"].setText("Stop following" if is_followed(self.query) else "Follow keyword")

    def ok_pressed(self):
        item = self._cur()
        if not item:
            return
        menu = [("Zap to Channel Now", "zap")]
        if find_reminder(item[4], item[5]):
            menu.append(("Remove Reminder", "rem"))
        elif item[5] > int(time.time()):
            menu.append(("Set Reminder", "rem"))
        if HAVE_RECORDTIMER:
            menu.append(("Record this programme", "rec"))
        menu.append(("Programme details", "info"))
        self.session.openWithCallback(lambda c: self._ok_cb(c, item), ChoiceBox, title=item[3], list=menu)

    def _ok_cb(self, choice, item):
        if not choice:
            return
        if choice[1] == "zap":
            self.act_zap(item)
            self.close()
        elif choice[1] == "rem":
            self.act_remind(item)
        elif choice[1] == "rec":
            self.act_record(item)
        elif choice[1] == "info":
            self.act_details(item)

    def remind_pressed(self):
        item = self._cur()
        if item:
            self.act_remind(item)

    def record_pressed(self):
        item = self._cur()
        if item and HAVE_RECORDTIMER:
            self.act_record(item)

    def info_pressed(self):
        item = self._cur()
        if item:
            self.act_details(item)

    def toggle_follow(self):
        if not self.query:
            return
        if is_followed(self.query):
            follow_remove(self.query)
            self._refresh_rows()
            self._note(f"Stopped following '{self.query}'.", timeout=2)
            return
        follow_add(self.query)
        added = 0
        if monitor:
            try:
                added = monitor.follow_keyword(self.query)
                if added:
                    save_watchlist()
            except Exception:
                added = 0
        self._refresh_rows()
        self._note(
            f"Following '{self.query}'.\nNew matches in the EPG get a reminder automatically."
            + (f"\n{added} reminder{'' if added == 1 else 's'} created for the next 24 hours." if added else ""),
            timeout=5
        )


# --- SETTINGS ---
class WhatToWatchSetup(Screen, ConfigListScreen):
    skin = """
        <screen position="center,center" size="600,400" title="What to Watch Settings">
            <widget name="config" position="10,10" size="580,300" scrollbarMode="showOnDemand" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="10,360" size="25,25" alphatest="on" />
            <widget name="key_red" position="40,360" size="200,25" zPosition="1" font="Regular;20" halign="left" text="Cancel" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="300,360" size="25,25" alphatest="on" />
            <widget name="key_green" position="330,360" size="200,25" zPosition="1" font="Regular;20" halign="left" text="Save" transparent="1" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [], session=session)
        self.session = session
        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Save")
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.cancel,
            "green": self.save,
            "cancel": self.cancel,
            "ok": self.save
        }, -2)
        self.list = [
            getConfigListEntry("Discovery Notifications", config.plugins.WhatToWatch.discovery_mode),
            getConfigListEntry("Discovery Popup Interval", config.plugins.WhatToWatch.discovery_interval),
            getConfigListEntry("Discovery Satellite Filter", config.plugins.WhatToWatch.discovery_sat),
            getConfigListEntry("Discovery Screen Position", config.plugins.WhatToWatch.discovery_position),
            getConfigListEntry("Discovery Transparency", config.plugins.WhatToWatch.discovery_transparency),
            getConfigListEntry("Transparent Background", config.plugins.WhatToWatch.transparent_bg),
            getConfigListEntry("Multi-Tier Adult Filter", config.plugins.WhatToWatch.adult_filter),
            getConfigListEntry("Use DVB Broadcaster Genres", config.plugins.WhatToWatch.use_dvb_genre),
            getConfigListEntry("Default Reminder Lead Time", config.plugins.WhatToWatch.default_lead_time),
            getConfigListEntry("Default Sort Mode", config.plugins.WhatToWatch.sort_mode),
            getConfigListEntry("Auto-Remind Followed Keywords", config.plugins.WhatToWatch.follow_enabled)
        ]
        self["config"].list = self.list
        self["config"].setList(self.list)

    def save(self):
        for x in self["config"].list:
            x[1].save()
        configfile.save()
        config.plugins.WhatToWatch.save()

        if monitor:
            monitor.restart_discovery_timer()

        self.close()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()


# --- MAIN SCREEN ---
class WhatToWatchScreen(Screen, WTWEventActions):
    TIME_STEPS = [0, 3600, 7200, 14400, 21600, 28800]

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        is_transparent = config.plugins.WhatToWatch.transparent_bg.value
        bg_color = "#80000000" if is_transparent else "#ff181818"
        # The layout is drawn for 1080p and scaled to the real desktop, so the colour buttons
        # (at y=760) stay on screen on a 720p receiver.
        btn_scale = '' if ui_scale() == 1.0 else ' scale="1"'

        self.skin = f"""<screen position="0,0" size="{_p(860, 860)}" title="What to Watch" flags="wfNoBorder" backgroundColor="#00000000">
            <eLabel position="0,0" size="{_p(860, 860)}" backgroundColor="{bg_color}" zPosition="-1" />

            <!-- ═══ HEADER STRIP 1: Left Logo + Event Count | Right Status ═══ -->
            <eLabel position="0,0" size="{_p(860, 50)}" backgroundColor="#ff0d0d12" zPosition="0" />
            <widget name="header_logo" position="{_p(15, 3)}" size="{_p(239, 43)}" zPosition="2" alphatest="on" scale="1" transparent="1" />
            <widget name="event_count_label" position="{_p(265, 3)}" size="{_p(270, 43)}" zPosition="2" font="Regular;{_s(22)}" halign="left" valign="center" foregroundColor="#00E5FF" backgroundColor="#ff0d0d12" transparent="1" />
            <widget name="status_label" position="{_p(540, 3)}" size="{_p(305, 43)}" zPosition="2" font="Regular;{_s(18)}" halign="right" valign="center" foregroundColor="#00E5FF" backgroundColor="#ff0d0d12" transparent="1" />

            <!-- ═══ ACCENT DIVIDER ═══ -->
            <eLabel position="{_p(0, 50)}" size="{_p(860, 2)}" backgroundColor="#00E5FF" zPosition="1" />

            <!-- ═══ HEADER STRIP 2: Info bar ═══ -->
            <eLabel position="{_p(0, 52)}" size="{_p(860, 24)}" backgroundColor="#ff101018" zPosition="0" />
            <widget name="info_bar" position="{_p(10, 52)}" size="{_p(840, 24)}" font="Regular;{_s(15)}" halign="center" valign="center" foregroundColor="#888899" backgroundColor="#ff101018" transparent="1" />

            <!-- ═══ EVENT LIST ═══ -->
            <widget name="event_list" position="{_p(10, 80)}" size="{_p(840, 668)}" scrollbarMode="showOnDemand" transparent="1" />

            <!-- ═══ BUTTONS ROW 1 ═══ -->
            <ePixmap pixmap="skin_default/buttons/red.png" position="{_p(15, 760)}" size="{_p(25, 25)}" alphatest="on"{btn_scale} />
            <widget name="key_red" position="{_p(42, 760)}" size="{_p(120, 25)}" zPosition="1" font="Regular;{_s(18)}" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="{_p(168, 760)}" size="{_p(25, 25)}" alphatest="on"{btn_scale} />
            <widget name="key_green" position="{_p(195, 760)}" size="{_p(185, 25)}" zPosition="1" font="Regular;{_s(18)}" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="{_p(386, 760)}" size="{_p(25, 25)}" alphatest="on"{btn_scale} />
            <widget name="key_yellow" position="{_p(414, 760)}" size="{_p(340, 25)}" zPosition="1" font="Regular;{_s(18)}" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="{_p(760, 760)}" size="{_p(25, 25)}" alphatest="on"{btn_scale} />
            <widget name="key_blue" position="{_p(788, 760)}" size="{_p(65, 25)}" zPosition="1" font="Regular;{_s(18)}" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />

            <!-- ═══ BOTTOM HINT BAR ═══ -->
            <widget name="hint_bar" position="{_p(10, 790)}" size="{_p(840, 20)}" font="Regular;{_s(14)}" halign="center" valign="center" foregroundColor="#ffff00" backgroundColor="{bg_color}" transparent="1" />
        </screen>"""

        self["header_logo"] = Pixmap()
        self["event_count_label"] = Label("")
        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        setup_event_list(self["event_list"])
        # Rows are built on demand: only the ones on screen are rendered and get their picon decoded.
        self["event_list"].l.setBuildFunc(build_list_entry)

        self["status_label"] = Label("Loading channels...")
        self["key_red"] = Label("Time: Now")
        self["key_green"] = Label("Satellite")
        self["key_yellow"] = Label("Category")
        self["key_blue"] = Label("Options")
        self["info_bar"] = Label("1-9: Category • 0: Reset • CH+/-: Time • MENU: Sort • INFO: Details")
        self.default_hint = f"v{VERSION} by {AUTHOR} • OK: Zap / Actions • Long OK: Remind"
        self["hint_bar"] = Label(self.default_hint)

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.ok_pressed,
            "ok_long": self.add_reminder,
            "cancel": self.close,
            "red": self.toggle_time,
            "green": self.show_sat_menu,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
            "info": self.show_details,
            "nextBouquet": lambda: self.step_time(1),
            "prevBouquet": lambda: self.step_time(-1),
        }, -1)

        self["numbers"] = NumberActionMap(["NumberActions"], {
            "1": lambda *a: self.jump_category_idx(0),
            "2": lambda *a: self.jump_category_idx(1),
            "3": lambda *a: self.jump_category_idx(2),
            "4": lambda *a: self.jump_category_idx(3),
            "5": lambda *a: self.jump_category_idx(4),
            "6": lambda *a: self.jump_category_idx(5),
            "7": lambda *a: self.jump_category_idx(6),
            "8": lambda *a: self.jump_category_idx(7),
            "9": lambda *a: self.jump_category_idx(8),
            "0": lambda *a: self.reset_filters()
        }, -1)

        self.full_list = []
        self.raw_services = []
        self.scan_pos = 0
        self.scanning = False
        self.hidden_adult = 0
        self.use_batch = True         # one EPG query per chunk; falls back to per-channel lookups
        self.batch_verified = False
        self.current_filter = None
        self.current_sat_filter = None
        self.use_favorites = False
        self.sort_mode = config.plugins.WhatToWatch.sort_mode.value
        self.time_offset = 0
        self._last_category_press = 0.0
        self._last_time_press = 0.0
        self._alive = True

        self.init_timer = eTimer()
        self.init_timer.callback.append(self.start_full_rescan)

        self.process_timer = eTimer()
        self.process_timer.callback.append(self.process_batch)

        self.repaint_timer = eTimer()
        self.repaint_timer.callback.append(self.rebuild_visual_list)

        # Keeps progress bars and "x min left" honest while the screen stays open.
        self.tick_timer = eTimer()
        self.tick_timer.callback.append(self._minute_tick)

        self.onLayoutFinish.append(self._on_layout_finish)
        self.onClose.append(self._cleanup)
        self._apply_header_logo()

    def _apply_header_logo(self):
        hdr_path = get_header_image_path()
        if not hdr_path or not os.path.exists(hdr_path):
            return
        # 1. Primary: ePicLoad for smooth, anti-aliased scaling to the header box
        try:
            sc = ePicLoad()
            sc.setPara((_s(239), _s(43), 1, 1, False, 1, "#00000000"))
            if sc.startDecode(hdr_path, 0, 0, False) == 0:
                ptr = sc.getData()
                if ptr:
                    self["header_logo"].setPixmap(ptr)
                    if hasattr(self["header_logo"], "instance") and self["header_logo"].instance:
                        self["header_logo"].instance.setScale(2)
                    return
        except Exception:
            pass
        # 2. Fallback: loadPNG
        try:
            px = loadPNG(hdr_path)
            if px:
                self["header_logo"].setPixmap(px)
                if hasattr(self["header_logo"], "instance") and self["header_logo"].instance:
                    self["header_logo"].instance.setScale(2)
        except Exception:
            pass

    def _on_layout_finish(self):
        self._apply_header_logo()
        self.init_timer.start(50, True)
        self.tick_timer.start(60000, False)

    def _cleanup(self):
        self._alive = False
        for tmr, cb in (
            (self.init_timer, self.start_full_rescan),
            (self.process_timer, self.process_batch),
            (self.repaint_timer, self.rebuild_visual_list),
            (self.tick_timer, self._minute_tick),
        ):
            tmr.stop()
            try:
                tmr.callback.remove(cb)
            except Exception:
                pass

    def _minute_tick(self):
        if not self.scanning:
            self.rebuild_visual_list()

    def _refresh_rows(self):
        self.rebuild_visual_list()

    def jump_category_idx(self, idx):
        if 0 <= idx < len(CATEGORIES_ORDER):
            self.current_filter = CATEGORIES_ORDER[idx]
            self.rebuild_visual_list()
            self["event_list"].moveToIndex(0)

    def reset_filters(self):
        self.current_filter = None
        self.current_sat_filter = None
        if self.time_offset:
            self.time_offset = 0
            self["key_red"].setText("Time: Now")
            self.start_full_rescan()
        else:
            self.rebuild_visual_list()

    def open_search(self):
        if HAVE_VIRTUAL_KEYBOARD:
            self.session.openWithCallback(self.search_input_callback, VirtualKeyBoard, title="Search EPG Events:")
        else:
            self.search_input_callback("")

    def search_input_callback(self, query):
        if query:
            self.session.openWithCallback(lambda *a: self.rebuild_visual_list(), WTWSearchScreen, query)

    def build_entry(self, *args, **kwargs):
        return build_list_entry(*args[:8])

    @staticmethod
    def _ver_tuple(v):
        return version_tuple(v)

    # ------------------------------------------------------------------ scanning
    def start_full_rescan(self):
        self.process_timer.stop()
        self.repaint_timer.stop()
        self.full_list = []
        self.raw_services = []
        self.scan_pos = 0
        self.hidden_adult = 0
        self.scanning = False
        self["event_list"].setList([])

        time_text = "Now" if self.time_offset == 0 else f"+{self.time_offset//3600}h"
        self["status_label"].setText(f"Loading channels ({time_text})...")
        self["event_count_label"].setText("(0 events)")

        try:
            service_handler = eServiceCenter.getInstance()
            ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' if self.use_favorites else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
            bouquet_root = eServiceReference(ref_str)
            bouquet_list = service_handler.list(bouquet_root)
            if not bouquet_list:
                self["status_label"].setText("No bouquets found.")
                return

            bouquet_content = bouquet_list.getContent("SN", True)
            if not bouquet_content:
                self["status_label"].setText("No bouquets found.")
                return

            raw = []
            for bouquet_entry in bouquet_content:
                if not bouquet_entry or not bouquet_entry[0]:
                    continue
                services = service_handler.list(eServiceReference(bouquet_entry[0]))
                if services:
                    items = services.getContent("SN", True)
                    if items:
                        for it in items:
                            if it and it[0]:
                                r_it = str(it[0])
                                if "FROM BOUQUET" in r_it or r_it.startswith("1:7:1:") or r_it.startswith("1:7:2:"):
                                    sub_list = service_handler.list(eServiceReference(it[0]))
                                    if sub_list:
                                        sub_items = sub_list.getContent("SN", True)
                                        if sub_items:
                                            for sit in sub_items:
                                                if sit and sit[0]:
                                                    rs = str(sit[0])
                                                    if not rs.startswith("1:64:") and "::" not in rs:
                                                        raw.append(sit)
                                elif not r_it.startswith("1:64:") and "::" not in r_it:
                                    raw.append(it)

            # Deduplicate channels and cap at 8,000
            seen, unique = set(), []
            for entry in raw:
                s_ref = str(entry[0])
                s_name = str(entry[1]) if len(entry) > 1 else ""
                if is_adult_content(s_name):
                    self.hidden_adult += 1
                    continue
                sat = get_sat_position(s_ref)
                key = (s_name.strip().lower(), sat)
                if key not in seen:
                    seen.add(key)
                    unique.append((s_ref, s_name))
                    if len(unique) >= 8000:
                        break

            self.raw_services = unique
            if self.raw_services:
                self.scanning = True
                self["status_label"].setText(f"Scanning {len(self.raw_services)} channels...")
                self.process_timer.start(10, False)
            else:
                self["status_label"].setText("No channels found in bouquets.")
        except Exception as e:
            self["status_label"].setText(f"Error: {e}")

    def _lookup_chunk(self, epg_cache, chunk, query_time):
        """One C++ call for a whole chunk of channels instead of one (or several) per channel.
        Returns (ref, name, query_ref, event_id, begin, duration, title, short_desc) tuples."""
        qmap = {}
        query = ["RIBDTS"]
        for s_ref, s_name in chunk:
            q = get_epg_refs(s_ref)[0]
            k = _ref_key(q)
            if k not in qmap:
                qmap[k] = []
                query.append((q, 0, query_time))
            qmap[k].append((s_ref, s_name, q))
        rows = epg_cache.lookupEvent(query) or []
        out = []
        for row in rows:
            if not row or len(row) < 5 or not row[4]:
                continue
            for s_ref, s_name, q in qmap.get(_ref_key(row[0]), ()):
                out.append((s_ref, s_name, q, row[1], int(row[2] or 0), int(row[3] or 0), str(row[4]), str(row[5] or "") if len(row) > 5 else ""))
        return out

    def _lookup_single(self, epg_cache, s_ref, query_time):
        for candidate_ref in get_epg_refs(s_ref):
            try:
                ev = epg_cache.lookupEventTime(eServiceReference(candidate_ref), query_time)
            except Exception:
                ev = None
            if ev and ev.getEventName():
                return ev
        return None

    def _add_event(self, s_ref, s_name, title, begin, dur, short_desc, genre=(0, 0)):
        cat = classify_enhanced(s_name, title, genre_nib=genre)
        if cat is None:
            self.hidden_adult += 1
            return None
        if short_desc == title:
            short_desc = ""
        self.full_list.append(WTWEventItem(cat, s_name, get_sat_position(s_ref), title, s_ref, begin, dur, short_desc))
        return cat

    def process_batch(self):
        total = len(self.raw_services)
        if self.scan_pos >= total:
            self.process_timer.stop()
            self.scanning = False
            self.rebuild_visual_list()
            return

        epg_cache = eEPGCache.getInstance()
        if not epg_cache:
            self.process_timer.stop()
            self.scanning = False
            self["status_label"].setText("EPG cache unavailable.")
            return

        query_time = int(time.time()) + self.time_offset
        use_genre = _cfg("use_dvb_genre", True)
        before = len(self.full_list)

        if self.use_batch:
            chunk = self.raw_services[self.scan_pos:self.scan_pos + 150]
            try:
                rows = self._lookup_chunk(epg_cache, chunk, query_time)
            except Exception:
                self.use_batch = False        # this image has no usable lookupEvent: go per channel
                return
            if rows:
                self.batch_verified = True
            elif not self.batch_verified:
                # Nothing came back and the batch path has never worked on this box: make sure that
                # is really "no EPG here" and not an API quirk before trusting it.
                for s_ref, s_name in chunk[:25]:
                    if self._lookup_single(epg_cache, s_ref, query_time):
                        self.use_batch = False
                        return
            self.scan_pos += len(chunk)
            for s_ref, s_name, q_ref, evt_id, begin, dur, title, short_desc in rows:
                genre = (0, 0)
                if use_genre and _channel_categories(s_name)[0] in (None, "General"):
                    # Only channels the database does not pin to a category need the broadcaster's genre.
                    try:
                        genre = genre_levels(epg_cache.lookupEventId(eServiceReference(q_ref), evt_id))
                    except Exception:
                        genre = (0, 0)
                self._add_event(s_ref, s_name, title, begin, dur, short_desc, genre)
        else:
            deadline = time.time() + 0.03
            while self.scan_pos < total and time.time() < deadline:
                s_ref, s_name = self.raw_services[self.scan_pos]
                self.scan_pos += 1
                try:
                    event = self._lookup_single(epg_cache, s_ref, query_time)
                    if not event:
                        continue
                    self._add_event(
                        s_ref, s_name, event.getEventName(),
                        int(event.getBeginTime() or 0), int(event.getDuration() or 0),
                        event.getShortDescription() or "",
                        genre_levels(event) if use_genre else (0, 0)
                    )
                except Exception:
                    continue

        self["status_label"].setText(f"Scanning {min(self.scan_pos, total)}/{total}...")
        if len(self.full_list) != before:
            self._request_repaint()

    def _request_repaint(self):
        if not self.repaint_timer.isActive():
            self.repaint_timer.start(300, True)

    def _sat_matches(self, sat_val, filter_val):
        return sat_matches(sat_val, filter_val)

    def rebuild_visual_list(self):
        if self.current_sat_filter == "watchlist":
            filtered = []
            for w in WATCHLIST:
                label = "Followed" if w.get('auto') else "Watch"
                filtered.append(WTWEventItem(
                    label, w.get('name', ''), "", w.get('evt', ''),
                    w.get('ref', ''), int(w.get('start_time', 0)), 0,
                    f"Following \"{w['auto']}\"" if w.get('auto') else ""
                ))
            filtered.sort(key=lambda x: x["start"])
        else:
            filtered = [
                x for x in self.full_list
                if (not self.current_filter or x["cat"] == self.current_filter) and
                   (not self.current_sat_filter or self._sat_matches(x["sat"], self.current_sat_filter))
            ]
            pinned = set(PINNED_CHANNELS)
            order = dict((c, i) for i, c in enumerate(CATEGORIES_ORDER))

            if self.sort_mode == 'category':
                filtered.sort(key=lambda x: (
                    0 if x[4] in pinned else 1,
                    order.get(x[0], 99),
                    x[5],
                    x[1].lower()
                ))
            elif self.sort_mode == 'channel':
                filtered.sort(key=lambda x: (
                    0 if x[4] in pinned else 1,
                    x[1].lower(),
                    x[5]
                ))
            else:
                filtered.sort(key=lambda x: (
                    0 if x[4] in pinned else 1,
                    x[5],
                    x[1].lower()
                ))

        self["event_list"].setList([tuple(x) for x in filtered])

        if self.current_sat_filter == "watchlist":
            sat_text = "My Watchlist"
        else:
            sat_text = get_sat_display_name(self.current_sat_filter) if self.current_sat_filter else "All Sats"
        cat_text = self.current_filter or "All"
        self["key_yellow"].setText(f"Category: {cat_text}")
        self["key_green"].setText(f"Sat: {sat_text}")
        if not self.scanning:
            self["status_label"].setText(f"{cat_text} • {sat_text}")
        count = f"({len(filtered)} events)"
        if self.hidden_adult and self.current_sat_filter != "watchlist":
            count = f"({len(filtered)} events • {self.hidden_adult} hidden)"
        self["event_count_label"].setText(count)

    # ------------------------------------------------------------------ time / category
    def _apply_time_offset(self, offset):
        self.time_offset = offset
        self["key_red"].setText(f"Time: +{self.time_offset//3600}h" if self.time_offset else "Time: Now")
        self.start_full_rescan()

    def step_time(self, direction):
        now = time.time()
        if (now - self._last_time_press) < 0.6:
            return
        self._last_time_press = now
        try:
            idx = self.TIME_STEPS.index(self.time_offset)
        except ValueError:
            idx = 0
        self._apply_time_offset(self.TIME_STEPS[(idx + direction) % len(self.TIME_STEPS)])

    def toggle_time(self):
        self.step_time(1)

    def cycle_category(self):
        now = time.time()
        if (now - getattr(self, "_last_category_press", 0.0)) < 0.5:
            return
        self._last_category_press = now

        present = set(x[0] for x in self.full_list if x[0])
        cats = [c for c in CATEGORIES_ORDER if c in present]     # same order as the number keys
        if not cats:
            return
        if not self.current_filter:
            self.current_filter = cats[0]
        else:
            try:
                idx = cats.index(self.current_filter)
                self.current_filter = cats[idx + 1] if idx < len(cats) - 1 else None
            except Exception:
                self.current_filter = None
        self.rebuild_visual_list()
        self["event_list"].moveToIndex(0)

    def show_details(self):
        item = self._cur()
        if item:
            self.act_details(item)

    def show_translated_info(self):
        self.show_details()

    # ------------------------------------------------------------------ options
    def show_options_menu(self):
        disc_state = config.plugins.WhatToWatch.discovery_mode.value
        try:
            disc_int = config.plugins.WhatToWatch.discovery_interval.value
        except Exception:
            disc_int = "15"
        sat_val = config.plugins.WhatToWatch.discovery_sat.value
        sat_tag = f" • {get_sat_display_name(sat_val)}" if sat_val != "all" else ""
        disc_text = f"Discovery Notifications ({disc_int}m{sat_tag} - Active)" if disc_state else "Discovery Notifications (Disabled)"
        item = self._cur()

        menu = [
            ("Search EPG", "search"),
            (f"Followed Keywords ({len(FOLLOWED)}) - never miss a title", "follow"),
            (disc_text, "discovery_setup"),
            ("Set Reminder / Zap", "rem"),
        ]
        if HAVE_RECORDTIMER:
            menu.append(("Record this programme", "rec"))
        menu.append(("Pin / Unpin Channel", "pin"))
        if item:
            ov = USER_OVERRIDES.get(str(item[1]).strip().lower())
            menu.append((f"Set Category for {item[1]}" + (f" (now: {ov})" if ov else ""), "override"))
        menu += [
            ("Clear All Reminders", "clear"),
            ("Refresh Channels", "refresh"),
            ("Check for Updates", "update"),
            ("Settings & Configuration", "settings")
        ]
        self.session.openWithCallback(self.menu_cb, ChoiceBox, title="What to Watch Options", list=menu)

    def options_menu_cb(self, choice):
        return self.menu_cb(choice)

    def menu_cb(self, choice):
        if not choice:
            return
        c = choice[1]
        if c == "search":
            self.open_search()
        elif c == "follow":
            self.show_follow_menu()
        elif c == "discovery_setup":
            self.session.open(WTWDiscoverySetup)
        elif c == "rem":
            self.add_reminder()
        elif c == "rec":
            item = self._cur()
            if item:
                self.act_record(item)
        elif c == "pin":
            item = self._cur()
            if item:
                toggle_pin(item[4])
                self.rebuild_visual_list()
        elif c == "override":
            self.show_override_menu()
        elif c == "clear":
            self.clear_all_reminders()
        elif c == "refresh":
            self.start_full_rescan()
        elif c == "update":
            self.check_for_updates()
        elif c == "settings":
            self.session.openWithCallback(lambda *a: self._settings_closed(), WhatToWatchSetup)

    def _settings_closed(self):
        # The adult filter / DVB genre switches change classification, so cached answers are stale.
        clear_classification_caches()
        self.start_full_rescan()

    # ------------------------------------------------------------------ category override
    def show_override_menu(self):
        item = self._cur()
        if not item:
            return
        menu = [("Automatic (remove my choice)", None)] + [(c, c) for c in CATEGORIES_ORDER]
        self.session.openWithCallback(lambda c: self._override_cb(c, item[1]), ChoiceBox, title=f"Category for {item[1]}", list=menu)

    def _override_cb(self, choice, channel_name):
        if not choice:
            return
        if not set_channel_override(channel_name, choice[1]):
            return
        target = str(channel_name).strip().lower()
        for i, x in enumerate(self.full_list):
            if str(x[1]).strip().lower() == target:
                cat = classify_enhanced(x[1], x[3]) or x[0]
                self.full_list[i] = WTWEventItem(cat, x[1], x[2], x[3], x[4], x[5], x[6], x[7])
        self.rebuild_visual_list()

    # ------------------------------------------------------------------ followed keywords
    def show_follow_menu(self):
        menu = [("+ Follow a new keyword (team, show, actor...)", ("add", None))]
        if FOLLOWED:
            menu.append(("Check the EPG now", ("scan", None)))
        for kw in FOLLOWED:
            pending = sum(1 for w in WATCHLIST if w.get('auto') == kw)
            menu.append((f"Stop following: {kw}" + (f"  ({pending} reminder{'' if pending == 1 else 's'})" if pending else ""), ("del", kw)))
        self.session.openWithCallback(self._follow_cb, ChoiceBox, title="Followed Keywords", list=menu)

    def _follow_cb(self, choice):
        if not choice:
            return
        action, kw = choice[1]
        if action == "add":
            if HAVE_VIRTUAL_KEYBOARD:
                self.session.openWithCallback(self._follow_add_cb, VirtualKeyBoard, title="Keyword to follow:")
        elif action == "del":
            follow_remove(kw)
            self.rebuild_visual_list()
            self._note(f"Stopped following '{kw}'.", timeout=2)
        elif action == "scan" and monitor:
            self["hint_bar"].setText("Checking the EPG for followed keywords...")
            monitor.follow_scan(done_cb=self._follow_scan_done)

    def _follow_add_cb(self, text):
        kw = str(text or "").strip()
        if not kw:
            return
        if not follow_add(kw):
            self._note(f"'{kw}' is already followed.", timeout=2)
            return
        added = 0
        if monitor:
            try:
                added = monitor.follow_keyword(kw)
                if added:
                    save_watchlist()
            except Exception:
                added = 0
        self.rebuild_visual_list()
        self._note(
            f"Following '{kw}'.\nNew matches in the EPG get a reminder automatically."
            + (f"\n{added} reminder{'' if added == 1 else 's'} created for the next 24 hours." if added else "\nNothing in the next 24 hours yet."),
            timeout=5
        )

    def _follow_scan_done(self, added):
        if not self._alive:
            return
        self["hint_bar"].setText(self.default_hint)
        self.rebuild_visual_list()
        self._note(f"{added} new reminder{'' if added == 1 else 's'} from followed keywords.", timeout=3)

    # ------------------------------------------------------------------ updates (all network I/O off the main loop)
    def check_for_updates(self):
        self.session.openWithCallback(self.do_update_check, MessageBox, "Check GitHub for updates?", MessageBox.TYPE_YESNO)

    def do_update_check(self, confirm):
        if not confirm:
            return
        self["hint_bar"].setText("Checking for updates...")
        http_get_async(UPDATE_URL_VER, self._on_version_fetched, timeout=8)

    def _on_version_fetched(self, data, err):
        if not self._alive:
            return
        self["hint_bar"].setText(self.default_hint)
        if not data:
            self.session.open(MessageBox, f"Cannot check for updates.\n{err or 'No response.'}", MessageBox.TYPE_ERROR)
            return
        new_ver = data.decode("utf-8", "replace").strip().split()[0] if data.strip() else ""
        if new_ver and version_tuple(new_ver) > version_tuple(VERSION):
            self.session.openWithCallback(self.install_update, MessageBox, f"New version {new_ver} available (installed: v{VERSION}).\nUpdate now?", MessageBox.TYPE_YESNO)
        else:
            self.session.open(MessageBox, f"Plugin is up to date (v{VERSION}).", MessageBox.TYPE_INFO)

    def install_update(self, confirm):
        if not confirm:
            return
        self["hint_bar"].setText("Downloading update...")
        http_get_async(UPDATE_URL_PY, self._on_update_fetched, timeout=25)

    def _on_update_fetched(self, data, err):
        if not self._alive:
            return
        self["hint_bar"].setText(self.default_hint)
        if not data:
            self.session.open(MessageBox, f"Download failed.\n{err or 'No response.'}\nThe current version is untouched.", MessageBox.TYPE_ERROR)
            return
        ok, msg, _new_ver = verify_update_payload(data)
        if ok:
            ok, msg = install_update_payload(data)
        else:
            msg += "\nThe current version is untouched."
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO if ok else MessageBox.TYPE_ERROR)

    def clear_all_reminders(self):
        del WATCHLIST[:]
        save_watchlist()
        self.rebuild_visual_list()
        self.session.open(MessageBox, "Watchlist cleared.", type=MessageBox.TYPE_INFO, timeout=2)

    def toggle_discovery_mode(self):
        new_state = not config.plugins.WhatToWatch.discovery_mode.value
        config.plugins.WhatToWatch.discovery_mode.value = new_state
        config.plugins.WhatToWatch.discovery_mode.save()
        configfile.save()
        if monitor:
            monitor.restart_discovery_timer()
        self.session.open(MessageBox, "Discovery Mode Enabled!" if new_state else "Discovery Mode Disabled.", type=MessageBox.TYPE_INFO, timeout=1)

    # ------------------------------------------------------------------ OK / reminders
    def ok_pressed(self):
        item = self._cur()
        if not item:
            return
        now = int(time.time())
        existing = find_reminder(item[4], item[5])
        if item[5] <= now and not existing and self.current_sat_filter != "watchlist":
            # Event has already started: zap directly to channel without closing UI
            if self.act_zap(item):
                self["hint_bar"].setText(f"Tuned to {item[1]} • Press EXIT when done")
            return

        menu = [("Zap to Channel Now", "zap")]
        if existing:
            menu.append(("Remove Reminder", "rem"))
        elif item[5] > now:
            menu.append(("Set Reminder", "rem"))
        if HAVE_RECORDTIMER and item[5] > now:
            menu.append(("Record this programme", "rec"))
        menu.append(("Programme details", "info"))
        self.session.openWithCallback(lambda c: self.ok_menu_cb(c, item), ChoiceBox, title="Action", list=menu)

    def ok_menu_cb(self, choice, data):
        if not choice:
            return
        if choice[1] == "zap":
            if self.act_zap(data):
                self["hint_bar"].setText(f"Tuned to {data[1]} • Press EXIT when done")
        elif choice[1] == "rem":
            self.act_remind(data)
        elif choice[1] == "rec":
            self.act_record(data)
        elif choice[1] == "info":
            self.act_details(data)

    def add_reminder(self):
        item = self._cur()
        if item:
            self.act_remind(item)

    def save_reminder(self, choice, data):
        self._save_reminder(choice, data)

    def show_sort_menu(self):
        self.session.openWithCallback(self.sort_cb, ChoiceBox, title="Select Sorting Mode", list=[
            ("Sort by Category & Start Time", "category"),
            ("Sort by Channel Name", "channel"),
            ("Sort by Start Time", "time")
        ])

    def sort_cb(self, c):
        if c:
            self.sort_mode = c[1]
            config.plugins.WhatToWatch.sort_mode.value = c[1]
            config.plugins.WhatToWatch.sort_mode.save()
            configfile.save()
            self.rebuild_visual_list()

    def show_sat_menu(self):
        event_sat_counts = {}
        for x in self.full_list:
            sat = x.get("sat")
            if sat:
                event_sat_counts[sat] = event_sat_counts.get(sat, 0) + 1

        service_sats = set()
        for s in self.raw_services:
            if s and s[0]:
                sp = get_sat_position(str(s[0]))
                if sp:
                    service_sats.add(sp)

        core_sats = ["13.0E", "16.0E", "19.2E", "7.0W", "26.0E", "28.2E", "42.0E", "30.0W", "0.8W", "4.0W", "5.0W", "9.0E", "23.5E", "39.0E", "52.0E", "IPTV"]
        all_sats = set(event_sat_counts.keys()) | service_sats | set(core_sats)

        def _sort_key(s):
            has_events = 0 if event_sat_counts.get(s, 0) > 0 else (1 if s in service_sats else 2)
            try:
                if s == "IPTV":
                    return (has_events, 9999)
                if s == "DVB-T/C":
                    return (has_events, 9998)
                if s.endswith("E"):
                    return (has_events, float(s[:-1]))
                if s.endswith("W"):
                    return (has_events, 360.0 - float(s[:-1]))
            except Exception:
                pass
            return (has_events, 5000)

        sorted_sats = sorted(list(all_sats), key=_sort_key)
        menu = [("All Satellites / All Sources", "all"), (f"★ MY WATCHLIST ({len(WATCHLIST)})", "watchlist")]
        for s in sorted_sats:
            name = get_sat_display_name(s)
            cnt = event_sat_counts.get(s, 0)
            label = f"{name} ({cnt} events)" if cnt > 0 else name
            menu.append((label, s))

        self.session.openWithCallback(lambda c: self.sat_cb(c), ChoiceBox, title="Select Satellite Filter", list=menu)

    def sat_cb(self, c):
        if c:
            self.current_sat_filter = None if c[1] == "all" else c[1]
            self.rebuild_visual_list()
            self["event_list"].moveToIndex(0)

# --- GLOBAL MONITOR INSTANCE ---
monitor = None

def sessionstart(reason, **kwargs):
    if "session" in kwargs:
        global monitor
        monitor = WTWMonitor(kwargs["session"])

def main(session, **kwargs):
    global monitor
    if monitor is None:
        try:
            monitor = WTWMonitor(session)
        except Exception:
            pass
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name=f"What to Watch v{VERSION}", description="EPG plugin by reali22", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name="What to Watch", description="EPG plugin by reali22", where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)
    ]

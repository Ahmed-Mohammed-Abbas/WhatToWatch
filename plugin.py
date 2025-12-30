# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 3.5 (Always-On Discovery)
#  Author: reali22
#  Description: Discovery Mode runs in background (even when closed).
# ============================================================================

import os
import time
import json
import random
from sys import version_info
from urllib.parse import quote

# --- Enigma2 Imports ---
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, ConfigSelection, getConfigListEntry
from enigma import eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, quitMainloop, eTimer, ePicLoad
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

# --- Configuration ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.api_key = ConfigText(default="", visible_width=50, fixed_size=False)
config.plugins.WhatToWatch.enable_ai = ConfigYesNo(default=False)
config.plugins.WhatToWatch.transparent_bg = ConfigYesNo(default=False)
config.plugins.WhatToWatch.discovery_mode = ConfigYesNo(default=False)

# --- Constants ---
VERSION = "3.3"
AUTHOR = "reali22"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")
SOUND_FILE = os.path.join(PLUGIN_PATH, "pop.mp3") 
PINNED_FILE = "/etc/enigma2/wtw_pinned.json"
WATCHLIST_FILE = "/etc/enigma2/wtw_watchlist.json"
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
    "/usr/share/enigma2/picon_50x30/"
]

# --- CATEGORY DATABASE ---
CATEGORIES_ORDER = ["Documentary", "Sports", "Movies", "Series", "Kids", "News", "Religious", "Music"]

CATEGORIES = {
    "Documentary": (
        ["discovery", "doc", "history", "nat geo", "wild", "planet", "animal", "science", "investigation", "crime", 
         "tlc", "quest", "arte", "geographic", "explorer", "viasat", "iasat history", "iasat nature", "ad nat geo", 
         "oman cultural", "al jazeera doc", "dw doc"], 
        ["documentary", "wildlife", "expedition", "universe", "factory", "engineering", "survival", "ancient", "nature", "safari", "space"]
    ),
    "Sports": (
        ["sport", "soccer", "football", "bein", "sky sport", "bt sport", "euro", "dazn", "ssc", "alkass", "on sport", 
         "nba", "racing", "motogp", "f1", "wwe", "ufc", "fight", "box", "arena", "tsn", "super", "calcio", 
         "canal+ sport", "eleven", "polsat sport", "ad sport", "dubai sport", "sharjah sport", "ksa sport", 
         "kuwait sport", "iraq sport", "oman sport", "bahrain sport", "yass", "al ahly", "zamalek", 
         "ss-1", "ss-2", "ss-3", "ss-4", "fightbox", "setanta", "match!", "espn"], 
        ["match", "vs", "league", "cup", "final", "premier", "bundesliga", "laliga", "serie a", "champion", 
         "derby", "racing", "grand prix", "tournament", "live", "olymp"]
    ),
    "Movies": (
        ["movie", "film", "cinema", "cine", "kino", "aflam", "hbo", "mbc 2", "mbc max", "mbc action", 
         "rotana cinema", "rotana classic", "zee aflam", "b4u", "osn movies", "amc", "fox movies", "paramount", 
         "tcm", "star movies", "dubai one", "mpc", "art aflam", "lbc movies", "top movies", "scare", "imagine", 
         "c1 action", "c1", "fx", "mgm"], 
        ["starring", "directed by", "thriller", "action", "comedy", "drama", "horror", "sci-fi", "romance", "adventure", "movie"]
    ),
    "Series": (
        ["drama", "series", "serial", "novela", "mosalsalat", "hikaya", "mbc 1", "mbc 4", "mbc drama", "mbc masr", 
         "rotana drama", "zee alwan", "zee tv", "colors", "sony", "fox", "axn", "tlc", "lbc", "mtv lebanon", 
         "al jadeed", "syria drama", "amman", "roya", "dmc", "cbc", "osn series", "netflix", "al hayah", "panorama drama", 
         "beta", "sama", "lan", "usv"], 
        ["episode", "season", "series", "soap", "telenovela", "sitcom"]
    ),
    "Kids": (
        ["cartoon", "cn ", "nick", "disney", "boomerang", "spacetoon", "mbc 3", "pogo", "majid", "dreamworks", 
         "baby", "kika", "gulli", "clan", "baraem", "jeem", "ajyal", "cbeebies", "fix & foxi", "jimjam", "semsem", 
         "toggolino", "super rtl", "koko"], 
        ["animation", "anime", "sponge", "patrol", "mouse", "tom and jerry", "princess", "lego", "toon"]
    ),
    "News": (
        ["news", "cnn", "bbc", "jazeera", "alarabiya", "skynews", "cnbc", "bloomberg", "weather", "rt ", "france 24", 
         "trt", "dw", "al hadath", "al hurra", "al sharqiya", "al sumaria", "rudaw", "kurdistan", "news 24", 
         "al ekhbariya", "al araby", "alghad"], 
        ["journal", "report", "briefing", "update", "headline", "breaking", "bulletin", "politics"]
    ),
    "Religious": (
        ["quran", "sunnah", "iqraa", "resalah", "majd", "karma", "miracle", "ctv", "aghapy", "noursat", "god tv", 
         "ewtn", "peace tv", "huda", "al nas", "al rahama", "al insan", "karbala", "al kafeel", "al maaref", 
         "al kawthar", "safb"], 
        ["prayer", "mass", "worship", "gospel", "recitation", "bible", "quran", "sheikh", "church", "khutbah"]
    ),
    "Music": (
        ["music", "mtv", "vh1", "melody", "mazzika", "rotana clip", "wanasah", "aghani", "4fun", "eska", "polo", 
         "kiss", "dance", "hits", "arabica", "mezzo", "trace", "box hits", "kerrang"], 
        ["concert", "videoclip", "hits", "playlist", "songs", "top 10", "top 20"]
    )
}

# --- GLOBAL HELPERS ---
PICON_CACHE = {}
PINNED_CHANNELS = []
WATCHLIST = []
# NEW: Global Cache for Background Monitor
GLOBAL_SERVICE_LIST = []

def load_data():
    global PINNED_CHANNELS, WATCHLIST
    if os.path.exists(PINNED_FILE):
        try:
            with open(PINNED_FILE, 'r') as f: PINNED_CHANNELS = json.load(f)
        except: PINNED_CHANNELS = []
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r') as f: WATCHLIST = json.load(f)
        except: WATCHLIST = []

def save_pinned():
    try:
        with open(PINNED_FILE, 'w') as f: json.dump(PINNED_CHANNELS, f)
    except: pass

def save_watchlist():
    try:
        with open(WATCHLIST_FILE, 'w') as f: json.dump(WATCHLIST, f)
    except: pass

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

def load_png(path):
    if os.path.exists(path): return loadPNG(path)
    return None

def get_picon_resized(service_ref, channel_name, genre_nibble):
    ref_clean = service_ref.strip().replace(":", "_").rstrip("_")
    if ref_clean in PICON_CACHE: return PICON_CACHE[ref_clean]
    
    found_path = None
    candidates = [ref_clean + ".png", ref_clean.replace("1_0_19", "1_0_1") + ".png", channel_name.strip() + ".png"]
    for path in PICON_PATHS:
        if os.path.exists(path):
            for name in candidates:
                full_path = os.path.join(path, name)
                if os.path.exists(full_path):
                    found_path = full_path
                    break
        if found_path: break
    
    if found_path:
        try:
            sc = ePicLoad()
            sc.setPara((50, 30, 1, 1, False, 1, "#00000000"))
            if sc.startDecode(found_path, 0, 0, False) == 0:
                ptr = sc.getData()
                if ptr:
                    PICON_CACHE[ref_clean] = ptr
                    return ptr
        except: pass

    icon_map = {0x1: "movies.png", 0x2: "news.png", 0x3: "show.png", 0x4: "sports.png", 0x5: "kids.png", 0x6: "music.png", 0x7: "arts.png", 0x9: "science.png"}
    icon_name = icon_map.get(genre_nibble, "default.png")
    fallback = loadPNG(os.path.join(ICON_PATH, icon_name)) or loadPNG(os.path.join(ICON_PATH, "default.png"))
    PICON_CACHE[ref_clean] = fallback
    return fallback

def classify_enhanced(channel_name, event_name):
    ch_clean = channel_name.lower()
    evt_clean = event_name.lower() if event_name else ""
    if "xxx" in ch_clean or "18+" in ch_clean: return None
    for cat in CATEGORIES_ORDER:
        ch_kws, evt_kws = CATEGORIES.get(cat, ([], []))
        for kw in ch_kws:
            if kw in ch_clean: return cat
    for cat in CATEGORIES_ORDER:
        ch_kws, evt_kws = CATEGORIES.get(cat, ([], []))
        for kw in evt_kws:
            if kw in evt_clean: return cat
    return "General"

def get_sat_position(ref_str):
    if ref_str.startswith("4097:") or ref_str.startswith("5001:"): return "IPTV"
    try:
        parts = ref_str.split(":")
        if len(parts) > 6:
            ns_val = int(parts[6], 16)
            orb_pos = (ns_val >> 16) & 0xFFFF
            if orb_pos == 0xFFFF: return "DVB-T/C"
            if orb_pos > 1800: return f"{(3600 - orb_pos)/10.0:.1f}W"
            else: return f"{orb_pos/10.0:.1f}E"
    except: pass
    return ""

def translate_text(text, target_lang='en'):
    try:
        encoded = quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded}"
        cmd = f"curl -k -s -A 'Mozilla/5.0' '{url}' > /tmp/wtw_trans.json"
        os.system(cmd)
        if os.path.exists("/tmp/wtw_trans.json"):
            with open("/tmp/wtw_trans.json", "r") as f:
                data = json.load(f)
            return data[0][0][0] if data and data[0] else text
    except: pass
    return text

# --- DISCOVERY TOAST (Dismissible) ---
class DiscoveryToast(Screen):
    skin = """
        <screen position="10,10" size="400,120" title="Discovery" flags="wfNoBorder" backgroundColor="#40000000">
            <eLabel position="0,0" size="400,120" backgroundColor="#20101010" zPosition="-1" />
            <widget name="header" position="10,5" size="380,30" font="Regular;22" halign="left" foregroundColor="#00ff00" backgroundColor="#20101010" transparent="1" />
            <widget name="channel" position="10,40" size="380,30" font="Regular;24" halign="left" foregroundColor="#ffffff" backgroundColor="#20101010" transparent="1" />
            <widget name="event" position="10,75" size="380,40" font="Regular;20" halign="left" foregroundColor="#a0a0a0" backgroundColor="#20101010" transparent="1" />
        </screen>
    """
    
    def __init__(self, session, category, channel_name, event_name):
        Screen.__init__(self, session)
        self["header"] = Label(f"Now Showing: {category}")
        self["channel"] = Label(channel_name)
        self["event"] = Label(event_name)
        
        self["actions"] = ActionMap(["OkCancelActions"], {
            "cancel": self.close,
            "ok": self.close
        }, -1)
        
        self.timer = eTimer()
        self.timer.callback.append(self.close)
        self.timer.start(10000, True)

# --- TOP NOTIFICATION SCREEN (Reminders) ---
class WTWNotification(Screen):
    skin = """
        <screen position="center,30" size="1000,100" title="Reminder" flags="wfNoBorder" backgroundColor="#40000000">
            <eLabel position="0,0" size="1000,100" backgroundColor="#20101010" zPosition="-1" />
            <eLabel text="!" position="20,20" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="#ffff00" backgroundColor="#20101010" transparent="1" />
            <widget name="message" position="100,10" size="880,80" font="Regular;28" valign="center" halign="left" foregroundColor="#ffffff" backgroundColor="#20101010" transparent="1" />
        </screen>
    """
    def __init__(self, session, message, timeout=5):
        Screen.__init__(self, session)
        self["message"] = Label(message)
        self.timer = eTimer()
        self.timer.callback.append(self.close)
        self.timer.start(timeout * 1000, True)

# --- BACKGROUND MONITOR (Updated with Discovery Logic) ---
class WTWMonitor:
    def __init__(self, session):
        self.session = session
        
        # 1. Reminder Timer
        self.timer = eTimer()
        self.timer.callback.append(self.check_reminders)
        self.timer.start(60000, False)
        
        # 2. Discovery Timer (Runs even if plugin is closed)
        self.discovery_timer = eTimer()
        self.discovery_timer.callback.append(self.discovery_tick)
        self.discovery_cat_idx = 0
        
        # Start scanning services for cache in background
        self.scan_timer = eTimer()
        self.scan_timer.callback.append(self.build_cache)
        self.scan_timer.start(5000, True) # Start building cache 5s after boot

        if config.plugins.WhatToWatch.discovery_mode.value:
            self.discovery_timer.start(60000, False)

    def build_cache(self):
        # Fetch all services once to populate GLOBAL_SERVICE_LIST
        global GLOBAL_SERVICE_LIST
        service_handler = eServiceCenter.getInstance()
        ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        bouquet_root = eServiceReference(ref_str)
        bouquet_list = service_handler.list(bouquet_root)
        if not bouquet_list: return

        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content: return

        temp_list = []
        for bouquet_entry in bouquet_content:
            services = service_handler.list(eServiceReference(bouquet_entry[0]))
            if services:
                temp_list.extend(services.getContent("SN", True))
                if len(temp_list) > 2000: break # Limit to avoid memory issues
        
        GLOBAL_SERVICE_LIST = temp_list

    def discovery_tick(self):
        if not config.plugins.WhatToWatch.discovery_mode.value: return
        if not GLOBAL_SERVICE_LIST: return

        # Rotate Category
        cat_name = CATEGORIES_ORDER[self.discovery_cat_idx]
        self.discovery_cat_idx = (self.discovery_cat_idx + 1) % len(CATEGORIES_ORDER)
        
        # Optimization: Don't scan everything. Pick random samples.
        epg_cache = eEPGCache.getInstance()
        now = int(time.time())
        found_item = None
        
        # Try 50 random channels to find a match for the current category
        for _ in range(50):
            s_ref, s_name = random.choice(GLOBAL_SERVICE_LIST)
            if "::" in s_ref: continue
            
            try:
                event = epg_cache.lookupEventTime(eServiceReference(s_ref), now)
                if not event: continue
                
                event_name = event.getEventName()
                cat = classify_enhanced(s_name, event_name)
                
                if cat == cat_name:
                    found_item = (cat, s_name, event_name)
                    break
            except: continue
            
        if found_item:
            self.session.open(DiscoveryToast, found_item[0], found_item[1], found_item[2])

    def check_reminders(self):
        now = int(time.time())
        dirty = False
        to_remove = []
        for item in WATCHLIST:
            target_time = item['notify_at']
            if now >= target_time and now < target_time + 120:
                self.trigger_event(item)
                if item.get('repeat', False):
                    item['start_time'] += 604800
                    item['notify_at'] += 604800
                    dirty = True
                else:
                    to_remove.append(item)
            elif now > target_time + 3600:
                if not item.get('repeat', False):
                    to_remove.append(item)
        for item in to_remove:
            if item in WATCHLIST:
                WATCHLIST.remove(item)
                dirty = True
        if dirty: save_watchlist()

    def trigger_event(self, item):
        if os.path.exists(SOUND_FILE):
            try:
                cmd = f"gst-launch-1.0 playbin uri=file://{SOUND_FILE} audio-sink=\"alsasink\" volume=0.8 > /dev/null 2>&1 &"
                os.system(cmd)
            except: pass
        
        msg = f"{item['evt']}\nOn: {item['name']}"
        
        if item['type'] == 'zap':
            self.session.open(WTWNotification, message=msg + "\nAuto-Tuning...", timeout=5)
            try: self.session.nav.playService(eServiceReference(item['ref']))
            except: pass
        else:
            self.session.open(WTWNotification, message=msg, timeout=8)

# --- List Builder ---
def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, genre_nibble, start_time, duration, show_progress=True):
    icon_pixmap = get_picon_resized(service_ref, channel_name, genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    
    display_name = channel_name
    if sat_info: display_name = f"{channel_name} ({sat_info})"
    
    is_pinned = service_ref in PINNED_CHANNELS
    is_reminder = any(w['ref'] == service_ref and w['start_time'] == start_time for w in WATCHLIST)
    
    if is_reminder:
        name_color = 0x00FF00 
        display_name = f"🔔 {display_name}"
    elif is_pinned:
        name_color = 0xFFFF00 
        display_name = f"★ {display_name}"
    else:
        name_color = 0xFFFFFF 

    short_cat = category_name[:5]
    progress_str = ""
    progress_color = 0xFFFFFF
    
    if show_progress and duration > 0:
        current_time = int(time.time())
        if start_time <= current_time < (start_time + duration):
            percent = int(((current_time - start_time) / float(duration)) * 100)
            if percent > 100: percent = 100
            progress_str = f"{percent}%"
            if percent <= 35: progress_color = 0x00FF00 
            elif percent <= 66: progress_color = 0xFFFF00 
            else: progress_color = 0xFF4040 

    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration),
        MultiContentEntryText(pos=(15, 5), size=(60, 25), font=2, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryPixmapAlphaTest(pos=(80, 15), size=(50, 30), png=icon_pixmap),
        MultiContentEntryText(pos=(135, 5), size=(390, 25), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=name_color, color_sel=name_color),
        MultiContentEntryText(pos=(135, 30), size=(390, 25), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(530, 5), size=(110, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=short_cat, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(530, 30), size=(110, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
    ]
    return res

# --- Configuration Screen ---
class WhatToWatchSetup(ConfigListScreen, Screen):
    skin = """<screen position="center,center" size="800,400" title="Settings">
            <widget name="config" position="10,10" size="780,300" scrollbarMode="showOnDemand" />
            <widget name="key_green" position="10,360" size="780,40" zPosition="1" font="Regular;24" halign="center" valign="center" backgroundColor="#1f771f" transparent="0" />
        </screen>"""
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session)
        self.createSetup()
        self["key_green"] = Label("Save Settings")
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "green": self.save, "save": self.save, "cancel": self.cancel, "ok": self.save
        }, -2)

    def createSetup(self):
        self.list = [
            getConfigListEntry("Enable AI Categorization (Gemini)", config.plugins.WhatToWatch.enable_ai),
            getConfigListEntry("Gemini API Key", config.plugins.WhatToWatch.api_key),
            getConfigListEntry("Transparent Background", config.plugins.WhatToWatch.transparent_bg),
            getConfigListEntry("Enable Discovery Mode", config.plugins.WhatToWatch.discovery_mode)
        ]
        self["config"].list = self.list
        self["config"].setList(self.list)

    def save(self):
        for x in self["config"].list: x[1].save()
        config.plugins.WhatToWatch.save()
        
        # Sync Global Monitor with new settings
        if monitor:
            if config.plugins.WhatToWatch.discovery_mode.value:
                monitor.discovery_timer.start(60000, False)
            else:
                monitor.discovery_timer.stop()
                
        self.session.open(MessageBox, "Settings Saved.", MessageBox.TYPE_INFO, timeout=2)
        self.close()

    def cancel(self):
        for x in self["config"].list: x[1].cancel()
        self.close()

# --- Main Screen ---
class WhatToWatchScreen(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        is_transparent = config.plugins.WhatToWatch.transparent_bg.value
        bg_color = "#80000000" if is_transparent else "#ff181818"
        
        self.skin = f"""<screen position="0,0" size="700,860" title="What to Watch" flags="wfNoBorder" backgroundColor="#00000000">
            <eLabel position="0,0" size="700,860" backgroundColor="{bg_color}" zPosition="-1" />
            <eLabel text="What to Watch" position="10,10" size="680,40" font="Regular;28" halign="center" valign="center" foregroundColor="#00ff00" backgroundColor="{bg_color}" transparent="1" />
            <eLabel text="By {AUTHOR}" position="10,45" size="680,20" font="Regular;16" halign="center" valign="center" foregroundColor="#505050" backgroundColor="{bg_color}" transparent="1" />
            <widget name="status_label" position="10,70" size="680,30" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <widget name="event_list" position="5,110" size="690,630" scrollbarMode="showOnDemand" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,760" size="25,25" alphatest="on" />
            <widget name="key_red" position="55,760" size="280,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="20,800" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="55,800" size="280,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="350,760" size="25,25" alphatest="on" />
            <widget name="key_green" position="385,760" size="280,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="350,800" size="25,25" alphatest="on" />
            <widget name="key_blue" position="385,800" size="280,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="{bg_color}" transparent="1" />
            <widget name="info_bar" position="10,830" size="680,20" font="Regular;16" halign="center" valign="center" foregroundColor="#ffff00" backgroundColor="{bg_color}" transparent="1" />
        </screen>"""

        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["event_list"].l.setFont(0, gFont("Regular", 26)) 
        self["event_list"].l.setFont(1, gFont("Regular", 22)) 
        self["event_list"].l.setFont(2, gFont("Regular", 20)) 
        self["event_list"].l.setItemHeight(80)
        
        self["status_label"] = Label("Loading...")
        self["key_red"] = Label("Time: Now")
        self["key_green"] = Label("Satellite")
        self["key_yellow"] = Label("Category")
        self["key_blue"] = Label("Options")
        self["info_bar"] = Label("Press EPG/INFO to Translate")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.ok_pressed,
            "ok_long": self.add_reminder,
            "cancel": self.close,
            "red": self.toggle_time,
            "green": self.show_sat_menu,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
            "info": self.show_translated_info,  
        }, -1)

        self.full_list = []
        self.raw_services = [] 
        self.processed_count = 0
        self.current_filter = None
        self.current_sat_filter = None
        self.use_favorites = False
        self.sort_mode = 'category'
        self.time_offset = 0
        self.process_timer = eTimer()
        self.process_timer.callback.append(self.process_batch)
        self.onLayoutFinish.append(self.start_full_rescan)

    def start_full_rescan(self):
        self.process_timer.stop()
        self.full_list = []
        self.raw_services = []
        self.processed_count = 0
        self["event_list"].setList([])
        
        time_text = "Now" if self.time_offset == 0 else f"+{self.time_offset//3600}h"
        self["status_label"].setText(f"Loading channels ({time_text})...")
        
        service_handler = eServiceCenter.getInstance()
        ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' if self.use_favorites else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        bouquet_root = eServiceReference(ref_str)
        bouquet_list = service_handler.list(bouquet_root)
        if not bouquet_list: return

        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content: return

        for bouquet_entry in bouquet_content:
            services = service_handler.list(eServiceReference(bouquet_entry[0]))
            if services:
                self.raw_services.extend(services.getContent("SN", True))
                if len(self.raw_services) > 2000: break

        self["status_label"].setText(f"Scanning {len(self.raw_services)} channels...")
        self.process_timer.start(10, False)

    def process_batch(self):
        if not self.raw_services:
            self.process_timer.stop()
            self["status_label"].setText(f"Done. {len(self.full_list)} events found.")
            return

        BATCH_SIZE = 10 
        epg_cache = eEPGCache.getInstance()
        query_time = int(time.time()) + self.time_offset
        seen_channels = {f"{x['name']}_{x['sat']}" for x in self.full_list}

        for _ in range(BATCH_SIZE):
            if not self.raw_services: break
            s_ref, s_name = self.raw_services.pop(0)
            if "::" in s_ref: continue
            
            try:
                sat_pos = get_sat_position(s_ref)
                unique_id = f"{s_name}_{sat_pos}"
                if unique_id in seen_channels: continue
                seen_channels.add(unique_id)

                event = epg_cache.lookupEventTime(eServiceReference(s_ref), query_time)
                if not event: continue
                event_name = event.getEventName()
                category = classify_enhanced(s_name, event_name)
                if not category: continue 

                entry_data = {
                    "cat": category, "name": s_name, "sat": sat_pos, "evt": event_name, 
                    "ref": s_ref, "nib": 0, "start": event.getBeginTime(), "dur": event.getDuration()
                }
                self.full_list.append(entry_data)
            except: continue

        self.processed_count += BATCH_SIZE
        if self.processed_count % 50 == 0: self.rebuild_visual_list()

    def rebuild_visual_list(self):
        if self.current_sat_filter == "watchlist":
            filtered = []
            for w in WATCHLIST:
                filtered.append({
                    "cat": "Watch", "name": w['name'], "sat": "", "evt": w['evt'],
                    "ref": w['ref'], "nib": 0, "start": w['start_time'], "dur": 0
                })
            filtered.sort(key=lambda x: x["start"])
        else:
            filtered = [x for x in self.full_list if (not self.current_filter or x["cat"] == self.current_filter) and (not self.current_sat_filter or x["sat"] == self.current_sat_filter)]
            filtered.sort(key=lambda x: (
                0 if x["ref"] in PINNED_CHANNELS else 1, 
                x["start"], 
                x["name"]
            ))
        
        show_prog = (self.time_offset == 0) and (self.current_sat_filter != "watchlist")
        res_list = []
        for item in filtered:
            res_list.append(build_list_entry(item["cat"], item["name"], item["sat"], item["evt"], item["ref"], item["nib"], item["start"], item["dur"], show_prog))
        self["event_list"].setList(res_list)
        
        if self.current_sat_filter == "watchlist":
            status_text = f"Filter: ★ MY WATCHLIST | Reminders: {len(filtered)}"
        else:
            filter_info = []
            if self.current_filter: filter_info.append(self.current_filter)
            if self.current_sat_filter: filter_info.append(self.current_sat_filter)
            if self.time_offset > 0: filter_info.append(f"+{self.time_offset//3600}h")
            if filter_info:
                status_text = f"Filter: {', '.join(filter_info)} | Channels: {len(filtered)}"
            else:
                status_text = f"All Channels | Total: {len(filtered)}"
        
        self["status_label"].setText(status_text)

    def toggle_time(self):
        times = [0, 3600, 7200, 14400, 21600, 28800]
        try:
            current_idx = times.index(self.time_offset)
            next_idx = (current_idx + 1) % len(times)
        except:
            next_idx = 0
        
        self.time_offset = times[next_idx]
        label_map = {0: "Time: Now", 3600: "Time: +1h", 7200: "Time: +2h", 14400: "Time: +4h", 21600: "Time: +6h", 28800: "Time: +8h"}
        self["key_red"].setText(label_map.get(self.time_offset, "Time"))
        self.start_full_rescan()

    def cycle_category(self):
        cats = sorted(list(set([x["cat"] for x in self.full_list])))
        if not cats: return
        if not self.current_filter: self.current_filter = cats[0]
        else:
            try:
                idx = cats.index(self.current_filter)
                self.current_filter = cats[idx + 1] if idx < len(cats) - 1 else None
            except: self.current_filter = None
        self.rebuild_visual_list()

    def show_translated_info(self):
        cur = self["event_list"].getCurrent()
        if cur: self.session.open(MessageBox, translate_text(cur[0][3]), type=MessageBox.TYPE_INFO)

    def show_options_menu(self):
        disc_state = config.plugins.WhatToWatch.discovery_mode.value
        disc_text = "Disable Discovery Mode" if disc_state else "Enable Discovery Mode"
        
        menu = [("Set Reminder / Auto-Tune", "rem"), 
                ("Pin/Unpin Channel", "pin"), 
                ("Clear All Reminders", "clear"), 
                (disc_text, "toggle_disc"),
                ("Toggle Source", "src"), 
                ("Refresh List", "refresh"), 
                ("Sort", "sort"), 
                ("Update", "upd"), 
                ("Settings", "ai")]
        self.session.openWithCallback(self.menu_cb, ChoiceBox, title="Options", list=menu)

    def menu_cb(self, choice):
        if not choice: return
        c = choice[1]
        if c == "rem": self.add_reminder()
        elif c == "pin":
            cur = self["event_list"].getCurrent()
            if cur:
                toggle_pin(cur[0][4])
                self.rebuild_visual_list()
        elif c == "clear": self.clear_all_reminders()
        elif c == "toggle_disc": self.toggle_discovery_mode()
        elif c == "src": self.use_favorites = not self.use_favorites; self.start_full_rescan()
        elif c == "refresh": self.start_full_rescan()
        elif c == "sort": self.show_sort_menu()
        elif c == "upd": self.check_updates()
        elif c == "ai": self.session.open(WhatToWatchSetup)

    def toggle_discovery_mode(self):
        new_state = not config.plugins.WhatToWatch.discovery_mode.value
        config.plugins.WhatToWatch.discovery_mode.value = new_state
        config.plugins.WhatToWatch.save()
        
        if new_state:
            # Re-sync global monitor if it exists
            global monitor
            if monitor:
                monitor.discovery_timer.start(60000, False)
            self.session.open(MessageBox, "Discovery Mode Enabled!", type=MessageBox.TYPE_INFO, timeout=2)
        else:
            if monitor:
                monitor.discovery_timer.stop()
            self.session.open(MessageBox, "Discovery Mode Disabled.", type=MessageBox.TYPE_INFO, timeout=2)

    def clear_all_reminders(self):
        global WATCHLIST
        WATCHLIST = []
        save_watchlist()
        self.session.open(MessageBox, "All reminders cleared!", type=MessageBox.TYPE_INFO, timeout=2)
        self.rebuild_visual_list()

    def ok_pressed(self):
        cur = self["event_list"].getCurrent()
        if not cur: return
        data = cur[0] 
        existing = [x for x in WATCHLIST if x['ref'] == data[4] and x['start_time'] == data[5]]
        is_future = data[5] > int(time.time())
        menu = [("Zap to Channel Now", "zap")]
        if existing:
            menu.append(("Remove Reminder", "remove_rem"))
        elif is_future:
            menu.append(("Set Reminder / Auto-Tune", "rem"))
        self.session.openWithCallback(lambda c: self.ok_menu_cb(c, data), ChoiceBox, title="Action Selection", list=menu)

    def ok_menu_cb(self, choice, data):
        if not choice: return
        action = choice[1]
        if action == "zap":
            self.session.nav.playService(eServiceReference(data[4]))
        elif action == "remove_rem":
            self.add_reminder() 
        elif action == "rem":
            self.add_reminder() 

    def add_reminder(self):
        cur = self["event_list"].getCurrent()
        if not cur: return
        data = cur[0] 
        
        existing = [x for x in WATCHLIST if x['ref'] == data[4] and x['start_time'] == data[5]]
        if existing:
            WATCHLIST.remove(existing[0])
            save_watchlist()
            self.session.open(MessageBox, "Reminder Removed!", type=MessageBox.TYPE_INFO, timeout=2)
            self.rebuild_visual_list()
            return

        if data[5] <= int(time.time()):
            self.session.open(MessageBox, "Program already started! Cannot set reminder.", type=MessageBox.TYPE_ERROR)
            return
            
        menu = [("Notification (At Start)", ("notify", 0)), ("Notification (5 min before)", ("notify", 300)), ("Notification (10 min before)", ("notify", 600)), ("Auto-Tune (Zap at Start)", ("zap", 0)), ("Weekly Notification", ("notify_week", 0))]
        self.session.openWithCallback(lambda c: self.save_reminder(c, data), ChoiceBox, title="Set Reminder", list=menu)

    def save_reminder(self, choice, data):
        if not choice: return
        type_code, offset = choice[1]
        repeat = (type_code == "notify_week")
        if repeat: type_code = "notify"
        entry = {"ref": data[4], "name": data[1], "evt": data[3], "start_time": data[5], "notify_at": data[5] - offset, "type": type_code, "repeat": repeat}
        WATCHLIST.append(entry)
        save_watchlist()
        self.session.open(MessageBox, "Reminder Set!", type=MessageBox.TYPE_INFO, timeout=3)
        self.rebuild_visual_list()

    def show_sort_menu(self):
        self.session.openWithCallback(self.sort_cb, ChoiceBox, title="Sort", list=[("Category", "category"), ("Channel", "channel"), ("Time", "time")])

    def sort_cb(self, c):
        if c: self.sort_mode = c[1]; self.rebuild_visual_list()

    def show_sat_menu(self):
        sats = sorted(list(set([x["sat"] for x in self.full_list if x["sat"]])))
        menu = [("All", "all"), ("★ MY WATCHLIST", "watchlist")] + [(s, s) for s in sats]
        self.session.openWithCallback(lambda c: self.sat_cb(c), ChoiceBox, title="Select Satellite", list=menu)

    def sat_cb(self, c):
        if c: 
            self.current_sat_filter = None if c[1] == "all" else c[1]
            self.rebuild_visual_list()

    def check_updates(self):
        try:
            os.system(f"wget --no-check-certificate -qO /tmp/wtw_ver {UPDATE_URL_VER}")
            if os.path.exists("/tmp/wtw_ver"):
                with open("/tmp/wtw_ver") as f:
                    if f.read().strip() > VERSION:
                        self.session.openWithCallback(self.do_upd, MessageBox, "Update Available!", MessageBox.TYPE_YESNO)
                    else:
                        self.session.open(MessageBox, "Up to date.", MessageBox.TYPE_INFO)
        except: pass

    def do_upd(self, c):
        if c:
            os.system(f"wget --no-check-certificate -qO {PLUGIN_FILE_PATH} {UPDATE_URL_PY}")
            quitMainloop(3)

    def zap_channel(self):
        cur = self["event_list"].getCurrent()
        if cur: self.session.nav.playService(eServiceReference(cur[0][4]))

# --- GLOBAL MONITOR INSTANCE ---
monitor = None

def sessionstart(reason, **kwargs):
    if "session" in kwargs:
        global monitor
        monitor = WTWMonitor(kwargs["session"])

def main(session, **kwargs): session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name=f"What to Watch v{VERSION}", description="EPG plugin by reali22", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart)
    ]

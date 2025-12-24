# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 2.0 (Stable Lite)
#  Description: Fast, lightweight, offline categorization.
#               Removes complex scoring for maximum stability on Python 3.
# ============================================================================

import os
import time
import re
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from enigma import eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, loadPNG, eTimer, quitMainloop
from Plugins.Plugin import PluginDescriptor

# --- CONSTANTS ---
VERSION = "2.0"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

# --- CONFIGURATION ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.show_picons = ConfigYesNo(default=True)
config.plugins.WhatToWatch.search_limit = ConfigText(default="1500", fixed_size=False)

# --- SIMPLE KEYWORDS (No Weights) ---
# Format: "Category": [List of keywords]
KEYWORDS = {
    "Sports": ["sport", "espn", "bein", "nba", "racing", "f1", "football", "soccer", "tennis", "cricket", "ssc", "alkass", "match", "arena", "calcio", "league", "cup", "bundesliga", "laliga", "serie a", "uefa", "fifa", "wwe", "ufc", "boxing", "goal"],
    "Kids": ["cartoon", "disney", "nick", "boomerang", "cbeebies", "baby", "junior", "kika", "gulli", "clan", "spacetoon", "mbc 3", "majid", "dreamworks", "pogo", "anime", "animation", "sponge", "patrol", "mouse"],
    "News": ["news", "cnn", "bbc", "jazeera", "skynews", "cnbc", "bloomberg", "weather", "rt", "france 24", "euronews", "trt", "dw", "watania", "ekhbariya", "alaraby", "alghad", "hadath", "arabia"],
    "Movies": ["movie", "film", "cinema", "cine", "kino", "hbo", "sky cinema", "mbc 2", "mbc max", "rotana cinema", "zee aflam", "osn movies", "amc", "fox movies", "starring", "thriller", "action", "comedy", "drama", "romance"],
    "Documentary": ["discovery", "history", "nat geo", "wild", "planet", "science", "investigation", "crime", "tlc", "quest", "arte", "phoenix", "explorer", "documentary", "wildlife", "safari", "space"],
    "Music": ["music", "mtv", "vh1", "kiss", "magic", "dance", "hits", "4fun", "eska", "trace", "rotana clip", "mazzika", "melody", "wanasah", "concert", "videoclip", "songs"],
    "Religious": ["quran", "sunnah", "iqraa", "resalah", "majd", "god tv", "ewtn", "bible", "church", "islam", "makkah", "madinah", "ctv", "aghapy", "prayer", "worship"]
}

ADULT_KEYWORDS = ["xxx", "18+", "porn", "adult", "sex", "erotic", "brazzers", "hustler", "playboy", "dorcel", "vivid", "redlight"]

# --- CORE HELPERS ---
def clean_text(text):
    if not text: return ""
    text = re.sub(r'(\x0B|\x19|\x86|\x87)', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.lower().strip()

def classify_event_simple(channel_name, event_title, event_desc):
    # 1. Safety Check
    combined = f"{channel_name} {event_title}".lower()
    for x in ADULT_KEYWORDS:
        if x in combined: return None, None

    # 2. Channel Name Match (High Priority)
    ch_clean = clean_text(channel_name)
    for cat, kws in KEYWORDS.items():
        for k in kws:
            if k in ch_clean:
                return get_cat_data(cat)

    # 3. Event Title Match (Medium Priority)
    evt_clean = clean_text(event_title)
    for cat, kws in KEYWORDS.items():
        for k in kws:
            if k in evt_clean:
                return get_cat_data(cat)

    # 4. Fallback
    return ("Shows", 0x3)

def get_cat_data(cat_name):
    # Returns (Name, Icon_Nibble)
    mapping = {
        "Movies": 0x1, "News": 0x2, "Shows": 0x3, "Sports": 0x4,
        "Kids": 0x5, "Music": 0x6, "Religious": 0x7, "Documentary": 0x9
    }
    return (cat_name, mapping.get(cat_name, 0x0))

def get_genre_icon(nibble):
    icon_map = {0x1: "movies.png", 0x2: "news.png", 0x3: "show.png", 0x4: "sports.png", 0x5: "kids.png", 0x6: "music.png", 0x7: "arts.png", 0x9: "science.png"}
    icon_name = icon_map.get(nibble, "default.png")
    png_path = os.path.join(ICON_PATH, icon_name)
    if os.path.exists(png_path): return loadPNG(png_path)
    return None

def get_sat_position(ref_str):
    if "4097:" in ref_str or "5001:" in ref_str: return "IPTV"
    try:
        parts = ref_str.split(":")
        if len(parts) > 6:
            ns = int(parts[6], 16)
            pos = (ns >> 16) & 0xFFFF
            if pos == 0xFFFF: return "DVB-T/C"
            if pos > 1800: return f"{(3600-pos)/10.0:.1f}W"
            else: return f"{pos/10.0:.1f}E"
    except: pass
    return ""

# --- LIST BUILDER ---
def build_list_entry(cat, name, sat, evt, ref, nib, start, dur):
    icon_pixmap = get_genre_icon(nib)
    
    if start > 0:
        t_struct = time.localtime(start)
        time_str = f"{t_struct.tm_hour:02d}:{t_struct.tm_min:02d}"
    else:
        time_str = "--:--"

    display_name = name
    if sat: display_name += f"  ({sat})"

    progress_str = ""
    progress_col = 0xFFFFFF
    if dur > 0:
        now = int(time.time())
        if start <= now < start + dur:
            pct = int(((now - start) / float(dur)) * 100)
            progress_str = f"{pct}%"
            if pct > 80: progress_col = 0xFF4040
            elif pct < 20: progress_col = 0x00FF00
    
    return [
        (cat, name, sat, evt, ref, start, dur), 
        MultiContentEntryPixmapAlphaTest(pos=(10, 8), size=(50, 50), png=icon_pixmap),
        MultiContentEntryText(pos=(70, 3), size=(550, 30), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF),
        MultiContentEntryText(pos=(70, 35), size=(550, 28), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=evt, color=0xA0A0A0),
        MultiContentEntryText(pos=(630, 3), size=(110, 60), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF),
        MultiContentEntryText(pos=(750, 3), size=(190, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=cat, color=0xFFFF00),
        MultiContentEntryText(pos=(950, 3), size=(100, 60), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_col),
    ]

# --- MAIN SCREEN ---
class WhatToWatchScreen(Screen):
    skin = """
        <screen position="center,center" size="1080,720" title="What to Watch 2.0">
            <widget name="status" position="15,10" size="1050,40" font="Regular;26" halign="center" valign="center" foregroundColor="#00ff00" />
            <widget name="list" position="15,60" size="1050,580" scrollbarMode="showOnDemand" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="15,660" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="225,660" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="435,660" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="645,660" size="40,40" alphatest="on" />
            
            <widget name="key_red" position="60,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
            <widget name="key_green" position="270,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
            <widget name="key_yellow" position="480,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
            <widget name="key_blue" position="690,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["list"].l.setFont(0, gFont("Regular", 28))
        self["list"].l.setFont(1, gFont("Regular", 24))
        self["list"].l.setItemHeight(65)
        
        self["status"] = Label("Initializing...")
        self["key_red"] = Label("Sort: Category")
        self["key_green"] = Label("Refresh")
        self["key_yellow"] = Label("Show Details")
        self["key_blue"] = Label("Bouquet")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions"], {
            "ok": self.zap,
            "cancel": self.close,
            "red": self.toggle_sort,
            "green": self.reload,
            "yellow": self.show_details,
            "blue": self.toggle_source,
            "menu": self.open_config
        }, -1)

        self.full_data = []
        self.raw_channels = []
        self.processed_count = 0
        self.use_favorites = True
        
        self.sort_modes = ["Category", "Channel Name", "Time"]
        self.sort_index = 0

        self.timer = eTimer()
        self.timer.callback.append(self.process_batch)
        self.onLayoutFinish.append(self.reload)

    def reload(self):
        self.timer.stop()
        self.full_data = []
        self.raw_channels = []
        self.processed_count = 0
        self["list"].setList([])
        
        src = "Favorites" if self.use_favorites else "All Channels"
        self["status"].setText(f"Loading {src}...")
        
        serviceHandler = eServiceCenter.getInstance()
        ref = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' if self.use_favorites else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        root = eServiceReference(ref)
        bouquet_list = serviceHandler.list(root)
        
        if bouquet_list:
            bouquets = bouquet_list.getContent("SN", True)
            for b in bouquets:
                s_list = serviceHandler.list(eServiceReference(b[0]))
                if s_list:
                    self.raw_channels.extend(s_list.getContent("SN", True))
                    try:
                        limit = int(config.plugins.WhatToWatch.search_limit.value)
                        if len(self.raw_channels) > limit: break
                    except: pass
        
        self["status"].setText(f"Scanning {len(self.raw_channels)} channels...")
        self.timer.start(10, False)

    def process_batch(self):
        if not self.raw_channels:
            self.timer.stop()
            self.apply_sort()
            return

        epg_cache = eEPGCache.getInstance()
        now = int(time.time())
        batch_size = 20 # Increased for v2.0 speed
        
        for _ in range(batch_size):
            if not self.raw_channels: break
            s_ref, s_name = self.raw_channels.pop(0)
            
            if "::" in s_ref: continue
            
            try:
                check_ref = s_ref
                if s_ref.startswith("4097:") or s_ref.startswith("5001:"):
                    parts = s_ref.split(":")
                    if len(parts) > 7:
                        check_ref = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"

                event = epg_cache.lookupEventTime(eServiceReference(check_ref), -1)
                if not event: continue

                evt_name = event.getEventName() or ""
                evt_desc = event.getShortDescription() or ""
                
                start = event.getBeginTime()
                dur = event.getDuration()
                
                if start + dur < now: continue 
                
                # Simple Classification
                cat, nib = classify_event_simple(s_name, evt_name, evt_desc)
                if not cat: continue

                sat_info = get_sat_position(s_ref)
                
                self.full_data.append({
                    "cat": cat, "name": s_name, "sat": sat_info,
                    "evt": evt_name, "desc": evt_desc, "ref": s_ref,
                    "nib": nib, "start": start, "dur": dur
                })
            except: continue

        self.processed_count += batch_size
        if self.processed_count % 100 == 0:
            self["status"].setText(f"Scanning... Found {len(self.full_data)} events")

    def toggle_sort(self):
        self.sort_index = (self.sort_index + 1) % len(self.sort_modes)
        self.apply_sort()

    def apply_sort(self):
        mode = self.sort_modes[self.sort_index]
        self["key_red"].setText(f"Sort: {mode}")
        self["status"].setText(f"Found {len(self.full_data)} Events. Sorted by {mode}")
        
        data = self.full_data[:]

        if mode == "Category":
            data.sort(key=lambda x: (x["cat"], x["name"]))
        elif mode == "Channel Name":
            data.sort(key=lambda x: x["name"])
        elif mode == "Time":
            data.sort(key=lambda x: x["start"])

        res = []
        for item in data:
            res.append(build_list_entry(
                item["cat"], item["name"], item["sat"], item["evt"], 
                item["ref"], item["nib"], item["start"], item["dur"]
            ))
        self["list"].setList(res)

    def show_details(self):
        cur = self["list"].getCurrent()
        if not cur: return
        ref = cur[0][4]
        evt_name = cur[0][3]
        
        desc = "No description."
        for x in self.full_data:
            if x["ref"] == ref and x["evt"] == evt_name:
                desc = x["desc"]
                break
        self.session.open(MessageBox, f"{evt_name}\n\n{desc}", MessageBox.TYPE_INFO)

    def toggle_source(self):
        self.use_favorites = not self.use_favorites
        self["key_blue"].setText("All Channels" if self.use_favorites else "Favorites")
        self.reload()

    def zap(self):
        cur = self["list"].getCurrent()
        if cur:
            self.session.nav.playService(eServiceReference(cur[0][4]))
            self.close()

    def open_config(self):
        self.session.open(WhatToWatchConfig)

# --- CONFIG SCREEN ---
class WhatToWatchConfig(ConfigListScreen, Screen):
    skin = """
        <screen position="center,center" size="600,300" title="Settings">
            <widget name="config" position="10,10" size="580,240" scrollbarMode="showOnDemand" />
            <widget name="key_green" position="10,260" size="580,30" font="Regular;22" halign="center" foregroundColor="#00ff00" transparent="1" />
        </screen>
    """
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.list = []
        ConfigListScreen.__init__(self, self.list, session=session)
        
        self.list.append(getConfigListEntry("Channel Scan Limit", config.plugins.WhatToWatch.search_limit))
        self.list.append(getConfigListEntry("Show Picons", config.plugins.WhatToWatch.show_picons))
        
        self["config"].list = self.list
        self["config"].setList(self.list)
        self["key_green"] = Label("Press OK to Save")
        
        self["actions"] = ActionMap(["SetupActions"], {
            "save": self.save,
            "ok": self.save,
            "cancel": self.cancel
        }, -2)

    def save(self):
        for x in self["config"].list: x[1].save()
        self.close()

    def cancel(self):
        for x in self["config"].list: x[1].cancel()
        self.close()

def main(session, **kwargs):
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [PluginDescriptor(name="What to Watch", description="Fast Offline Browser", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 1.5 (Classic / Clean)
#  Description: The original simple version. 
#               No AI. No Weights. No Complex Sorting.
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
VERSION = "1.5"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

# --- CONFIGURATION ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.show_picons = ConfigYesNo(default=True)
config.plugins.WhatToWatch.search_limit = ConfigText(default="1500", fixed_size=False)

# --- SIMPLE KEYWORD LISTS ---
# No weights, just simple lists.
KEYWORDS = {
    "Sports": ["sport", "espn", "bein", "nba", "racing", "f1", "football", "soccer", "tennis", "cricket", "ssc", "alkass", "match", "arena", "calcio", "league", "cup", "bundesliga", "laliga", "serie a", "uefa", "fifa", "wwe", "ufc", "boxing"],
    "Kids": ["cartoon", "disney", "nick", "boomerang", "cbeebies", "baby", "junior", "kika", "gulli", "clan", "spacetoon", "mbc 3", "majid", "dreamworks", "pogo", "anime", "animation"],
    "News": ["news", "cnn", "bbc", "jazeera", "skynews", "cnbc", "bloomberg", "weather", "rt", "france 24", "euronews", "trt", "dw", "watania", "ekhbariya", "alaraby", "alghad", "hadath", "arabia"],
    "Movies": ["movie", "film", "cinema", "cine", "kino", "hbo", "sky cinema", "mbc 2", "mbc max", "rotana cinema", "zee aflam", "osn movies", "amc", "fox movies", "starring", "action", "comedy", "drama", "romance"],
    "Documentary": ["discovery", "history", "nat geo", "wild", "planet", "science", "investigation", "crime", "tlc", "quest", "arte", "phoenix", "explorer", "documentary", "wildlife"],
    "Music": ["music", "mtv", "vh1", "kiss", "magic", "dance", "hits", "4fun", "eska", "trace", "rotana clip", "mazzika", "melody", "wanasah", "concert"],
    "Religious": ["quran", "sunnah", "iqraa", "resalah", "majd", "god tv", "ewtn", "bible", "church", "islam", "makkah", "madinah", "ctv", "aghapy"]
}

# --- HELPERS ---
def clean_text(text):
    if not text: return ""
    text = re.sub(r'(\x0B|\x19|\x86|\x87)', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.lower().strip()

def classify_simple(text):
    # Returns (CategoryName, IconNibble)
    text = clean_text(text)
    
    # Check strict lists
    for cat, kws in KEYWORDS.items():
        for k in kws:
            if k in text:
                return get_cat_data(cat)
                
    # Default
    return ("Shows", 0x3)

def get_cat_data(cat_name):
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
    
    return [
        (cat, name, sat, evt, ref, start, dur), 
        MultiContentEntryPixmapAlphaTest(pos=(10, 8), size=(50, 50), png=icon_pixmap),
        MultiContentEntryText(pos=(70, 3), size=(550, 30), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF),
        MultiContentEntryText(pos=(70, 35), size=(550, 28), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=evt, color=0xA0A0A0),
        MultiContentEntryText(pos=(630, 3), size=(110, 60), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF),
        MultiContentEntryText(pos=(750, 3), size=(190, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=cat, color=0xFFFF00),
    ]

# --- MAIN SCREEN ---
class WhatToWatchScreen(Screen):
    skin = """
        <screen position="center,center" size="1080,720" title="What to Watch 1.5">
            <widget name="status" position="15,10" size="1050,40" font="Regular;26" halign="center" valign="center" foregroundColor="#00ff00" />
            <widget name="list" position="15,60" size="1050,580" scrollbarMode="showOnDemand" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="15,660" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="225,660" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="435,660" size="40,40" alphatest="on" />
            
            <widget name="key_red" position="60,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
            <widget name="key_green" position="270,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
            <widget name="key_blue" position="480,660" size="150,40" font="Regular;22" halign="left" valign="center" transparent="1" />
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
        self["key_blue"] = Label("Bouquet")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.zap,
            "cancel": self.close,
            "red": self.toggle_sort,
            "green": self.reload,
            "blue": self.toggle_source
        }, -1)

        self.full_data = []
        self.raw_channels = []
        self.processed_count = 0
        self.use_favorites = True
        self.sort_mode = "Category" # Simple toggle: Category <-> Name

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
        batch_size = 25
        
        for _ in range(batch_size):
            if not self.raw_channels: break
            s_ref, s_name = self.raw_channels.pop(0)
            
            if "::" in s_ref: continue
            
            try:
                # Check Refs
                check_ref = s_ref
                if s_ref.startswith("4097:") or s_ref.startswith("5001:"):
                    parts = s_ref.split(":")
                    if len(parts) > 7:
                        check_ref = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"

                event = epg_cache.lookupEventTime(eServiceReference(check_ref), -1)
                if not event: continue

                evt_name = event.getEventName() or ""
                start = event.getBeginTime()
                dur = event.getDuration()
                
                if start + dur < now: continue 
                
                # Simple Classification (Name + Title combined)
                cat, nib = classify_simple(s_name + " " + evt_name)
                
                sat_info = get_sat_position(s_ref)
                
                self.full_data.append({
                    "cat": cat, "name": s_name, "sat": sat_info,
                    "evt": evt_name, "ref": s_ref,
                    "nib": nib, "start": start, "dur": dur
                })
            except: continue

        self.processed_count += batch_size
        if self.processed_count % 100 == 0:
            self["status"].setText(f"Scanning... Found {len(self.full_data)} events")

    def toggle_sort(self):
        if self.sort_mode == "Category": self.sort_mode = "Name"
        else: self.sort_mode = "Category"
        self.apply_sort()

    def apply_sort(self):
        self["key_red"].setText(f"Sort: {self.sort_mode}")
        self["status"].setText(f"Found {len(self.full_data)} Events.")
        
        data = self.full_data[:]

        if self.sort_mode == "Category":
            data.sort(key=lambda x: (x["cat"], x["name"]))
        else:
            data.sort(key=lambda x: x["name"])

        res = []
        for item in data:
            res.append(build_list_entry(
                item["cat"], item["name"], item["sat"], item["evt"], 
                item["ref"], item["nib"], item["start"], item["dur"]
            ))
        self["list"].setList(res)

    def toggle_source(self):
        self.use_favorites = not self.use_favorites
        self["key_blue"].setText("All Channels" if self.use_favorites else "Favorites")
        self.reload()

    def zap(self):
        cur = self["list"].getCurrent()
        if cur:
            self.session.nav.playService(eServiceReference(cur[0][4]))
            self.close()

def main(session, **kwargs):
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [PluginDescriptor(name="What to Watch", description="Classic EPG Browser", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

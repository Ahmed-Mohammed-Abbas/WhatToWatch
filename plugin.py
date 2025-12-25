# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 2.8 (Perfect Fit Edition)
#  Author: reali22
#  Description: optimized layout. No cut-off text. Smart abbreviations.
# ============================================================================

import os
import time
import re
import json
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
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, getConfigListEntry
from enigma import eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, quitMainloop, eTimer
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

# --- Configuration ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.api_key = ConfigText(default="", visible_width=50, fixed_size=False)
config.plugins.WhatToWatch.enable_ai = ConfigYesNo(default=False)

# --- Constants ---
VERSION = "2.8"
AUTHOR = "reali22"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- SMART CATEGORY DATABASE ---
CATEGORIES = {
    "Kids": (
        ["cartoon", "cn ", "nick", "disney", "boomerang", "spacetoon", "mbc 3", "pogo", "majid", "dreamworks", "baby", "kika", "gulli", "clan", "cbeebies", "citv", "pop", "tiny", "junior", "jeem", "baraem", "fix & foxi", "duck"],
        ["cartoon", "animation", "anime", "sponge", "patrol", "mouse", "tom and jerry", "pig", "bear", "tales", "princess", "dragon", "lego", "pokemon"]
    ),
    "Sports": (
        ["sport", "espn", "bein", "sky sport", "bt sport", "euro", "dazn", "ssc", "alkass", "ad sport", "dubai sport", "on sport", "nba", "racing", "motogp", "f1", "wwe", "ufc", "fight", "box", "arena", "tsn", "super", "calcio", "canal+ sport", "eleven", "polsat sport", "match!", "setanta", "extreme"],
        [" vs ", "live:", "match", "cup", "league", "football", "soccer", "racing", "tournament", "championship", "derby", "qualifying", "final", "bundesliga", "laliga", "serie a", "premier league"]
    ),
    "News": (
        ["news", "cnn", "bbc", "jazeera", "alarabiya", "hadath", "skynews", "cnbc", "bloomberg", "weather", "rt ", "france 24", "trt", "dw", "watania", "ekhbariya", "alaraby", "alghad", "asharq", "lbc", "tagesschau", "welt", "n-tv", "rai news", "24h"],
        ["news", "journal", "report", "briefing", "update", "headline", "politics", "weather", "parliament", "breaking"]
    ),
    "Documentary": (
        ["doc", "history", "historia", "nat geo", "national geographic", "wild", "planet", "animal", "science", "investigation", "crime", "discovery", "tlc", "quest", "arte", "phoenix", "explorer", "smithsonian", "eden", "viasat", "focus", "dmax"],
        ["documentary", "wildlife", "expedition", "universe", "factory", "engineering", "survival", "ancient", "world war", "nature", "safari", "shark", "space"]
    ),
    "Movies": (
        ["movie", "film", "cinema", "cine", "kino", "aflam", "hbo", "sky cinema", "mbc 2", "mbc max", "mbc action", "mbc bollywood", "rotana cinema", "rotana classic", "zee aflam", "b4u", "osn movies", "amc", "fox movies", "paramount", "tcm", "filmbox", "sony max", "star movies", "wb tv"],
        ["starring", "directed by", "thriller", "action", "comedy", "drama", "horror", "sci-fi", "romance", "adventure", "blockbuster"]
    ),
    "Religious": (
        ["quran", "sunnah", "iqraa", "resalah", "majd", "karma", "miracle", "ctv", "aghapy", "noursat", "god tv", "ewtn", "bibel", "makkah", "madinah", "islam", "church", "peace tv", "huda", "guide"],
        ["prayer", "mass", "worship", "gospel", "recitation", "bible", "quran", "sheikh"]
    ),
    "Music": (
        ["music", "mtv", "vh1", "melody", "mazzika", "rotana clip", "wanasah", "aghani", "4fun", "eska", "polo", "kiss", "dance", "hits", "trace", "mezzo", "classica", "nrj", "radio", "fm"],
        ["concert", "videoclip", "hits", "top 40", "playlist", "songs", "symphony", "orchestra", "festival"]
    ),
    "Shows": (
        ["drama", "series", "mosalsalat", "hikaya", "mbc 1", "mbc 4", "mbc drama", "mbc masr", "rotana drama", "rotana khalijia", "zee alwan", "zee tv", "star plus", "colors", "sony", "sky one", "sky atlantic", "fox", "comedy central", "syfy", "axn", "novelas", "bet", "e!"],
        ["episode", "season", "series", "show", "reality", "soap", "telenovela", "sitcom"]
    )
}

ADULT_KEYWORDS = ["xxx", "18+", "porn", "adult", "sex", "erotic", "brazzers", "hustler", "playboy", "dorcel", "vivid", "redlight"]

# --- Global Helpers ---
def load_png(path):
    if os.path.exists(path): return loadPNG(path)
    return None

def get_genre_icon(nibble):
    icon_map = {0x1: "movies.png", 0x2: "news.png", 0x3: "show.png", 0x4: "sports.png", 0x5: "kids.png", 0x6: "music.png", 0x7: "arts.png", 0x9: "science.png"}
    icon_name = icon_map.get(nibble, "default.png")
    return load_png(os.path.join(ICON_PATH, icon_name)) or load_png(os.path.join(ICON_PATH, "default.png"))

def is_adult(text):
    if not text: return False
    t = text.lower()
    return any(k in t for k in ADULT_KEYWORDS) and "essex" not in t and "sussex" not in t

# --- ENHANCED CLASSIFICATION LOGIC ---
def classify_enhanced(channel_name, event_name):
    ch_clean = channel_name.lower()
    evt_clean = event_name.lower() if event_name else ""
    
    if is_adult(ch_clean) or is_adult(evt_clean): return None, None

    # TIER 1: Channel Name Lock
    for cat, (ch_kws, _) in CATEGORIES.items():
        for kw in ch_kws:
            if kw in ch_clean: return get_cat_data(cat)

    # TIER 2: Event Name Scan
    for cat, (_, evt_kws) in CATEGORIES.items():
        for kw in evt_kws:
            if kw in evt_clean: return get_cat_data(cat)

    return ("General", 0x3)

def get_cat_data(cat_name):
    mapping = {
        "Movies": 0x1, "News": 0x2, "Shows": 0x3, "Sports": 0x4,
        "Kids": 0x5, "Music": 0x6, "Religious": 0x7, "Documentary": 0x9
    }
    return (cat_name, mapping.get(cat_name, 0x0))

def clean_channel_name_fuzzy(name):
    n = name.lower()
    n = re.sub(r'\b(hd|sd|fhd|4k|uhd|hevc)\b', '', n)
    n = re.sub(r'\+\d+', '', n) 
    return re.sub(r'[\W_]+', '', n)

def get_sat_position(ref_str):
    if ref_str.startswith("4097:") or ref_str.startswith("5001:"): return "IPTV"
    try:
        parts = ref_str.split(":")
        if len(parts) > 6:
            ns_val = int(parts[6], 16)
            orb_pos = (ns_val >> 16) & 0xFFFF
            if orb_pos == 0xFFFF: return "DVB-T/C"
            if orb_pos == 0: return ""
            if orb_pos > 1800: return f"{(3600 - orb_pos)/10.0:.1f}W"
            else: return f"{orb_pos/10.0:.1f}E"
    except: pass
    return ""

def translate_text(text, target_lang='en'):
    if not text or len(text) < 2: return "No description."
    if any('\u0600' <= char <= '\u06FF' for char in text[:30]): return text
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

def abbreviate_category(cat_name):
    subs = {
        "Documentary": "Doc", "Religious": "Rel.", "Sports": "Spt",
        "Movies": "Mov", "Entertainment": "Ent.", "General": "Gen",
        "Kids": "Kid", "Music": "Mus", "News": "News"
    }
    return subs.get(cat_name, cat_name[:4])

# --- List Builder (Optimized Layout) ---
def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, genre_nibble, start_time, duration, show_progress=True):
    icon_pixmap = get_genre_icon(genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    
    display_name = channel_name
    if sat_info:
        display_name = f"{channel_name} ({sat_info})"

    short_cat = abbreviate_category(category_name)

    progress_str = ""
    progress_color = 0xFFFFFF 
    if show_progress and duration > 0:
        current_time = int(time.time())
        if start_time <= current_time < (start_time + duration):
            percent = int(((current_time - start_time) / float(duration)) * 100)
            if percent > 100: percent = 100
            progress_str = f"{percent}%"
            if percent > 85: progress_color = 0xFF4040 
            elif percent > 10: progress_color = 0x00FF00
    
    # --- CALCULATED LAYOUT (Width 555px) ---
    # Col 1: Icon (50px)
    # Col 2: Time (60px)
    # Col 3: Texts (375px)
    # Col 4: Info (60px)
    
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration),
        
        # 1. Icon (Far Left)
        MultiContentEntryPixmapAlphaTest(pos=(5, 12), size=(50, 50), png=icon_pixmap),
        
        # 2. Time (Next to Icon)
        MultiContentEntryText(pos=(60, 5), size=(60, 25), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),

        # 3. Channel Name (Middle)
        MultiContentEntryText(pos=(125, 5), size=(365, 25), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        
        # 4. Event Name (Middle Below)
        MultiContentEntryText(pos=(125, 30), size=(365, 25), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        
        # 5. Progress % (Top Right Edge)
        MultiContentEntryText(pos=(495, 5), size=(55, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
        
        # 6. Abbreviated Category (Bottom Right Edge)
        MultiContentEntryText(pos=(495, 30), size=(55, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=short_cat, color=0xFFFF00, color_sel=0xFFFF00),
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
            getConfigListEntry("Gemini API Key", config.plugins.WhatToWatch.api_key)
        ]
        self["config"].list = self.list
        self["config"].setList(self.list)

    def save(self):
        for x in self["config"].list: x[1].save()
        config.plugins.WhatToWatch.save()
        self.close()

    def cancel(self):
        for x in self["config"].list: x[1].cancel()
        self.close()

# --- The GUI Screen ---
class WhatToWatchScreen(Screen):
    # Position: Left Sidebar (0,0). Width=555. Height=720.
    skin = f"""
        <screen position="0,0" size="555,720" title="What to Watch" flags="wfNoBorder" backgroundColor="#20000000">
            <eLabel position="0,0" size="555,720" backgroundColor="#181818" zPosition="-1" />
            
            <eLabel text="What to Watch" position="10,10" size="535,40" font="Regular;28" halign="center" valign="center" foregroundColor="#00ff00" backgroundColor="#181818" transparent="1" />
            <eLabel text="By {AUTHOR}" position="10,45" size="535,20" font="Regular;16" halign="center" valign="center" foregroundColor="#505050" backgroundColor="#181818" transparent="1" />

            <widget name="status_label" position="10,70" size="535,30" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <widget name="event_list" position="5,110" size="545,500" scrollbarMode="showOnDemand" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,620" size="25,25" alphatest="on" />
            <widget name="key_red" position="55,620" size="210,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="20,660" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="55,660" size="210,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/green.png" position="280,620" size="25,25" alphatest="on" />
            <widget name="key_green" position="315,620" size="210,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/blue.png" position="280,660" size="25,25" alphatest="on" />
            <widget name="key_blue" position="315,660" size="210,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <widget name="info_bar" position="10,690" size="535,20" font="Regular;16" halign="center" valign="center" foregroundColor="#ffff00" backgroundColor="#181818" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        
        # RESIZED FONTS FOR BETTER FIT (28 Title / 24 Detail)
        self["event_list"].l.setFont(0, gFont("Regular", 28)) 
        self["event_list"].l.setFont(1, gFont("Regular", 24)) 
        self["event_list"].l.setItemHeight(80)
        
        self["status_label"] = Label("Loading...")
        self["key_red"] = Label("Satellite")
        self["key_green"] = Label("Refresh")
        self["key_yellow"] = Label("Category")
        self["key_blue"] = Label("Options")
        self["info_bar"] = Label("Press EPG/INFO to Translate")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.zap_channel,
            "cancel": self.close,
            "red": self.show_sat_menu,
            "green": self.start_full_rescan,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
            "info": self.show_translated_info,  
            "epg": self.show_translated_info,   
        }, -1)

        self.full_list = []
        self.raw_services = [] 
        self.processed_count = 0
        self.unique_channels = {}
        
        self.current_filter = None
        self.current_sat_filter = None
        self.use_favorites = False
        self.sort_mode = 'category'
        self.lookup_time = int(time.time())
        
        self.process_timer = eTimer()
        self.process_timer.callback.append(self.process_batch)
        self.onLayoutFinish.append(self.start_full_rescan)

    def start_full_rescan(self):
        self.process_timer.stop()
        self.full_list = []
        self.unique_channels = {}
        self.raw_services = []
        self.processed_count = 0
        self["event_list"].setList([])
        
        source_text = "Favorites" if self.use_favorites else "All Channels"
        self["status_label"].setText(f"Loading {source_text}...")
        
        service_handler = eServiceCenter.getInstance()
        ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' if self.use_favorites else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        bouquet_root = eServiceReference(ref_str)
        bouquet_list = service_handler.list(bouquet_root)
        
        if not bouquet_list:
            self["status_label"].setText("Error: No Bouquets.")
            return

        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content: return

        for bouquet_entry in bouquet_content:
            bouquet_ref = eServiceReference(bouquet_entry[0])
            services = service_handler.list(bouquet_ref)
            if services:
                self.raw_services.extend(services.getContent("SN", True))
                if len(self.raw_services) > 2000: break

        self["status_label"].setText(f"Scanning {len(self.raw_services)} channels...")
        self.lookup_time = int(time.time())
        self.process_timer.start(10, False)

    def process_batch(self):
        if not self.raw_services:
            self.process_timer.stop()
            self["status_label"].setText(f"Done. {len(self.full_list)} events.")
            return

        BATCH_SIZE = 10 
        epg_cache = eEPGCache.getInstance()

        for _ in range(BATCH_SIZE):
            if not self.raw_services: break
            s_ref, s_name = self.raw_services.pop(0)
            
            if "::" in s_ref or "---" in s_name: continue
            
            try:
                service_reference = eServiceReference(s_ref)
                event = epg_cache.lookupEventTime(service_reference, self.lookup_time)
                
                if not event and (s_ref.startswith("4097:") or s_ref.startswith("5001:")):
                    parts = s_ref.split(":")
                    if len(parts) > 7:
                        clean_str = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"
                        event = epg_cache.lookupEventTime(eServiceReference(clean_str), self.lookup_time)

                if not event: continue
                event_name = event.getEventName()
                if not event_name: continue

                category, nibble = classify_enhanced(s_name, event_name)
                if category is None: continue 

                clean_ch = clean_channel_name_fuzzy(s_name)
                is_hd = "hd" in s_name.lower()
                start_time = event.getBeginTime()
                duration = event.getDuration()
                sat_info = get_sat_position(s_ref)
                
                entry_data = {
                    "cat": category, "name": s_name, "sat": sat_info, "evt": event_name, 
                    "ref": s_ref, "nib": nibble, "start": start_time, "dur": duration, 
                    "hd": is_hd, "clean": clean_ch
                }

                if clean_ch in self.unique_channels:
                    existing = self.unique_channels[clean_ch]
                    if is_hd and not existing["hd"]:
                        self.unique_channels[clean_ch] = entry_data
                else:
                    self.unique_channels[clean_ch] = entry_data

            except: continue

        self.processed_count += BATCH_SIZE
        if self.processed_count % 50 == 0:
            self.rebuild_visual_list()
            self["status_label"].setText(f"Scanning... {len(self.full_list)} found")

    def rebuild_visual_list(self):
        raw_list = list(self.unique_channels.values())
        filtered = []
        for item in raw_list:
            if self.current_filter and item["cat"] != self.current_filter: continue
            if self.current_sat_filter and item["sat"] != self.current_sat_filter: continue
            filtered.append(item)

        if self.sort_mode == 'category': filtered.sort(key=lambda x: (x["cat"], x["name"]))
        elif self.sort_mode == 'channel': filtered.sort(key=lambda x: x["name"])
        elif self.sort_mode == 'time': filtered.sort(key=lambda x: x["start"])

        self.full_list = []
        for item in filtered:
            entry = build_list_entry(
                item["cat"], item["name"], item["sat"], item["evt"], item["ref"], 
                item["nib"], item["start"], item["dur"], True
            )
            self.full_list.append(entry)

        self["event_list"].setList(self.full_list)

    def cycle_category(self):
        cats = sorted(list(set([v["cat"] for v in self.unique_channels.values()])))
        if not cats: return
        if not self.current_filter: self.current_filter = cats[0]
        else:
            try:
                idx = cats.index(self.current_filter)
                if idx < len(cats) - 1: self.current_filter = cats[idx + 1]
                else: self.current_filter = None
            except: self.current_filter = None
        self.rebuild_visual_list()

    def show_translated_info(self):
        current_selection = self["event_list"].getCurrent()
        if not current_selection: return
        payload = current_selection[0]
        self.session.open(MessageBox, "Translating...", type=MessageBox.TYPE_INFO, timeout=1)
        epg_cache = eEPGCache.getInstance()
        text = payload[3]
        try:
            event = epg_cache.lookupEventTime(eServiceReference(payload[4]), payload[5])
            if event:
                s = event.getShortDescription() or ""
                e = event.getExtendedDescription() or ""
                text = f"{payload[3]}\n\n{s}\n{e}"
        except: pass
        res = translate_text(text)
        self.session.open(MessageBox, res, type=MessageBox.TYPE_INFO)

    def show_options_menu(self):
        menu = [("Toggle Source", "src"), ("Sort", "sort"), ("Update", "upd"), ("AI Settings", "ai")]
        self.session.openWithCallback(self.menu_cb, ChoiceBox, title="Options", list=menu)

    def menu_cb(self, choice):
        if not choice: return
        c = choice[1]
        if c == "src": self.use_favorites = not self.use_favorites; self.start_full_rescan()
        elif c == "sort": self.show_sort_menu()
        elif c == "upd": self.check_updates()
        elif c == "ai": self.session.open(WhatToWatchSetup)

    def show_sat_menu(self):
        sats = sorted(list(set([v["sat"] for v in self.unique_channels.values() if v["sat"]])))
        menu = [("All", "all")] + [(s, s) for s in sats]
        self.session.openWithCallback(self.sat_cb, ChoiceBox, title="Select Satellite", list=menu)

    def sat_cb(self, c):
        if c: 
            self.current_sat_filter = None if c[1] == "all" else c[1]
            self.rebuild_visual_list()

    def show_sort_menu(self):
        self.session.openWithCallback(self.sort_cb, ChoiceBox, title="Sort", list=[("Category", "category"), ("Channel", "channel"), ("Time", "time")])

    def sort_cb(self, c):
        if c: self.sort_mode = c[1]; self.rebuild_visual_list()

    def check_updates(self):
        self.session.open(MessageBox, "Checking...", type=MessageBox.TYPE_INFO, timeout=2)
        os.system(f"wget -qO /tmp/v {UPDATE_URL_VER}")
        if os.path.exists("/tmp/v"):
            with open("/tmp/v") as f: 
                if f.read().strip() > VERSION:
                    self.session.openWithCallback(self.do_upd, MessageBox, "Update Available!", MessageBox.TYPE_YESNO)
                else:
                    self.session.open(MessageBox, "Up to date.", MessageBox.TYPE_INFO)

    def do_upd(self, c):
        if c:
            os.system(f"wget -qO {PLUGIN_FILE_PATH} {UPDATE_URL_PY}")
            self.session.open(MessageBox, "Restarting...", type=MessageBox.TYPE_INFO, timeout=2)
            time.sleep(1); quitMainloop(3)

    def zap_channel(self):
        cur = self["event_list"].getCurrent()
        if cur: self.session.nav.playService(eServiceReference(cur[0][4]))

def main(session, **kwargs): session.open(WhatToWatchScreen)
def Plugins(**kwargs): return [PluginDescriptor(name=f"What to Watch v{VERSION}", description="EPG Browser by reali22", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

# ============================================================================
#  Plugin: What to Watch
#  Author: reali22
#  Version: 1.0
#  Description: Advanced EPG Browser with categorization, satellite filtering,
#               smart deduplication, and Auto-Update.
#  GitHub: https://github.com/Ahmed-Mohammed-Abbas/WhatToWatch
# ============================================================================

import os
import time
import re
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from enigma import eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, loadPNG, quitMainloop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

# --- Constants ---
VERSION = "1.0"
AUTHOR = "reali22"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- 1. Setup Paths & Icons ---
# Standard Enigma2 path resolution
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

def get_genre_icon(nibble):
    icon_map = {
        0x1: "movies.png", 0x2: "news.png", 0x3: "show.png", 0x4: "sports.png",
        0x5: "kids.png", 0x6: "music.png", 0x7: "arts.png", 0x8: "social.png",
        0x9: "science.png", 0xA: "leisure.png"
    }
    icon_name = icon_map.get(nibble, "default.png")
    png_path = os.path.join(ICON_PATH, icon_name)
    if os.path.exists(png_path): return loadPNG(png_path)
    default_path = os.path.join(ICON_PATH, "default.png")
    if os.path.exists(default_path): return loadPNG(default_path)
    return None

# --- 2. Advanced Categorization ---
def classify_by_channel_name(channel_name):
    name_lower = channel_name.lower()
    
    # === ADULT FILTER (Safety) ===
    adult_keywords = [
        "xxx", "18+", "+18", "adult", "porn", "sex", "barely", "hustler", 
        "playboy", "penthouse", "blue movie", "redlight", "babes", "brazzers", 
        "dorcel", "private", "vivid", "colours", "night", "hot", "love", 
        "sct", "pink", "passion", "girls"
    ]
    if any(k in name_lower for k in adult_keywords):
        if "essex" not in name_lower and "sussex" not in name_lower:
             return None, None

    # === DOCUMENTARY (0x9) ===
    if any(k in name_lower for k in ["doc", "history", "historia", "nat geo", "wild", "planet", "earth", "animal", "science", "investigation", "crime", "discovery", "tlc", "quest", "travel", "cook", "food", "geographic"]):
        return "Documentary", 0x9

    # === SPORTS (0x4) ===
    if any(k in name_lower for k in ["sport", "soccer", "football", "kora", "league", "racing", "f1", "wwe", "ufc", "fight", "box", "arena"]):
        return "Sports", 0x4
    if any(k in name_lower for k in ["espn", "bein", "ssc", "alkass", "ad sport", "dubai sport", "on sport", "euro", "bt sport", "sky sport", "match!", "dazn"]):
        return "Sports", 0x4

    # === NEWS (0x2) ===
    if any(k in name_lower for k in ["news", "akhbar", "arabia", "jazeera", "hadath", "bbc", "cnn", "cnbc", "bloomberg", "weather", "trt", "dw", "lbc", "mtv lebanon"]):
        return "News", 0x2

    # === KIDS (0x5) ===
    if any(k in name_lower for k in ["kid", "child", "cartoon", "toon", "anime", "junior", "disney", "nick", "boomerang", "cbeebies", "baraem", "jeem", "spacetoon", "mbc 3", "cn", "pogo"]):
        return "Kids", 0x5

    # === MUSIC (0x6) ===
    if any(k in name_lower for k in ["music", "song", "clip", "mix", "fm", "radio", "mtv", "vh1", "melody", "mazzika", "rotana clip", "wanasah", "aghani"]):
        return "Music", 0x6

    # === MOVIES (0x1) ===
    if any(k in name_lower for k in ["movie", "film", "cinema", "cine", "kino", "aflam", "vod", "box office"]):
        return "Movies", 0x1
    if any(k in name_lower for k in ["hbo", "sky cinema", "mbc 2", "mbc max", "mbc action", "rotana cinema", "zee aflam", "b4u", "osn movies", "amc", "fox action", "fox thriller"]):
        return "Movies", 0x1
    if any(k in name_lower for k in ["action", "thriller", "horror", "comedy", "sci-fi"]):
        return "Movies", 0x1

    # === SHOWS (0x3) ===
    if any(k in name_lower for k in ["drama", "series", "mosalsalat", "hikaya", "show", "tv", "general", "family", "colors", "zee", "star plus", "mbc 1", "mbc 4", "rotana khalijia", "sky one", "bbc one", "itv", "rai", "zdf", "rtl"]):
        return "Shows", 0x3

    return "General/Other", 0x0

def clean_channel_name_fuzzy(name):
    """Clean channel name for smart deduplication."""
    n = name.lower()
    n = re.sub(r'\b(hd|sd|fhd|4k|uhd|hevc)\b', '', n)
    n = re.sub(r'\+\d+', '', n) 
    return normalize_string(n)

def normalize_string(text):
    if not text: return ""
    return re.sub(r'[\W_]+', '', text.lower())

# --- 3. Satellite Logic ---
def get_sat_position(ref_str):
    if ref_str.startswith("4097:") or ref_str.startswith("5001:") or ref_str.startswith("5002:"):
        return "IPTV"
    try:
        parts = ref_str.split(":")
        if len(parts) > 6:
            ns_val = int(parts[6], 16)
            orb_pos = (ns_val >> 16) & 0xFFFF
            if orb_pos == 0xFFFF: return "DVB-T/C"
            if orb_pos == 0: return ""
            if orb_pos > 1800:
                pos = 3600 - orb_pos
                return f"{pos/10.0:.1f}W"
            else:
                return f"{orb_pos/10.0:.1f}E"
    except: pass
    return ""

def scan_epg_import_dir():
    base_path = "/etc/epgimport/"
    xml_count = 0
    if not os.path.exists(base_path): return 0
    try:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".xml") or file.endswith(".sources.xml"):
                    xml_count += 1
        return xml_count
    except: return 0

def check_epg_dat_exists():
    paths = ["/media/hdd/epg.dat", "/media/usb/epg.dat", "/etc/enigma2/epg.dat", "/hdd/epg.dat"]
    for p in paths:
        if os.path.exists(p): return True, p
    return False, "Not Found"

# --- 4. List Builder (Percentage Text) ---
def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, genre_nibble, start_time, duration, show_progress=True):
    icon_pixmap = get_genre_icon(genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    display_name = f"{channel_name} ({sat_info})" if sat_info else channel_name
    
    # Calculate Percentage
    progress_str = ""
    progress_color = 0xFFFFFF # Default White
    
    if show_progress and duration > 0:
        current_time = int(time.time())
        if start_time <= current_time < (start_time + duration):
            percent = int(((current_time - start_time) / float(duration)) * 100)
            if percent > 100: percent = 100
            progress_str = f"({percent}%)"
            
            # Smart Coloring
            if percent > 85:
                progress_color = 0xFF4040 # Red (Ending soon)
            elif percent > 10:
                progress_color = 0x00FF00 # Green (Active)
            # Else White (Just started)
    
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration),
        
        # 1. Icon (Left)
        MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(40, 40), png=icon_pixmap),
        
        # 2. Channel & Event Stack (Width: 280)
        MultiContentEntryText(pos=(60, 2), size=(280, 24), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        MultiContentEntryText(pos=(60, 26), size=(280, 20), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        
        # 3. Time (Width: 70)
        MultiContentEntryText(pos=(350, 2), size=(70, 48), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        
        # 4. Category (Width: 130)
        MultiContentEntryText(pos=(430, 2), size=(130, 48), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        
        # 5. Percentage (Far Right, Width: 80)
        MultiContentEntryText(pos=(570, 2), size=(80, 48), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
    ]
    
    return res

# --- 5. Backend Logic ---
def get_categorized_events_list(use_favorites=False, time_offset=0):
    results = []
    MAX_CHANNELS = 4000
    channel_count = 0
    seen_programs = set()

    try:
        epg_cache = eEPGCache.getInstance()
        service_handler = eServiceCenter.getInstance()
        
        if use_favorites:
            ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'
        else:
            ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        
        bouquet_root = eServiceReference(ref_str)
        bouquet_list = service_handler.list(bouquet_root)
        
        if not bouquet_list: return []
        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content: return []
        
        bouquets_to_scan = bouquet_content 
        
        current_time = int(time.time())
        target_timestamp = current_time + time_offset
        lookup_time = -1 if time_offset == 0 else target_timestamp
        
        show_prog = (time_offset == 0)

        for bouquet_entry in bouquets_to_scan:
            if channel_count >= MAX_CHANNELS: break
            
            bouquet_ref = eServiceReference(bouquet_entry[0])
            services = service_handler.list(bouquet_ref)
            if not services: continue
            
            service_list = services.getContent("SN", True)
            
            for s_ref, s_name in service_list:
                if "::" in s_ref or "---" in s_name: continue
                
                channel_count += 1
                if channel_count >= MAX_CHANNELS: break

                category, nibble = classify_by_channel_name(s_name)
                if category is None: continue 
                
                sat_info = get_sat_position(s_ref)
                
                try:
                    service_reference = eServiceReference(s_ref)
                    event = epg_cache.lookupEventTime(service_reference, lookup_time)
                    
                    if not event and (s_ref.startswith("4097:") or s_ref.startswith("5001:") or s_ref.startswith("5002:")):
                        parts = s_ref.split(":")
                        if len(parts) > 7:
                            clean_str = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"
                            clean_ref = eServiceReference(clean_str)
                            event = epg_cache.lookupEventTime(clean_ref, lookup_time)

                    if not event: continue

                    event_name = event.getEventName()
                    if not event_name: continue
                    
                    clean_ch = clean_channel_name_fuzzy(s_name)
                    clean_evt = normalize_string(event_name)
                    start_time = event.getBeginTime()
                    time_block = int(start_time / 900) 
                    
                    unique_key = f"{clean_ch}_{clean_evt}_{time_block}"
                    if unique_key in seen_programs:
                        continue 
                    seen_programs.add(unique_key)
                    
                    duration = event.getDuration()
                    
                    entry = build_list_entry(category, s_name, sat_info, event_name, s_ref, nibble, start_time, duration, show_prog)
                    results.append(entry)

                except: continue

    except: return []

    return results

# --- 6. The GUI Screen ---
class WhatToWatchScreen(Screen):
    # Updated Title to include Version
    skin = f"""
        <screen position="center,center" size="800,600" title="What to Watch v{VERSION}">
            <widget name="status_label" position="10,10" size="780,40" font="Regular;22" halign="center" valign="center" foregroundColor="#00ff00" />
            <widget name="event_list" position="10,60" size="780,440" scrollbarMode="showOnDemand" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="10,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="200,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="390,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="580,510" size="40,40" alphatest="on" />
            
            <widget name="key_red" position="55,515" size="140,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_green" position="245,515" size="140,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_yellow" position="435,515" size="140,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_blue" position="625,515" size="165,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            
            <widget name="info_bar" position="10,555" size="780,35" font="Regular;16" halign="center" valign="center" foregroundColor="#ffff00" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["event_list"].l.setFont(0, gFont("Regular", 22))
        self["event_list"].l.setFont(1, gFont("Regular", 18))
        self["event_list"].l.setItemHeight(50)
        
        self["status_label"] = Label("Loading...")
        
        self["key_red"] = Label("Time: Now")
        self["key_green"] = Label("Refresh")
        self["key_yellow"] = Label("Category")
        self["key_blue"] = Label("Options")
        self["info_bar"] = Label("")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions"], {
            "ok": self.zap_channel,
            "cancel": self.close,
            "red": self.toggle_time_filter,
            "green": self.refresh_list,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
        }, -1)

        self.full_list = []
        self.current_filter = None
        self.current_sat_filter = None
        self.use_favorites = False
        self.sort_mode = 'category'
        self.time_modes = [("Time: Now", 0), ("Time: +1h", 3600), ("Time: +2h", 7200), ("Time: Tonight", 14400)]
        self.time_mode_index = 0
        
        self.onLayoutFinish.append(self.on_start)

    def on_start(self):
        c = scan_epg_import_dir()
        if c > 0: print(f"[WhatToWatch] {c} EPG sources found")
        self.refresh_list()

    def refresh_list(self):
        source_text = "Favorites" if self.use_favorites else "All Channels"
        time_label, time_offset = self.time_modes[self.time_mode_index]
        
        self["status_label"].setText(f"Scanning {source_text} ({time_label})...")
        self["key_red"].setText(time_label)
        
        self.full_list = get_categorized_events_list(self.use_favorites, time_offset)
        
        if not self.full_list:
            found, path = check_epg_dat_exists()
            msg = f"No events for {time_label}."
            if not found: msg += " (epg.dat missing)"
            self["status_label"].setText(msg)
            self["event_list"].setList([])
            return

        self.current_filter = None
        self.current_sat_filter = None
        self.apply_sorting()
        self.apply_filter()

    def toggle_time_filter(self):
        self.time_mode_index = (self.time_mode_index + 1) % len(self.time_modes)
        self.refresh_list()

    def apply_sorting(self):
        if self.sort_mode == 'category':
            self.full_list.sort(key=lambda x: (x[0][0], x[0][1]))
        elif self.sort_mode == 'channel':
            self.full_list.sort(key=lambda x: x[0][1])
        elif self.sort_mode == 'time':
            self.full_list.sort(key=lambda x: x[0][5])

    def apply_filter(self):
        if not self.full_list: 
            self["event_list"].setList([])
            return
            
        filtered = self.full_list
        
        if self.current_filter:
            filtered = [e for e in filtered if e[0][0] == self.current_filter]

        if self.current_sat_filter:
            filtered = [e for e in filtered if e[0][2] == self.current_sat_filter]

        self["event_list"].setList(filtered)
        
        time_label = self.time_modes[self.time_mode_index][0]
        cat_txt = self.current_filter if self.current_filter else "All"
        sat_txt = self.current_sat_filter if self.current_sat_filter else "All Sats"
        
        self["status_label"].setText(f"{cat_txt} | {sat_txt} | {len(filtered)} events")
        self.update_info_bar()

    def cycle_category(self):
        if not self.full_list: return
        categories = sorted(list(set([e[0][0] for e in self.full_list])))
        if not categories: return
        
        if not self.current_filter:
            self.current_filter = categories[0]
        else:
            try:
                idx = categories.index(self.current_filter)
                if idx < len(categories) - 1:
                    self.current_filter = categories[idx + 1]
                else:
                    self.current_filter = None
            except ValueError:
                self.current_filter = None
        self.apply_filter()

    def show_options_menu(self):
        menu_list = [
            ("Toggle Source (Fav/All)", "toggle_source"),
            ("Filter by Satellite", "filter_sat"),
            ("Sort By...", "sort_menu"),
            ("Check for Updates", "update"),
        ]
        self.session.openWithCallback(self.options_menu_callback, ChoiceBox, title="Options", list=menu_list)

    def options_menu_callback(self, choice):
        if choice is None: return
        action = choice[1]
        
        if action == "toggle_source":
            self.use_favorites = not self.use_favorites
            self.refresh_list()
        elif action == "filter_sat":
            self.show_sat_menu()
        elif action == "sort_menu":
            self.show_sort_menu()
        elif action == "update":
            self.check_updates()

    # --- AUTO UPDATE LOGIC ---
    def check_updates(self):
        self["status_label"].setText("Checking for updates...")
        # Use wget to fetch version.txt to /tmp
        cmd = f"wget -qO /tmp/wtw_ver.txt {UPDATE_URL_VER}"
        os.system(cmd)
        
        if os.path.exists("/tmp/wtw_ver.txt"):
            with open("/tmp/wtw_ver.txt", "r") as f:
                remote_ver = f.read().strip()
            
            if remote_ver > VERSION:
                self.session.openWithCallback(self.do_update, MessageBox, f"New version {remote_ver} available!\nUpdate now?", MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, "You have the latest version.", MessageBox.TYPE_INFO, timeout=3)
                self["status_label"].setText("Version is up to date.")
        else:
            self.session.open(MessageBox, "Update check failed (No Internet?)", MessageBox.TYPE_ERROR)

    def do_update(self, confirm):
        if confirm:
            self["status_label"].setText("Updating plugin...")
            # Download new plugin.py
            cmd = f"wget -qO {PLUGIN_FILE_PATH} {UPDATE_URL_PY}"
            os.system(cmd)
            
            self.session.open(MessageBox, "Update successful! Restarting GUI...", MessageBox.TYPE_INFO, timeout=3)
            # Force Restart
            import time
            time.sleep(2)
            quitMainloop(3)

    def show_sat_menu(self):
        if not self.full_list: return
        sats = sorted(list(set([e[0][2] for e in self.full_list if e[0][2]])))
        if not sats: return
        
        menu_list = [("All Satellites", "all")]
        for s in sats:
            menu_list.append((s, s))
            
        self.session.openWithCallback(self.sat_menu_callback, ChoiceBox, title="Select Satellite", list=menu_list)

    def sat_menu_callback(self, choice):
        if choice is None: return
        if choice[1] == "all":
            self.current_sat_filter = None
        else:
            self.current_sat_filter = choice[1]
        self.apply_filter()

    def show_sort_menu(self):
        menu_list = [("Category", "category"), ("Channel", "channel"), ("Time", "time")]
        self.session.openWithCallback(self.sort_menu_callback, ChoiceBox, title="Sort By", list=menu_list)

    def sort_menu_callback(self, choice):
        if choice is None: return
        self.sort_mode = choice[1]
        self.apply_sorting()
        self.apply_filter()

    def update_info_bar(self):
        sat_txt = self.current_sat_filter if self.current_sat_filter else "All"
        self["info_bar"].setText(f"Sort: {self.sort_mode} | Cat: {self.current_filter or 'All'} | Sat: {sat_txt}")

    def zap_channel(self):
        current_selection = self["event_list"].getCurrent()
        if current_selection:
            self.session.nav.playService(eServiceReference(current_selection[0][4]))
            self.close()

def main(session, **kwargs):
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=f"What to Watch v{VERSION}", 
            description=f"Smart EPG Browser v{VERSION} by {AUTHOR}", 
            where=PluginDescriptor.WHERE_PLUGINMENU, 
            icon="plugin.png", 
            fnc=main
        )
    ]

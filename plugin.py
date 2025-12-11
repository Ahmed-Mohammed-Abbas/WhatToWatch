# ============================================================================
#  Plugin: What to Watch
#  Author: reali22
#  Version: 1.5
#  Description: Advanced EPG Browser with categorization, satellite filtering,
#               smart deduplication, Auto-Update, Preview Mode, 
#               STRICT Adult Filtering, and EPG Button UI.
#  GitHub: https://github.com/Ahmed-Mohammed-Abbas/WhatToWatch
# ============================================================================

import os
import time
import re
import json
from sys import version_info

if version_info.major == 3:
    from urllib.request import Request, urlopen
    from urllib.parse import quote
else:
    from urllib2 import Request, urlopen
    from urllib import quote

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
VERSION = "1.5"
AUTHOR = "reali22"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- ADULT BLACKLIST ---
ADULT_KEYWORDS = [
    "xxx", "18+", "+18", "adult", "porn", "sex", "erotic", "nude", "hardcore", 
    "barely", "hustler", "playboy", "penthouse", "blue movie", "redlight", 
    "babes", "brazzers", "dorcel", "private", "vivid", "colours", "night", 
    "hot", "love", "sct", "pink", "passion", "girls", "centoxcento", "exotic",
    "xy mix", "xy plus", "man-x", "evilangel", "daring", "lovesuite", "babe"
]

# --- 1. Helper Functions ---
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

def translate_text(text, target_lang='en'):
    if not text or len(text) < 2: return "No description available."
    if any('\u0600' <= char <= '\u06FF' for char in text[:30]): return text

    encoded_text = quote(text)
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=%s&dt=t&q=%s" % (target_lang, encoded_text)
    
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    try:
        response = urlopen(req, timeout=5)
        data = response.read().decode('utf-8')
        json_data = json.loads(data)
        translation = ""
        if json_data and isinstance(json_data, list):
            for item in json_data[0]:
                if item and len(item) > 0: translation += item[0]
        return translation
    except Exception as e:
        return f"Translation Failed: {str(e)}\n\nOriginal: {text}"

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
def is_adult_content(text):
    if not text: return False
    text_lower = text.lower()
    if any(k in text_lower for k in ADULT_KEYWORDS):
        if "essex" not in text_lower and "sussex" not in text_lower:
             return True
    return False

def classify_by_channel_name(channel_name):
    if is_adult_content(channel_name): return None, None
    name_lower = channel_name.lower()

    if any(k in name_lower for k in ["sport", "soccer", "football", "kora", "league", "racing", "f1", "wwe", "ufc", "fight", "box", "arena", "calcio", "match", "dazn", "motogp", "nba", "tennis", "espn", "bein", "ssc", "alkass", "ad sport", "dubai sport", "on sport", "nile sport", "arryadia", "kuwait sport", "saudi sport", "euro", "bt sport", "sky sport", "polstat sport", "canal+ sport", "tsn", "supersport", "eleven"]):
        return "Sports", 0x4
    if any(k in name_lower for k in ["movie", "film", "cinema", "cine", "kino", "aflam", "vod", "box office", "premiere", "hbo", "sky cinema", "sky movies", "mbc 2", "mbc max", "mbc action", "mbc bollywood", "rotana cinema", "rotana classic", "zee aflam", "zee cinema", "b4u", "osn movies", "amc", "fox movies", "fox action", "fox thriller", "paramount", "tcm", "action", "thriller", "horror", "comedy", "sci-fi", "canal+ cinema", "cine+", "filmbox", "warnertv", "sony max"]):
        return "Movies", 0x1
    if any(k in name_lower for k in ["kid", "child", "cartoon", "toon", "anime", "anim", "junior", "disney", "nick", "boomerang", "cbeebies", "baraem", "jeem", "ajyal", "spacetoon", "mbc 3", "cn", "pogo", "majid", "dreamworks", "baby", "duck", "fix&foxi", "kika", "super rtl", "gulli", "clan"]):
        return "Kids", 0x5
    if any(k in name_lower for k in ["news", "akhbar", "arabia", "jazeera", "hadath", "bbc", "cnn", "cnbc", "bloomberg", "weather", "trt", "dw", "lbc", "mtv lebanon", "skynews", "france 24", "russia today", "rt ", "euronews", "tagesschau", "n24", "welt", "i24", "al araby", "alghad", "asharq", "watania", "al ekhbariya"]):
        return "News", 0x2
    if any(k in name_lower for k in ["doc", "history", "historia", "nat geo", "wild", "planet", "earth", "animal", "science", "investigation", "crime", "discovery", "tlc", "quest", "travel", "cook", "food", "geographic", "arte", "phoenix", "zdfinfo", "alpha", "explorer", "viasat explore", "viasat history"]):
        return "Documentary", 0x9
    if any(k in name_lower for k in ["music", "song", "clip", "mix", "fm", "radio", "mtv", "vh1", "melody", "mazzika", "rotana clip", "rotana music", "wanasah", "aghani", "arabica", "4fun", "eska", "polo", "vivia", "nrj", "kiss", "dance", "hits"]):
        return "Music", 0x6
    if any(k in name_lower for k in ["drama", "series", "mosalsalat", "hikaya", "show", "tv", "general", "family", "entertainment", "novelas", "soaps", "mbc 1", "mbc 4", "mbc drama", "mbc masr", "mbc iraq", "rotana khalijia", "rotana drama", "zee alwan", "zee tv", "star plus", "colors", "sony", "sky one", "sky atlantic", "bbc one", "bbc two", "itv", "channel 4", "rai 1", "rai 2", "canale 5", "italia 1", "tf1", "m6", "antena 3", "zdf", "rtl", "sat.1", "pro7", "vox", "kabel 1"]):
        return "Shows", 0x3
    return "General/Other", 0x0

def clean_channel_name_fuzzy(name):
    n = name.lower()
    n = re.sub(r'\b(hd|sd|fhd|4k|uhd|hevc)\b', '', n)
    n = re.sub(r'\+\d+', '', n) 
    return re.sub(r'[\W_]+', '', n)

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
    if not os.path.exists(base_path): return 0
    try:
        count = 0
        for root, dirs, files in os.walk(base_path):
            count += len([f for f in files if f.endswith(".xml") or f.endswith(".sources.xml")])
        return count
    except: return 0

def check_epg_dat_exists():
    paths = ["/media/hdd/epg.dat", "/media/usb/epg.dat", "/etc/enigma2/epg.dat", "/hdd/epg.dat"]
    for p in paths:
        if os.path.exists(p): return True, p
    return False, "Not Found"

# --- 4. List Builder ---
def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, genre_nibble, start_time, duration, show_progress=True):
    icon_pixmap = get_genre_icon(genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    display_name = f"{channel_name} ({sat_info})" if sat_info else channel_name
    
    progress_str = ""
    progress_color = 0xFFFFFF 
    if show_progress and duration > 0:
        current_time = int(time.time())
        if start_time <= current_time < (start_time + duration):
            percent = int(((current_time - start_time) / float(duration)) * 100)
            if percent > 100: percent = 100
            progress_str = f"({percent}%)"
            if percent > 85: progress_color = 0xFF4040 
            elif percent > 10: progress_color = 0x00FF00
    
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration),
        MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(40, 40), png=icon_pixmap),
        MultiContentEntryText(pos=(60, 2), size=(280, 24), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        MultiContentEntryText(pos=(60, 26), size=(280, 20), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(350, 2), size=(70, 48), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryText(pos=(430, 2), size=(130, 48), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(570, 2), size=(80, 48), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
    ]
    return res

# --- 5. Backend Logic ---
def get_categorized_events_list(use_favorites=False, time_offset=0):
    results = []
    MAX_CHANNELS = 4000
    channel_count = 0
    unique_channels = {} 

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
                    
                    if is_adult_content(event_name): continue

                    clean_ch = clean_channel_name_fuzzy(s_name)
                    is_hd = "hd" in s_name.lower()
                    
                    start_time = event.getBeginTime()
                    duration = event.getDuration()
                    
                    entry = build_list_entry(category, s_name, sat_info, event_name, s_ref, nibble, start_time, duration, show_prog)
                    
                    if clean_ch in unique_channels:
                        existing_entry, existing_is_hd = unique_channels[clean_ch]
                        if is_hd and not existing_is_hd:
                            unique_channels[clean_ch] = (entry, is_hd)
                    else:
                        unique_channels[clean_ch] = (entry, is_hd)

                except: continue

    except: return []

    return [val[0] for val in unique_channels.values()]

# --- 6. The GUI Screen ---
class WhatToWatchScreen(Screen):
    # Added EPG Button Layout (5 buttons total)
    skin = f"""
        <screen position="center,center" size="800,600" title="What to Watch v{VERSION}">
            <widget name="status_label" position="10,10" size="780,40" font="Regular;22" halign="center" valign="center" foregroundColor="#00ff00" />
            <widget name="event_list" position="10,60" size="780,440" scrollbarMode="showOnDemand" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="10,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="165,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="320,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="475,510" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/key_epg.png" position="630,510" size="40,40" alphatest="on" />
            
            <widget name="key_red" position="55,515" size="110,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_green" position="210,515" size="110,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_yellow" position="365,515" size="110,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_blue" position="520,515" size="110,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_epg" position="675,515" size="110,30" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" text="Translate" />
            
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
        self["key_epg"] = Label("Translate") # Label for EPG Button
        self["info_bar"] = Label("Press EPG/INFO to translate description")

        # Map both "info" and "epg" keys to the translation function
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.zap_channel,
            "cancel": self.close,
            "red": self.toggle_time_filter,
            "green": self.refresh_list,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
            "info": self.show_translated_info,  
            "epg": self.show_translated_info,   # <--- Added EPG Mapping
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

    # --- TRANSLATION FEATURE ---
    def show_translated_info(self):
        current_selection = self["event_list"].getCurrent()
        if not current_selection: return

        # Payload structure: (Cat, Channel, Sat, EventName, Ref, Start, Dur)
        payload = current_selection[0]
        event_name = payload[3]
        service_ref = payload[4]
        start_time = payload[5]
        
        epg_cache = eEPGCache.getInstance()
        text_to_translate = event_name # Default
        
        try:
            # Fetch FULL description for specific time
            event = epg_cache.lookupEventTime(eServiceReference(service_ref), start_time)
            if event:
                short = event.getShortDescription() or ""
                ext = event.getExtendedDescription() or ""
                full = f"{event_name}\n\n{short}\n{ext}".strip()
                if len(full) > len(event_name):
                    text_to_translate = full
        except: pass

        self.session.open(MessageBox, "Translating...", type=MessageBox.TYPE_INFO, timeout=1)
        translated = translate_text(text_to_translate, target_lang='en') # Change 'en' to 'ar' if preferred
        self.session.open(MessageBox, translated, type=MessageBox.TYPE_INFO)

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
                if idx < len(categories) - 1: self.current_filter = categories[idx + 1]
                else: self.current_filter = None
            except: self.current_filter = None
        self.apply_filter()

    def show_options_menu(self):
        menu_list = [("Toggle Source (Fav/All)", "toggle_source"), ("Filter by Satellite", "filter_sat"), ("Sort By...", "sort_menu"), ("Check for Updates", "update")]
        self.session.openWithCallback(self.options_menu_callback, ChoiceBox, title="Options", list=menu_list)

    def options_menu_callback(self, choice):
        if choice is None: return
        action = choice[1]
        if action == "toggle_source":
            self.use_favorites = not self.use_favorites
            self.refresh_list()
        elif action == "filter_sat": self.show_sat_menu()
        elif action == "sort_menu": self.show_sort_menu()
        elif action == "update": self.check_updates()

    def check_updates(self):
        self["status_label"].setText("Checking for updates...")
        cmd = f"wget -qO /tmp/wtw_ver.txt {UPDATE_URL_VER}"
        os.system(cmd)
        if os.path.exists("/tmp/wtw_ver.txt"):
            with open("/tmp/wtw_ver.txt", "r") as f: remote_ver = f.read().strip()
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
            cmd = f"wget -qO {PLUGIN_FILE_PATH} {UPDATE_URL_PY}"
            os.system(cmd)
            self.session.open(MessageBox, "Update successful! Restarting GUI...", MessageBox.TYPE_INFO, timeout=3)
            import time; time.sleep(2); quitMainloop(3)

    def show_sat_menu(self):
        if not self.full_list: return
        sats = sorted(list(set([e[0][2] for e in self.full_list if e[0][2]])))
        if not sats: return
        menu_list = [("All Satellites", "all")]
        for s in sats: menu_list.append((s, s))
        self.session.openWithCallback(self.sat_menu_callback, ChoiceBox, title="Select Satellite", list=menu_list)

    def sat_menu_callback(self, choice):
        if choice is None: return
        self.current_sat_filter = None if choice[1] == "all" else choice[1]
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

def main(session, **kwargs):
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [PluginDescriptor(name=f"What to Watch v{VERSION}", description=f"Smart EPG Browser v{VERSION} by {AUTHOR}", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

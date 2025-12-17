# ============================================================================
#  Plugin: What to Watch
#  Author: reali22
#  Version: 2.1
#  Description: Content-Aware EPG Browser with "Offline AI" (Weighted Scoring),
#               Satellite Filtering, Deduplication, Auto-Update, and Translation.
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
VERSION = "2.1"
AUTHOR = "reali22"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- 1. THE "OFFLINE AI" BRAIN (Weighted Keywords) ---
# Dictionary format: "keyword": {"Category": score}
# Higher score = stronger indicator.
WEIGHTED_DB = {
    # --- SPORTS (0x4) ---
    "sport": {"Sports": 10}, "sports": {"Sports": 10}, "soccer": {"Sports": 10},
    "football": {"Sports": 10}, "kora": {"Sports": 10}, "calcio": {"Sports": 10},
    "match": {"Sports": 5}, "live": {"Sports": 2}, "vs": {"Sports": 3},
    "cup": {"Sports": 5}, "league": {"Sports": 5}, "racing": {"Sports": 8},
    "f1": {"Sports": 10}, "motogp": {"Sports": 10}, "wwe": {"Sports": 10},
    "ufc": {"Sports": 10}, "boxing": {"Sports": 8}, "arena": {"Sports": 5},
    "bein": {"Sports": 20}, "espn": {"Sports": 20}, "alkass": {"Sports": 15},
    "ssc": {"Sports": 15}, "ad sport": {"Sports": 15}, "dubai sport": {"Sports": 15},
    "on sport": {"Sports": 15}, "euro": {"Sports": 3}, "eurosport": {"Sports": 15},
    "premier": {"Sports": 5}, "champion": {"Sports": 5}, "olymp": {"Sports": 8},
    "goal": {"Sports": 5}, "hd": {"Sports": 0}, # Neutral

    # --- MOVIES (0x1) ---
    "movie": {"Movies": 10}, "movies": {"Movies": 10}, "film": {"Movies": 10},
    "cinema": {"Movies": 10}, "cine": {"Movies": 10}, "kino": {"Movies": 10},
    "aflam": {"Movies": 15}, "vod": {"Movies": 8}, "box office": {"Movies": 8},
    "hbo": {"Movies": 15}, "rotana": {"Movies": 2}, "cinema": {"Movies": 10},
    "action": {"Movies": 6}, "thriller": {"Movies": 6}, "horror": {"Movies": 6},
    "comedy": {"Movies": 4}, "drama": {"Movies": 2, "Shows": 5}, # Split weight
    "sci-fi": {"Movies": 6}, "western": {"Movies": 6}, "osn": {"Movies": 5},
    "fox": {"Movies": 3, "Shows": 3}, "mbc 2": {"Movies": 20}, "mbc max": {"Movies": 20},
    "bollywood": {"Movies": 10}, "zee aflam": {"Movies": 20}, "b4u": {"Movies": 15},
    "starring": {"Movies": 5}, "directed": {"Movies": 5},

    # --- NEWS (0x2) ---
    "news": {"News": 15}, "akhbar": {"News": 15}, "arabia": {"News": 3},
    "jazeera": {"News": 15}, "bbc": {"News": 10}, "cnn": {"News": 15},
    "cnbc": {"News": 15}, "weather": {"News": 10}, "bloomberg": {"News": 15},
    "hadath": {"News": 10}, "report": {"News": 5}, "journal": {"News": 8},
    "update": {"News": 3}, "breaking": {"News": 5}, "info": {"News": 2},
    "france 24": {"News": 15}, "russia today": {"News": 15}, "trt": {"News": 5},
    "lbc": {"News": 5}, "skynews": {"News": 15}, "tagesschau": {"News": 10},

    # --- KIDS (0x5) ---
    "kid": {"Kids": 10}, "kids": {"Kids": 10}, "child": {"Kids": 8},
    "cartoon": {"Kids": 15}, "toon": {"Kids": 15}, "anime": {"Kids": 12},
    "anim": {"Kids": 5}, "junior": {"Kids": 8}, "disney": {"Kids": 15},
    "nick": {"Kids": 15}, "cbeebies": {"Kids": 15}, "spacetoon": {"Kids": 20},
    "mbc 3": {"Kids": 20}, "cn": {"Kids": 10}, "pogo": {"Kids": 15},
    "dreamworks": {"Kids": 15}, "baby": {"Kids": 10}, "tales": {"Kids": 5},
    "adventure": {"Kids": 2}, "mouse": {"Kids": 5}, "sponge": {"Kids": 5},

    # --- DOCUMENTARY (0x9) ---
    "doc": {"Documentary": 10}, "history": {"Documentary": 10}, "historia": {"Documentary": 10},
    "geo": {"Documentary": 8}, "wild": {"Documentary": 10}, "planet": {"Documentary": 8},
    "earth": {"Documentary": 8}, "animal": {"Documentary": 10}, "science": {"Documentary": 10},
    "discovery": {"Documentary": 15}, "investigation": {"Documentary": 8}, "crime": {"Documentary": 5},
    "nature": {"Documentary": 8}, "space": {"Documentary": 8}, "universe": {"Documentary": 8},
    "safari": {"Documentary": 8}, "travel": {"Documentary": 8}, "cook": {"Documentary": 5},

    # --- MUSIC (0x6) ---
    "music": {"Music": 15}, "song": {"Music": 10}, "clip": {"Music": 8},
    "mix": {"Music": 5}, "radio": {"Music": 10}, "mtv": {"Music": 15},
    "melody": {"Music": 10}, "mazzika": {"Music": 15}, "wanasah": {"Music": 15},
    "aghani": {"Music": 15}, "dance": {"Music": 8}, "hits": {"Music": 8},
    "concert": {"Music": 8}, "live": {"Music": 2}, # Shared with sports

    # --- RELIGIOUS (0x7) ---
    "quran": {"Religious": 20}, "sunnah": {"Religious": 20}, "iqraa": {"Religious": 15},
    "islam": {"Religious": 10}, "church": {"Religious": 10}, "catholic": {"Religious": 10},
    "resalah": {"Religious": 10}, "majd": {"Religious": 5}, "karma": {"Religious": 5},
    "agape": {"Religious": 10}, "ctv": {"Religious": 5}, "noursat": {"Religious": 10},

    # --- SHOWS (0x3) ---
    "series": {"Shows": 10}, "show": {"Shows": 5}, "tv": {"Shows": 1},
    "drama": {"Shows": 8}, "soap": {"Shows": 8}, "episode": {"Shows": 5},
    "season": {"Shows": 5}, "mosalsalat": {"Shows": 15}, "hikaya": {"Shows": 10},
    "general": {"Shows": 5}, "family": {"Shows": 5}, "entertainment": {"Shows": 5},
    "mbc 1": {"Shows": 15}, "mbc 4": {"Shows": 15}, "mbc drama": {"Shows": 15},
    "zee": {"Shows": 5}, "colors": {"Shows": 5}, "star plus": {"Shows": 5}
}

# --- ADULT BLACKLIST (Strict) ---
ADULT_KEYWORDS = [
    "xxx", "18+", "+18", "adult", "porn", "sex", "erotic", "nude", "hardcore", 
    "barely", "hustler", "playboy", "penthouse", "blue movie", "redlight", 
    "babes", "brazzers", "dorcel", "private", "vivid", "colours", "night", 
    "hot", "love", "sct", "pink", "passion", "girls", "centoxcento", "exotic",
    "xy mix", "xy plus", "man-x", "evilangel", "daring", "lovesuite", "babe",
    "softcore", "uncensored", "after dark", "blue hustler", "dorcel tv"
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
        0x9: "science.png", 0xA: "leisure.png", 0xB: "arts.png"
    }
    icon_name = icon_map.get(nibble, "default.png")
    png_path = os.path.join(ICON_PATH, icon_name)
    if os.path.exists(png_path): return loadPNG(png_path)
    default_path = os.path.join(ICON_PATH, "default.png")
    if os.path.exists(default_path): return loadPNG(default_path)
    return None

# --- 2. Intelligent Categorization Engine ---
def is_adult_content(text):
    if not text: return False
    text_lower = text.lower()
    if any(k in text_lower for k in ADULT_KEYWORDS):
        if "essex" not in text_lower and "sussex" not in text_lower and "middlesex" not in text_lower:
             return True
    return False

def calculate_category_score(text):
    """
    Parses text and calculates a score for each category based on WEIGHTED_DB.
    Returns: Dictionary {Category: Score}
    """
    scores = {
        "Movies": 0, "Sports": 0, "News": 0, "Kids": 0, 
        "Documentary": 0, "Music": 0, "Religious": 0, "Shows": 0
    }
    
    if not text: return scores
    
    # Tokenize: Split by spaces and special chars
    tokens = re.split(r'[\W_]+', text.lower())
    
    for token in tokens:
        if token in WEIGHTED_DB:
            impact = WEIGHTED_DB[token]
            for cat, points in impact.items():
                scores[cat] += points
                
    return scores

def classify_content(channel_name, event_name):
    """
    Determines category using the Weighted Scoring System.
    """
    # 1. Safety Check
    if is_adult_content(channel_name) or is_adult_content(event_name):
        return None, None

    # 2. Calculate Scores
    # Channel name carries more weight (x1.5) than event name in some contexts,
    # but here we just sum them up for a holistic view.
    
    cat_scores = calculate_category_score(channel_name)
    evt_scores = calculate_category_score(event_name)
    
    # Combine Scores
    final_scores = {}
    for cat in cat_scores:
        # Channel name is usually a stronger indicator of the STATION TYPE
        # Event name is a stronger indicator of CURRENT CONTENT
        # We give slight preference to Channel Name for stability
        final_scores[cat] = (cat_scores[cat] * 1.5) + evt_scores.get(cat, 0)

    # 3. Find Winner
    best_cat = "General/Other"
    highest_score = 0
    
    for cat, score in final_scores.items():
        if score > highest_score:
            highest_score = score
            best_cat = cat
            
    # 4. Threshold Check
    # If the highest score is very low (< 3), it might be a false positive or generic
    if highest_score < 3:
        return "General/Other", 0x0
        
    # 5. Map to Nibble
    cat_map = {
        "Movies": 0x1, "News": 0x2, "Shows": 0x3, "Sports": 0x4,
        "Kids": 0x5, "Music": 0x6, "Religious": 0x7, "Documentary": 0x9
    }
    
    return best_cat, cat_map.get(best_cat, 0x0)

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

# --- 4. List Builder (Resized for 1080 Width) ---
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
        MultiContentEntryPixmapAlphaTest(pos=(10, 7), size=(50, 50), png=icon_pixmap),
        MultiContentEntryText(pos=(70, 2), size=(550, 30), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        MultiContentEntryText(pos=(70, 34), size=(550, 28), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(640, 2), size=(100, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryText(pos=(750, 2), size=(190, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(950, 2), size=(100, 60), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
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
                    
                    # CLASSIFY using AI-Score
                    category, nibble = classify_content(s_name, event_name)
                    if category is None: continue 

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
    skin = f"""
        <screen position="center,center" size="1080,720" title="What to Watch v{VERSION}">
            <widget name="status_label" position="15,15" size="1050,50" font="Regular;28" halign="center" valign="center" foregroundColor="#00ff00" />
            <widget name="event_list" position="15,80" size="1050,560" scrollbarMode="showOnDemand" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="15,650" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="225,650" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="435,650" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="645,650" size="40,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/key_epg.png" position="855,650" size="40,40" alphatest="on" />
            
            <widget name="key_red" position="60,655" size="150,35" zPosition="1" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_green" position="270,655" size="150,35" zPosition="1" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_yellow" position="480,655" size="150,35" zPosition="1" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_blue" position="690,655" size="150,35" zPosition="1" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="key_epg" position="900,655" size="160,35" zPosition="1" font="Regular;24" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" text="EPG Translate" />
            
            <widget name="info_bar" position="15,695" size="1050,25" font="Regular;20" halign="center" valign="center" foregroundColor="#ffff00" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        self["event_list"].l.setFont(0, gFont("Regular", 28))
        self["event_list"].l.setFont(1, gFont("Regular", 24))
        self["event_list"].l.setItemHeight(65)
        
        self["status_label"] = Label("Loading...")
        
        self["key_red"] = Label("Time: Now")
        self["key_green"] = Label("Refresh")
        self["key_yellow"] = Label("Category")
        self["key_blue"] = Label("Options")
        self["key_epg"] = Label("EPG Translate") 
        self["info_bar"] = Label("Press EPG/INFO to translate description")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", "EPGSelectActions", "InfoActions"], {
            "ok": self.zap_channel,
            "cancel": self.close,
            "red": self.toggle_time_filter,
            "green": self.refresh_list,
            "yellow": self.cycle_category,
            "blue": self.show_options_menu,
            "menu": self.show_sort_menu,
            "info": self.show_translated_info,  
            "epg": self.show_translated_info,   
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

        payload = current_selection[0]
        event_name = payload[3]
        service_ref = payload[4]
        start_time = payload[5]
        
        epg_cache = eEPGCache.getInstance()
        text_to_translate = event_name # Default
        
        try:
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

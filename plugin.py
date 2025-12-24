"""
============================================================================
Plugin: What to Watch
Author: reali22
Version: 2.0 (Enhanced)
Description: Content-Aware EPG Browser with Smart AI Categorization,
             Progress-Based Sorting, and Multi-Signal Detection
============================================================================
"""

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
VERSION = "2.0"
AUTHOR = "reali22"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- ENHANCED WEIGHTED KEYWORD DATABASE ---
WEIGHTED_DB = {
    # --- SPORTS (0x4) ---
    "sport": {"Sports": 12}, "sports": {"Sports": 12}, "soccer": {"Sports": 15},
    "football": {"Sports": 15}, "kora": {"Sports": 18}, "calcio": {"Sports": 15},
    "match": {"Sports": 8}, "live": {"Sports": 3}, "vs": {"Sports": 6},
    "cup": {"Sports": 8}, "league": {"Sports": 10}, "racing": {"Sports": 12},
    "f1": {"Sports": 15}, "motogp": {"Sports": 15}, "wwe": {"Sports": 15},
    "ufc": {"Sports": 15}, "boxing": {"Sports": 12}, "arena": {"Sports": 8},
    "bein": {"Sports": 25}, "espn": {"Sports": 25}, "alkass": {"Sports": 20},
    "ssc": {"Sports": 20}, "ad sport": {"Sports": 20}, "dubai sport": {"Sports": 20},
    "on sport": {"Sports": 20}, "euro": {"Sports": 5}, "eurosport": {"Sports": 20},
    "premier": {"Sports": 8}, "champion": {"Sports": 8}, "olymp": {"Sports": 12},
    "goal": {"Sports": 8}, "stadium": {"Sports": 10}, "tournament": {"Sports": 10},
    "playoff": {"Sports": 10}, "finals": {"Sports": 8}, "basketball": {"Sports": 15},
    "tennis": {"Sports": 15}, "golf": {"Sports": 15}, "cricket": {"Sports": 15},
    
    # --- MOVIES (0x1) ---
    "movie": {"Movies": 15}, "movies": {"Movies": 15}, "film": {"Movies": 15},
    "cinema": {"Movies": 15}, "cine": {"Movies": 15}, "kino": {"Movies": 15},
    "aflam": {"Movies": 20}, "vod": {"Movies": 12}, "box office": {"Movies": 12},
    "hbo": {"Movies": 20}, "rotana": {"Movies": 5}, "action": {"Movies": 10},
    "thriller": {"Movies": 10}, "horror": {"Movies": 10}, "comedy": {"Movies": 8},
    "drama": {"Movies": 3, "Shows": 8}, "sci-fi": {"Movies": 10},
    "western": {"Movies": 10}, "osn": {"Movies": 10}, "fox": {"Movies": 5, "Shows": 5},
    "mbc 2": {"Movies": 25}, "mbc max": {"Movies": 25}, "bollywood": {"Movies": 15},
    "zee aflam": {"Movies": 25}, "b4u": {"Movies": 20}, "starring": {"Movies": 8},
    "directed": {"Movies": 8}, "premiere": {"Movies": 8},
    
    # --- NEWS (0x2) ---
    "news": {"News": 20}, "akhbar": {"News": 20}, "arabia": {"News": 5},
    "jazeera": {"News": 20}, "bbc": {"News": 15}, "cnn": {"News": 20},
    "cnbc": {"News": 20}, "weather": {"News": 15}, "bloomberg": {"News": 20},
    "hadath": {"News": 15}, "report": {"News": 8}, "journal": {"News": 12},
    "update": {"News": 5}, "breaking": {"News": 10}, "info": {"News": 3},
    "france 24": {"News": 20}, "russia today": {"News": 20}, "trt": {"News": 8},
    "lbc": {"News": 8}, "skynews": {"News": 20}, "tagesschau": {"News": 15},
    "press": {"News": 10}, "bulletin": {"News": 12},
    
    # --- KIDS (0x5) ---
    "kid": {"Kids": 15}, "kids": {"Kids": 15}, "child": {"Kids": 12},
    "cartoon": {"Kids": 20}, "toon": {"Kids": 20}, "anime": {"Kids": 15},
    "anim": {"Kids": 8}, "junior": {"Kids": 12}, "disney": {"Kids": 20},
    "nick": {"Kids": 20}, "cbeebies": {"Kids": 20}, "spacetoon": {"Kids": 25},
    "mbc 3": {"Kids": 25}, "cn": {"Kids": 15}, "pogo": {"Kids": 20},
    "dreamworks": {"Kids": 20}, "baby": {"Kids": 15}, "tales": {"Kids": 8},
    "adventure": {"Kids": 3}, "mouse": {"Kids": 8}, "sponge": {"Kids": 8},
    
    # --- DOCUMENTARY (0x9) ---
    "doc": {"Documentary": 15}, "documentary": {"Documentary": 20},
    "history": {"Documentary": 15}, "historia": {"Documentary": 15},
    "geo": {"Documentary": 12}, "wild": {"Documentary": 15},
    "planet": {"Documentary": 12}, "earth": {"Documentary": 12},
    "animal": {"Documentary": 15}, "science": {"Documentary": 15},
    "discovery": {"Documentary": 20}, "investigation": {"Documentary": 12},
    "crime": {"Documentary": 8}, "nature": {"Documentary": 12},
    "space": {"Documentary": 12}, "universe": {"Documentary": 12},
    "safari": {"Documentary": 12}, "travel": {"Documentary": 12},
    "cook": {"Documentary": 8}, "explorer": {"Documentary": 15},
    
    # --- MUSIC (0x6) ---
    "music": {"Music": 20}, "song": {"Music": 15}, "clip": {"Music": 12},
    "mix": {"Music": 8}, "radio": {"Music": 15}, "mtv": {"Music": 20},
    "melody": {"Music": 15}, "mazzika": {"Music": 20}, "wanasah": {"Music": 20},
    "aghani": {"Music": 20}, "dance": {"Music": 12}, "hits": {"Music": 12},
    "concert": {"Music": 12}, "artist": {"Music": 10},
    
    # --- RELIGIOUS (0x7) ---
    "quran": {"Religious": 25}, "sunnah": {"Religious": 25},
    "iqraa": {"Religious": 20}, "islam": {"Religious": 15},
    "church": {"Religious": 15}, "catholic": {"Religious": 15},
    "resalah": {"Religious": 15}, "majd": {"Religious": 10},
    "karma": {"Religious": 10}, "agape": {"Religious": 15},
    "ctv": {"Religious": 8}, "noursat": {"Religious": 15},
    "prayer": {"Religious": 15}, "sermon": {"Religious": 15},
    
    # --- SHOWS (0x3) ---
    "series": {"Shows": 15}, "show": {"Shows": 8}, "tv": {"Shows": 2},
    "drama": {"Shows": 12}, "soap": {"Shows": 12}, "episode": {"Shows": 10},
    "season": {"Shows": 10}, "mosalsalat": {"Shows": 20},
    "hikaya": {"Shows": 15}, "general": {"Shows": 8},
    "family": {"Shows": 8}, "entertainment": {"Shows": 10},
    "mbc 1": {"Shows": 20}, "mbc 4": {"Shows": 20},
    "mbc drama": {"Shows": 20}, "zee": {"Shows": 8},
    "colors": {"Shows": 8}, "star plus": {"Shows": 8},
    "reality": {"Shows": 10}, "talk": {"Shows": 8}
}

# --- ADULT BLACKLIST ---
ADULT_KEYWORDS = [
    "xxx", "18+", "+18", "adult", "porn", "sex", "erotic", "nude", "hardcore",
    "barely", "hustler", "playboy", "penthouse", "blue movie", "redlight",
    "babes", "brazzers", "dorcel", "private", "vivid", "colours", "night",
    "hot", "love", "sct", "pink", "passion", "girls", "centoxcento", "exotic",
    "xy mix", "xy plus", "man-x", "evilangel", "daring", "lovesuite", "babe",
    "softcore", "uncensored", "after dark", "blue hustler", "dorcel tv"
]

# --- Helper Functions ---
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

def translate_text(text, target_lang='en'):
    if not text or len(text) < 2:
        return "No description available."
    if any('\u0600' <= char <= '\u06FF' for char in text[:30]):
        return text
    
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
                if item and len(item) > 0:
                    translation += item[0]
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
    if os.path.exists(png_path):
        return loadPNG(png_path)
    default_path = os.path.join(ICON_PATH, "default.png")
    if os.path.exists(default_path):
        return loadPNG(default_path)
    return None

# --- ENHANCED CATEGORIZATION ENGINE ---

def is_adult_content(text):
    """Check if content contains adult keywords"""
    if not text:
        return False
    text_lower = text.lower()
    if any(k in text_lower for k in ADULT_KEYWORDS):
        if "essex" not in text_lower and "sussex" not in text_lower and "middlesex" not in text_lower:
            return True
    return False

def calculate_category_score(text):
    """
    Enhanced scoring with multi-word phrase detection
    Returns: Dictionary {Category: Score}
    """
    scores = {
        "Movies": 0, "Sports": 0, "News": 0, "Kids": 0,
        "Documentary": 0, "Music": 0, "Religious": 0, "Shows": 0
    }
    
    if not text:
        return scores
    
    text_lower = text.lower()
    
    # First pass: Multi-word phrases (higher priority)
    for keyword, impact in WEIGHTED_DB.items():
        if ' ' in keyword:  # Multi-word phrase
            if keyword in text_lower:
                for cat, points in impact.items():
                    scores[cat] += points * 1.5  # Boost for exact phrase match
    
    # Second pass: Single word tokens
    tokens = re.split(r'[\W_]+', text_lower)
    for token in tokens:
        if token in WEIGHTED_DB and ' ' not in WEIGHTED_DB[token]:
            impact = WEIGHTED_DB[token]
            for cat, points in impact.items():
                scores[cat] += points
    
    return scores

def classify_content(channel_name, event_name):
    """
    Smart categorization using weighted scoring with channel priority
    """
    # Safety check
    if is_adult_content(channel_name) or is_adult_content(event_name):
        return None, None
    
    # Calculate scores with different weights
    channel_scores = calculate_category_score(channel_name)
    event_scores = calculate_category_score(event_name)
    
    # Combine with channel name having 2x weight (channels are more reliable indicators)
    final_scores = {}
    for cat in channel_scores:
        final_scores[cat] = (channel_scores[cat] * 2.0) + event_scores.get(cat, 0)
    
    # Find winner
    best_cat = "General/Other"
    highest_score = 0
    
    for cat, score in final_scores.items():
        if score > highest_score:
            highest_score = score
            best_cat = cat
    
    # Confidence threshold
    if highest_score < 5:
        return "General/Other", 0x0
    
    # Map to genre nibble
    cat_map = {
        "Movies": 0x1, "News": 0x2, "Shows": 0x3, "Sports": 0x4,
        "Kids": 0x5, "Music": 0x6, "Religious": 0x7, "Documentary": 0x9
    }
    
    return best_cat, cat_map.get(best_cat, 0x0)

def clean_channel_name_fuzzy(name):
    """Clean channel name for deduplication"""
    n = name.lower()
    n = re.sub(r'\b(hd|sd|fhd|4k|uhd|hevc)\b', '', n)
    n = re.sub(r'\+\d+', '', n)
    return re.sub(r'[\W_]+', '', n)

def get_sat_position(ref_str):
    """Extract satellite position from service reference"""
    if ref_str.startswith("4097:") or ref_str.startswith("5001:") or ref_str.startswith("5002:"):
        return "IPTV"
    try:
        parts = ref_str.split(":")
        if len(parts) > 6:
            ns_val = int(parts[6], 16)
            orb_pos = (ns_val >> 16) & 0xFFFF
            if orb_pos == 0xFFFF:
                return "DVB-T/C"
            if orb_pos == 0:
                return ""
            if orb_pos > 1800:
                pos = 3600 - orb_pos
                return f"{pos/10.0:.1f}W"
            else:
                return f"{orb_pos/10.0:.1f}E"
    except:
        pass
    return ""

def calculate_program_progress(start_time, duration):
    """
    Calculate how much of the program has elapsed
    Returns: (progress_percent, time_elapsed_seconds)
    """
    if duration <= 0 or start_time <= 0:
        return 0, 0
    
    current_time = int(time.time())
    
    # Program hasn't started yet
    if current_time < start_time:
        return 0, 0
    
    # Program has ended
    if current_time >= (start_time + duration):
        return 100, duration
    
    elapsed = current_time - start_time
    progress = int((elapsed / float(duration)) * 100)
    
    return progress, elapsed

# --- LIST BUILDER ---

def build_list_entry(category_name, channel_name, sat_info, event_name, 
                     service_ref, genre_nibble, start_time, duration, show_progress=True):
    """Build display entry with progress indicator"""
    icon_pixmap = get_genre_icon(genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    display_name = f"{channel_name} ({sat_info})" if sat_info else channel_name
    
    progress_str = ""
    progress_color = 0xFFFFFF
    progress_pct = 0
    time_elapsed = 0
    
    if show_progress and duration > 0:
        progress_pct, time_elapsed = calculate_program_progress(start_time, duration)
        
        if progress_pct > 0:
            progress_str = f"({progress_pct}%)"
            if progress_pct > 85:
                progress_color = 0xFF4040  # Red (ending soon)
            elif progress_pct > 10:
                progress_color = 0x00FF00  # Green (in progress)
            else:
                progress_color = 0xFFFF00  # Yellow (just started)
    
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, 
         start_time, duration, progress_pct, time_elapsed),
        MultiContentEntryPixmapAlphaTest(pos=(10, 7), size=(50, 50), png=icon_pixmap),
        MultiContentEntryText(pos=(70, 2), size=(550, 30), font=0, 
                            flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, 
                            text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        MultiContentEntryText(pos=(70, 34), size=(550, 28), font=1, 
                            flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, 
                            text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(640, 2), size=(100, 60), font=1, 
                            flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, 
                            text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryText(pos=(750, 2), size=(190, 60), font=1, 
                            flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, 
                            text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(950, 2), size=(100, 60), font=1, 
                            flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, 
                            text=progress_str, color=progress_color, color_sel=progress_color),
    ]
    return res

# --- BACKEND LOGIC ---

def get_categorized_events_list(use_favorites=False, time_offset=0):
    """Scan EPG and build categorized event list"""
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
        if not bouquet_list:
            return []
        
        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content:
            return []
        
        current_time = int(time.time())
        target_timestamp = current_time + time_offset
        lookup_time = -1 if time_offset == 0 else target_timestamp
        show_prog = (time_offset == 0)
        
        for bouquet_entry in bouquet_content:
            if channel_count >= MAX_CHANNELS:
                break
            
            bouquet_ref = eServiceReference(bouquet_entry[0])
            services = service_handler.list(bouquet_ref)
            if not services:
                continue
            
            service_list = services.getContent("SN", True)
            
            for s_ref, s_name in service_list:
                if "::" in s_ref or "---" in s_name:
                    continue
                
                channel_count += 1
                if channel_count >= MAX_CHANNELS:
                    break
                
                sat_info = get_sat_position(s_ref)
                
                try:
                    service_reference = eServiceReference(s_ref)
                    event = epg_cache.lookupEventTime(service_reference, lookup_time)
                    
                    # Fallback for IPTV channels
                    if not event and (s_ref.startswith("4097:") or s_ref.startswith("5001:") or s_ref.startswith("5002:")):
                        parts = s_ref.split(":")
                        if len(parts) > 7:
                            clean_str = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"
                            clean_ref = eServiceReference(clean_str)
                            event = epg_cache.lookupEventTime(clean_ref, lookup_time)
                    
                    if not event:
                        continue
                    
                    event_name = event.getEventName()
                    if not event_name:
                        continue
                    
                    # SMART CLASSIFICATION
                    category, nibble = classify_content(s_name, event_name)
                    if category is None:
                        continue
                    
                    clean_ch = clean_channel_name_fuzzy(s_name)
                    is_hd = "hd" in s_name.lower()
                    
                    start_time = event.getBeginTime()
                    duration = event.getDuration()
                    
                    entry = build_list_entry(category, s_name, sat_info, event_name, 
                                           s_ref, nibble, start_time, duration, show_prog)
                    
                    # Deduplication: prefer HD
                    if clean_ch in unique_channels:
                        existing_entry, existing_is_hd = unique_channels[clean_ch]
                        if is_hd and not existing_is_hd:
                            unique_channels[clean_ch] = (entry, is_hd)
                    else:
                        unique_channels[clean_ch] = (entry, is_hd)
                
                except:
                    continue
    
    except:
        return []
    
    return [val[0] for val in unique_channels.values()]

# --- GUI SCREEN ---

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
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MenuActions", 
                                     "EPGSelectActions", "InfoActions"], {
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
        self.sort_mode = 'progress'  # Default to progress-based sorting
        self.time_modes = [("Time: Now", 0), ("Time: +1h", 3600), 
                          ("Time: +2h", 7200), ("Time: Tonight", 14400)]
        self.time_mode_index = 0
        
        self.onLayoutFinish.append(self.on_start)
    
    def on_start(self):
        self.refresh_list()
    
    def refresh_list(self):
        source_text = "Favorites" if self.use_favorites else "All Channels"
        time_label, time_offset = self.time_modes[self.time_mode_index]
        self["status_label"].setText(f"Scanning {source_text} ({time_label})...")
        self["key_red"].setText(time_label)
        self.full_list = get_categorized_events_list(self.use_favorites, time_offset)
        
        if not self.full_list:
            self["status_label"].setText(f"No events for {time_label}.")
            self["event_list"].setList([])
            return
        
        self.current_filter = None
        self.current_sat_filter = None
        self.apply_sorting()
        self.apply_filter()
    
    def show_translated_info(self):
        current_selection = self["event_list"].getCurrent()
        if not current_selection:
            return
        
        payload = current_selection[0]
        event_name = payload[3]
        service_ref = payload[4]
        start_time = payload[5]
        
        epg_cache = eEPGCache.getInstance()
        text_to_translate = event_name
        
        try:
            event = epg_cache.lookupEventTime(eServiceReference(service_ref), start_time)
            if event:
                short = event.getShortDescription() or ""
                ext = event.getExtendedDescription() or ""
                full = f"{event_name}\n\n{short}\n{ext}".
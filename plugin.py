# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 2.9 (Fixed for Python 3)
#  Description: Connectivity Fix, Category Sorting, Satellite Filter, Update.
# ============================================================================

import os
import time
import re
import json
from sys import version_info
from urllib.parse import quote  # Fixed import for Python 3

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
from enigma import eEPGCache, eServiceReference, eServiceCenter, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, loadPNG, quitMainloop, eTimer
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

# --- Configuration ---
config.plugins.WhatToWatch = ConfigSubsection()
config.plugins.WhatToWatch.api_key = ConfigText(default="", visible_width=50, fixed_size=False)
config.plugins.WhatToWatch.enable_ai = ConfigYesNo(default=False)

# --- Constants ---
VERSION = "2.9"
AUTHOR = "reali22"
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"
CACHE_FILE = "/etc/enigma2/wtw_ai_cache.json"

# --- ADULT BLACKLIST ---
ADULT_KEYWORDS = [
    "xxx", "18+", "+18", "adult", "porn", "sex", "erotic", "nude", "hardcore", 
    "barely", "hustler", "playboy", "penthouse", "blue movie", "redlight", 
    "babes", "brazzers", "dorcel", "private", "vivid", "colours", "night", 
    "hot", "love", "sct", "pink", "passion", "girls", "centoxcento", "exotic",
    "xy mix", "xy plus", "man-x", "evilangel", "daring", "lovesuite", "babe",
    "softcore", "uncensored", "after dark", "blue hustler", "dorcel tv"
]

# --- 1. Global Helpers ---
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py") # Fixed: Defined missing variable
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")

# AI Cache
AI_CACHE = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r') as f: AI_CACHE = json.load(f)
    except: pass

def save_ai_cache():
    try:
        with open(CACHE_FILE, 'w') as f: json.dump(AI_CACHE, f)
    except: pass

def ask_gemini_category(text):
    """
    Uses system cURL to bypass Python SSL issues.
    """
    api_key = config.plugins.WhatToWatch.api_key.value
    if not api_key or len(api_key) < 10: return None, False
    
    cache_key = text.lower().strip()
    if cache_key in AI_CACHE: return AI_CACHE[cache_key], True

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Escape quotes for shell command
    safe_text = text.replace("'", "").replace('"', "")
    prompt = f"Classify into ONE: Sports, Movies, News, Kids, Documentary, Music, Religious, Shows. Input: {safe_text}"
    
    # Construct JSON payload for cURL
    json_data = '{"contents": [{"parts": [{"text": "' + prompt + '"}]}]}'
    
    # CURL COMMAND: -k (insecure/no-ssl-check), -s (silent), -X POST
    cmd = f"curl -k -s -H 'Content-Type: application/json' -d '{json_data}' '{url}' > /tmp/wtw_response.json"
    
    try:
        os.system(cmd)
        
        if os.path.exists("/tmp/wtw_response.json"):
            with open("/tmp/wtw_response.json", "r") as f:
                response = json.load(f)
            
            # Check for API error structure
            if "error" in response:
                print(f"[WtW] API Error: {response['error']}")
                return None, False

            answer = response['candidates'][0]['content']['parts'][0]['text'].strip()
            
            mapping = {
                "Sports": ("Sports", 0x4), "Movies": ("Movies", 0x1), "News": ("News", 0x2),
                "Kids": ("Kids", 0x5), "Music": ("Music", 0x6), "Documentary": ("Documentary", 0x9),
                "Religious": ("Religious", 0x7), "Shows": ("Shows", 0x3)
            }
            
            for k, v in mapping.items():
                if k.lower() in answer.lower():
                    AI_CACHE[cache_key] = v
                    return v, True
            
            # Default fallback if AI answers something else
            res = ("General/Other", 0x0)
            AI_CACHE[cache_key] = res
            return res, True
            
    except Exception as e:
        print(f"[WtW] Curl/Parse Error: {e}")
        return None, False
        
    return None, False

def translate_text(text, target_lang='en'):
    """
    Uses cURL for translation to avoid SSL errors.
    """
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

def get_genre_icon(nibble):
    icon_map = {0x1: "movies.png", 0x2: "news.png", 0x3: "show.png", 0x4: "sports.png", 0x5: "kids.png", 0x6: "music.png", 0x7: "arts.png", 0x8: "social.png", 0x9: "science.png", 0xA: "leisure.png", 0xB: "arts.png"}
    icon_name = icon_map.get(nibble, "default.png")
    png_path = os.path.join(ICON_PATH, icon_name)
    if os.path.exists(png_path): return loadPNG(png_path)
    default_path = os.path.join(ICON_PATH, "default.png")
    if os.path.exists(default_path): return loadPNG(default_path)
    return None

# --- 2. Classification Logic ---
def is_adult_content(text):
    if not text: return False
    text_lower = text.lower()
    if any(k in text_lower for k in ADULT_KEYWORDS):
        if "essex" not in text_lower and "sussex" not in text_lower and "middlesex" not in text_lower:
             return True
    return False

def classify_content_hybrid(channel_name, event_name, allow_api=False):
    if is_adult_content(channel_name) or is_adult_content(event_name): return None, None, False
    ch_lower = channel_name.lower()
    evt_lower = event_name.lower() if event_name else ""

    # FAST OFFLINE CHECK
    if any(k in ch_lower for k in ["cartoon", "cn ", "nick", "disney", "boomerang", "spacetoon", "mbc 3", "pogo", "majid", "dreamworks", "baby", "kika", "gulli", "clan"]): return "Kids", 0x5, False
    if any(k in evt_lower for k in ["cartoon", "animation", "anime", "sponge", "patrol", "mouse", "tom and jerry"]): return "Kids", 0x5, False
    
    if any(k in ch_lower for k in ["sport", "soccer", "football", "kora", "racing", "f1", "wwe", "ufc", "fight", "arena", "calcio", "match", "dazn", "nba", "espn", "bein", "ssc", "alkass", "ad sport", "dubai sport", "on sport", "euro", "bt sport", "sky sport", "tsn"]): return "Sports", 0x4, False
    if any(k in evt_lower for k in [" vs ", "live:", "match", "cup", "league", "football", "soccer", "racing", "tournament", "championship", "derby"]): return "Sports", 0x4, False
    
    if any(k in ch_lower for k in ["news", "akhbar", "arabia", "jazeera", "hadath", "bbc", "cnn", "cnbc", "bloomberg", "weather", "trt", "lbc", "skynews", "france 24", "russia today", "euronews", "tagesschau", "welt", "al araby", "alghad", "asharq", "watania", "ekhbariya", "dw"]): return "News", 0x2, False
    
    if any(k in ch_lower for k in ["doc", "history", "historia", "nat geo", "wild", "planet", "earth", "animal", "science", "investigation", "crime", "discovery", "tlc", "quest", "geographic", "arte", "phoenix", "explorer"]): return "Documentary", 0x9, False
    
    if any(k in ch_lower for k in ["quran", "sunnah", "iqraa", "resalah", "majd", "karma", "miracle", "ctv", "aghapy", "noursat", "god tv", "ewtn", "bibel", "makkah", "madinah", "islam", "church"]): return "Religious", 0x7, False
    
    if any(k in ch_lower for k in ["music", "song", "clip", "mix", "fm", "radio", "mtv", "vh1", "melody", "mazzika", "rotana clip", "wanasah", "aghani", "4fun", "eska", "polo", "kiss", "dance", "hits"]): return "Music", 0x6, False
    
    if any(k in ch_lower for k in ["movie", "film", "cinema", "cine", "kino", "aflam", "vod", "box office", "hbo", "sky cinema", "mbc 2", "mbc max", "mbc action", "rotana cinema", "zee aflam", "b4u", "osn movies", "amc", "fox movies", "paramount", "tcm", "filmbox", "sony max"]): return "Movies", 0x1, False
    
    if any(k in ch_lower for k in ["drama", "series", "mosalsalat", "hikaya", "show", "tv", "general", "family", "novelas", "soaps", "mbc 1", "mbc 4", "mbc drama", "mbc masr", "rotana khalijia", "zee alwan", "zee tv", "star plus", "colors", "sony", "sky one", "bbc one", "itv", "rai 1", "canale 5", "tf1", "zdf", "rtl", "mediaset"]): return "Shows", 0x3, False

    # AI Fallback (Cached Only during bulk scan)
    cache_key = f"{channel_name} {event_name}".lower().strip()
    if cache_key in AI_CACHE:
        return AI_CACHE[cache_key][0], AI_CACHE[cache_key][1], True

    return "General/Other", 0x0, False

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
        MultiContentEntryPixmapAlphaTest(pos=(10, 7), size=(50, 50), png=icon_pixmap),
        MultiContentEntryText(pos=(70, 2), size=(550, 30), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=display_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        MultiContentEntryText(pos=(70, 34), size=(550, 28), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        MultiContentEntryText(pos=(640, 2), size=(100, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        MultiContentEntryText(pos=(750, 2), size=(190, 60), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=category_name, color=0xFFFF00, color_sel=0xFFFF00),
        MultiContentEntryText(pos=(950, 2), size=(100, 60), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
    ]
    return res

# --- 5. Configuration Screen ---
class WhatToWatchSetup(ConfigListScreen, Screen):
    skin = """<screen position="center,center" size="800,400" title="What to Watch AI Settings">
            <widget name="config" position="10,10" size="780,300" scrollbarMode="showOnDemand" />
            <widget name="key_red" position="10,360" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="0" />
            <widget name="key_green" position="160,360" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="0" />
            <widget name="key_yellow" position="310,360" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="0" />
        </screen>"""
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.list = []
        ConfigListScreen.__init__(self, self.list, session=self.session)
        self.createSetup()
        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Save")
        self["key_yellow"] = Label("Test API")
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "red": self.cancel, "green": self.save, "yellow": self.test_api, 
            "save": self.save, "cancel": self.cancel, "ok": self.save
        }, -2)

    def createSetup(self):
        self.list = [
            getConfigListEntry("Enable AI Categorization (Gemini)", config.plugins.WhatToWatch.enable_ai),
            getConfigListEntry("Gemini API Key", config.plugins.WhatToWatch.api_key)
        ]
        self["config"].list = self.list
        self["config"].setList(self.list)

    def test_api(self):
        self.session.open(MessageBox, "Testing API (cURL)...", type=MessageBox.TYPE_INFO, timeout=2)
        test_query = "BBC World News"
        result, success = ask_gemini_category(test_query)
        if success:
            self.session.open(MessageBox, f"Success!\nAI classified '{test_query}' as: {result[0]}", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "Connection Failed!\nAPI Error or No Internet (Check cURL).", MessageBox.TYPE_ERROR)

    def save(self):
        for x in self["config"].list: x[1].save()
        config.plugins.WhatToWatch.save()
        self.close()

    def cancel(self):
        for x in self["config"].list: x[1].cancel()
        self.close()

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
        self.time_modes = [("Time: Now", 0), ("Time: +1h", 3600), ("Time: +2h", 7200), ("Time: Tonight", 14400)]
        self.time_mode_index = 0
        
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
        self["status_label"].setText(f"Loading {source_text} list...")
        
        service_handler = eServiceCenter.getInstance()
        ref_str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' if self.use_favorites else '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        bouquet_root = eServiceReference(ref_str)
        bouquet_list = service_handler.list(bouquet_root)
        
        if not bouquet_list:
            self["status_label"].setText("Error: No Bouquets found.")
            return

        bouquet_content = bouquet_list.getContent("SN", True)
        if not bouquet_content: return

        for bouquet_entry in bouquet_content:
            bouquet_ref = eServiceReference(bouquet_entry[0])
            services = service_handler.list(bouquet_ref)
            if services:
                self.raw_services.extend(services.getContent("SN", True))
                if len(self.raw_services) > 2000: break

        self["status_label"].setText(f"Found {len(self.raw_services)} channels. Processing...")
        self.process_timer.start(10, False)

    def process_batch(self):
        if not self.raw_services:
            self.process_timer.stop()
            self["status_label"].setText(f"Done. {len(self.full_list)} events loaded.")
            if config.plugins.WhatToWatch.enable_ai.value: save_ai_cache()
            return

        BATCH_SIZE = 10 
        epg_cache = eEPGCache.getInstance()
        current_time = int(time.time())
        _, time_offset = self.time_modes[self.time_mode_index]
        lookup_time = -1 if time_offset == 0 else current_time + time_offset
        show_prog = (time_offset == 0)

        for _ in range(BATCH_SIZE):
            if not self.raw_services: break
            s_ref, s_name = self.raw_services.pop(0)
            
            if "::" in s_ref or "---" in s_name: continue
            
            try:
                service_reference = eServiceReference(s_ref)
                event = epg_cache.lookupEventTime(service_reference, lookup_time)
                
                if not event and (s_ref.startswith("4097:") or s_ref.startswith("5001:")):
                    parts = s_ref.split(":")
                    if len(parts) > 7:
                        clean_str = "1:0:1:" + ":".join(parts[3:7]) + ":0:0:0:"
                        event = epg_cache.lookupEventTime(eServiceReference(clean_str), lookup_time)

                if not event: continue
                event_name = event.getEventName()
                if not event_name: continue

                category, nibble, used_ai = classify_content_hybrid(s_name, event_name, allow_api=False)
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
            self["status_label"].setText(f"Scanning... {len(self.full_list)} channels found")

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

        show_prog = (self.time_modes[self.time_mode_index][1] == 0)
        self.full_list = []
        for item in filtered:
            entry = build_list_entry(
                item["cat"], item["name"], item["sat"], item["evt"], item["ref"], 
                item["nib"], item["start"], item["dur"], show_prog
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

    def toggle_time_filter(self):
        self.time_mode_index = (self.time_mode_index + 1) % len(self.time_modes)
        self.start_full_rescan()

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
        menu = [("Toggle Source", "src"), ("Filter Satellite", "sat"), ("Sort", "sort"), ("Update", "upd"), ("AI Settings", "ai")]
        self.session.openWithCallback(self.menu_cb, ChoiceBox, title="Options", list=menu)

    def menu_cb(self, choice):
        if not choice: return
        c = choice[1]
        if c == "src": self.use_favorites = not self.use_favorites; self.start_full_rescan()
        elif c == "sat": self.show_sat_menu()
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
def Plugins(**kwargs): return [PluginDescriptor(name=f"What to Watch v{VERSION}", description="AI EPG Browser", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

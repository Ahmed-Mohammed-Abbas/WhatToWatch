# -*- coding: utf-8 -*-
# ============================================================================
#  Plugin: What to Watch
#  Version: 3.5 (Wider Sidebar Edition)
#  Author: reali22
#  Description: Left Sidebar UI (20% wider). Red Button = Satellite.
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
VERSION = "3.5"
AUTHOR = "reali22"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")
UPDATE_URL_VER = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/version.txt"
UPDATE_URL_PY = "https://raw.githubusercontent.com/Ahmed-Mohammed-Abbas/WhatToWatch/main/plugin.py"

# --- SMART CATEGORY DATABASE ---
# --- ENHANCED SMART CATEGORY DATABASE ---
# Replace the entire CATEGORIES dictionary with this enhanced version

CATEGORIES = {
    "Kids": (
        # Channel keywords - Higher priority
        ["cartoon", "cn ", "nick", "disney", "boomerang", "spacetoon", "mbc 3", "pogo", 
         "majid", "dreamworks", "baby", "kika", "gulli", "clan", "cbeebies", "citv", "pop", 
         "tiny", "junior", "jeem", "baraem", "fix & foxi", "duck", "kids", "child", "youth",
         "tiji", "toyor", "طيور", "براعم", "سمسم", "كراميش"],
        # Event keywords - More comprehensive
        ["cartoon", "animation", "anime", "sponge", "patrol", "mouse", "tom and jerry", 
         "pig", "bear", "tales", "princess", "dragon", "lego", "pokemon", "paw patrol",
         "peppa", "dora", "blues clues", "sesame", "muppet", "elmo", "barney", "teletubbies",
         "power ranger", "transformer", "avenger", "spider-man", "spiderman", "batman", "superman",
         "frozen", "moana", "toy story", "cars", "nemo", "incredibles", "shrek", "minion",
         "teenage", "ninja turtle", "adventure time", "gravity falls", "ben 10", "bakugan",
         "beyblade", "digimon", "yu-gi-oh", "doraemon", "shin chan", "conan", "detective",
         "scooby", "looney", "bugs bunny", "daffy", "tweety", "sylvester", "popeye"]
    ),
    "Sports": (
        ["sport", "espn", "bein", "sky sport", "bt sport", "euro", "dazn", "ssc", "alkass", 
         "ad sport", "dubai sport", "on sport", "nba", "racing", "motogp", "f1", "wwe", "ufc", 
         "fight", "box", "arena", "tsn", "super", "calcio", "canal+ sport", "eleven", 
         "polsat sport", "match!", "setanta", "extreme", "tennis", "golf", "cricket", "rugby",
         "nfl", "mlb", "nhl", "fifa", "olympics", "الرياضية", "كأس", "الكأس"],
        [" vs ", " v ", "live:", "match", "cup", "league", "football", "soccer", "racing", 
         "tournament", "championship", "derby", "qualifying", "final", "bundesliga", "laliga", 
         "serie a", "premier league", "champions league", "europa league", "world cup",
         "basketball", "tennis", "golf", "cricket", "rugby", "boxing", "mma", "wrestling",
         "formula", "motogp", "rally", "cycling", "swimming", "athletics", "olympics",
         "playoff", "semi-final", "quarter-final", "kick-off", "highlights", "goal",
         "penalty", "overtime", "innings", "touchdown", "slam", "grand prix", "podium",
         "ligue 1", "eredivisie", "primeira liga", "scottish premiership"]
    ),
    "News": (
        ["news", "cnn", "bbc", "jazeera", "alarabiya", "hadath", "skynews", "cnbc", "bloomberg", 
         "weather", "rt ", "france 24", "trt", "dw", "watania", "ekhbariya", "alaraby", "alghad", 
         "asharq", "lbc", "tagesschau", "welt", "n-tv", "rai news", "24h", "fox news", "msnbc",
         "nbc news", "abc news", "cbs news", "euronews", "press tv", "الإخبارية", "الحدث", "الأخبار"],
        ["news", "journal", "report", "briefing", "update", "headline", "politics", "weather", 
         "parliament", "breaking", "bulletin", "newscast", "press conference", "interview",
         "debate", "election", "vote", "summit", "diplomatic", "crisis", "emergency",
         "forecast", "stock market", "economy", "business news", "political", "government",
         "president", "minister", "senate", "congress", "الأخبار", "نشرة", "تقرير"]
    ),
    "Documentary": (
        ["doc", "history", "historia", "nat geo", "national geographic", "wild", "planet", 
         "animal", "science", "investigation", "crime", "discovery", "tlc", "quest", "arte", 
         "phoenix", "explorer", "smithsonian", "eden", "viasat", "focus", "dmax", "curiosity",
         "knowledge", "learning", "h2", "military", "biography", "وثائقي", "وثائقية"],
        ["documentary", "wildlife", "expedition", "universe", "factory", "engineering", 
         "survival", "ancient", "world war", "nature", "safari", "shark", "space", "cosmos",
         "ocean", "jungle", "desert", "arctic", "antarctica", "volcano", "earthquake",
         "dinosaur", "prehistoric", "civilization", "pharaoh", "rome", "egypt", "maya",
         "investigation", "mystery", "crime scene", "forensic", "detective", "murder",
         "serial killer", "biography", "life story", "behind", "secret", "untold",
         "technology", "innovation", "invention", "science", "physics", "chemistry",
         "biology", "astronomy", "geology", "archaeology", "anthropology", "explorer"]
    ),
    "Movies": (
        ["movie", "film", "cinema", "cine", "kino", "aflam", "hbo", "sky cinema", "mbc 2", 
         "mbc max", "mbc action", "mbc bollywood", "rotana cinema", "rotana classic", 
         "zee aflam", "b4u", "osn movies", "amc", "fox movies", "paramount", "tcm", "filmbox", 
         "sony max", "star movies", "wb tv", "universal", "starz", "showtime", "cinemax",
         "أفلام", "سينما", "الأفلام"],
        ["starring", "directed by", "director:", "cast:", "thriller", "action", "comedy", 
         "drama", "horror", "sci-fi", "science fiction", "romance", "adventure", "blockbuster",
         "western", "noir", "mystery", "suspense", "fantasy", "animated", "musical",
         "biographical", "historical", "war film", "crime film", "gangster", "heist",
         "martial arts", "superhero", "zombie", "vampire", "ghost", "monster",
         "oscar", "academy award", "golden globe", "cannes", "venice", "berlin",
         "premiere", "exclusive", "فيلم", "بطولة"]
    ),
    "Religious": (
        ["quran", "sunnah", "iqraa", "resalah", "majd", "karma", "miracle", "ctv", "aghapy", 
         "noursat", "god tv", "ewtn", "bibel", "makkah", "madinah", "islam", "church", 
         "peace tv", "huda", "guide", "al-rahma", "القرآن", "الرسالة", "المجد", "الرحمة"],
        ["prayer", "mass", "worship", "gospel", "recitation", "bible", "quran", "sheikh",
         "sermon", "preacher", "imam", "priest", "rabbi", "holy", "sacred", "spiritual",
         "faith", "religion", "pilgrimage", "hajj", "ramadan", "easter", "christmas",
         "passover", "diwali", "vespers", "liturgy", "communion", "baptism", "confession",
         "meditation", "contemplation", "صلاة", "دعاء", "تلاوة", "خطبة", "قرآن"]
    ),
    "Music": (
        ["music", "mtv", "vh1", "melody", "mazzika", "rotana clip", "wanasah", "aghani", 
         "4fun", "eska", "polo", "kiss", "dance", "hits", "trace", "mezzo", "classica", 
         "nrj", "radio", "fm", "vevo", "beat", "jam", "الموسيقى", "أغاني", "كليب"],
        ["concert", "videoclip", "video clip", "music video", "hits", "top 40", "top 100", 
         "playlist", "songs", "symphony", "orchestra", "festival", "live performance",
         "acoustic", "unplugged", "remix", "mashup", "album", "single", "track",
         "rock", "pop", "jazz", "classical", "hip hop", "rap", "r&b", "soul", "blues",
         "country", "folk", "electronic", "techno", "house", "trance", "reggae",
         "metal", "punk", "indie", "alternative", "opera", "choir", "band", "artist",
         "singer", "musician", "guitarist", "pianist", "drummer", "أغنية", "موسيقى", "كليب"]
    ),
    "Shows": (
        ["drama", "series", "mosalsalat", "hikaya", "mbc 1", "mbc 4", "mbc drama", "mbc masr", 
         "rotana drama", "rotana khalijia", "zee alwan", "zee tv", "star plus", "colors", 
         "sony", "sky one", "sky atlantic", "fox", "comedy central", "syfy", "axn", "novelas", 
         "bet", "e!", "lifetime", "hallmark", "freeform", "المسلسلات", "دراما", "مسلسل"],
        ["episode", "season", "series", "show", "reality", "soap", "telenovela", "sitcom",
         "talk show", "game show", "quiz", "competition", "talent", "cooking show",
         "makeover", "home improvement", "dating", "bachelor", "survivor", "big brother",
         "voice", "idol", "got talent", "master chef", "bake off", "fashion",
         "drama series", "comedy series", "thriller series", "mystery series", "crime series",
         "anthology", "miniseries", "special", "finale", "premiere", "pilot",
         "تمثيلية", "حلقة", "موسم", "برنامج", "مسلسل"]
    )
}

# Enhanced adult keywords
ADULT_KEYWORDS = ["xxx", "18+", "porn", "adult", "sex", "erotic", "brazzers", "hustler", 
                  "playboy", "dorcel", "vivid", "redlight", "+18", "sexy", "nude", "naked"]

# --- ENHANCED CLASSIFICATION LOGIC WITH SCORING ---
# Replace the classify_enhanced function with this improved version

def classify_enhanced(channel_name, event_name):
    """
    Enhanced multi-tier classification with keyword scoring.
    Returns (category_name, genre_nibble) or (None, None) for adult content.
    """
    ch_clean = channel_name.lower()
    evt_clean = event_name.lower() if event_name else ""
    
    # Filter adult content first
    if is_adult(ch_clean) or is_adult(evt_clean):
        return None, None

    # TIER 1: Strong Channel Name Lock (Highest Priority)
    # Direct channel name match - most reliable indicator
    for cat, (ch_kws, _) in CATEGORIES.items():
        for kw in ch_kws:
            if kw in ch_clean:
                return get_cat_data(cat)

    # TIER 2: Event Name Scoring System (Medium Priority)
    # Count and weight keyword matches for each category
    category_scores = {}
    for cat, (_, evt_kws) in CATEGORIES.items():
        score = 0
        for kw in evt_kws:
            if kw in evt_clean:
                # Multi-word keywords are more specific - give higher weight
                word_count = len(kw.split())
                if word_count > 1:
                    score += word_count * 2  # Double weight for multi-word matches
                else:
                    score += 1  # Single weight for single-word matches
        
        if score > 0:
            category_scores[cat] = score
    
    # Return category with highest score if any matches found
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        return get_cat_data(best_category)

    # TIER 3: Partial Channel Name Match (Lowest Priority)
    # Weak indicators - only used as last resort
    partial_channel_indicators = {
        "Kids": ["kid", "child", "junior", "baby", "teen"],
        "Sports": ["fc ", "team", "club", "athletic"],
        "Movies": ["max", "premiere", "classic", "gold"],
        "Shows": ["drama", "plus", "one", "prime"],
        "Music": ["music", "melody", "song"],
        "News": ["today", "now", "live"]
    }
    
    for cat, indicators in partial_channel_indicators.items():
        for ind in indicators:
            if ind in ch_clean:
                return get_cat_data(cat)

    # Default fallback
    return ("General", 0x3)

# Updated is_adult function with more false positive exclusions
def is_adult(text):
    """Check if text contains adult content keywords"""
    if not text:
        return False
    t = text.lower()
    # Check for adult keywords but exclude false positives
    for keyword in ADULT_KEYWORDS:
        if keyword in t:
            # Exclude common false positives
            if "essex" not in t and "sussex" not in t and "middlesex" not in t:
                return True
    return False 

# --- List Builder (Wider Sidebar Layout) ---
def build_list_entry(category_name, channel_name, sat_info, event_name, service_ref, genre_nibble, start_time, duration, show_progress=True):
    icon_pixmap = get_genre_icon(genre_nibble)
    time_str = time.strftime("%H:%M", time.localtime(start_time)) if start_time > 0 else ""
    
    # Progress Logic
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
    
    # --- WIDER SIDEBAR LAYOUT (Total Width ~504) ---
    res = [
        (category_name, channel_name, sat_info, event_name, service_ref, start_time, duration),
        # 1. Icon (Top Left)
        MultiContentEntryPixmapAlphaTest(pos=(10, 10), size=(50, 50), png=icon_pixmap),
        
        # 2. Channel Name (Top Right) - Wider
        MultiContentEntryText(pos=(70, 5), size=(330, 25), font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=channel_name, color=0xFFFFFF, color_sel=0xFFFFFF),
        
        # 3. Event Name (Below Channel) - Wider
        MultiContentEntryText(pos=(70, 30), size=(330, 25), font=1, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=event_name, color=0xA0A0A0, color_sel=0xD0D0D0),
        
        # 4. Time (Far Right Top) - Shifted Right
        MultiContentEntryText(pos=(410, 5), size=(80, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=time_str, color=0x00FFFF, color_sel=0x00FFFF),
        
        # 5. Progress/Category (Far Right Bottom) - Shifted Right
        MultiContentEntryText(pos=(410, 30), size=(80, 25), font=1, flags=RT_HALIGN_RIGHT|RT_VALIGN_CENTER, text=progress_str, color=progress_color, color_sel=progress_color),
        
        # 6. Satellite Info (Tiny, below icon)
        MultiContentEntryText(pos=(10, 60), size=(50, 20), font=2, flags=RT_HALIGN_CENTER|RT_VALIGN_CENTER, text=sat_info, color=0x808080, color_sel=0x808080),
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
    # Position: Left Sidebar (0,0). Width=504 (20% wider). Height=720 (Full Height).
    skin = f"""
        <screen position="0,0" size="504,720" title="What to Watch" flags="wfNoBorder" backgroundColor="#20000000">
            <eLabel position="0,0" size="504,720" backgroundColor="#181818" zPosition="-1" />
            
            <eLabel text="What to Watch" position="10,10" size="484,40" font="Regular;28" halign="center" valign="center" foregroundColor="#00ff00" backgroundColor="#181818" transparent="1" />
            <eLabel text="By {AUTHOR}" position="10,45" size="484,20" font="Regular;16" halign="center" valign="center" foregroundColor="#505050" backgroundColor="#181818" transparent="1" />

            <widget name="status_label" position="10,70" size="484,30" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <widget name="event_list" position="5,110" size="494,500" scrollbarMode="showOnDemand" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,620" size="25,25" alphatest="on" />
            <widget name="key_red" position="55,620" size="190,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="20,660" size="25,25" alphatest="on" />
            <widget name="key_yellow" position="55,660" size="190,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/green.png" position="260,620" size="25,25" alphatest="on" />
            <widget name="key_green" position="295,620" size="190,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <ePixmap pixmap="skin_default/buttons/blue.png" position="260,660" size="25,25" alphatest="on" />
            <widget name="key_blue" position="295,660" size="190,25" zPosition="1" font="Regular;18" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#181818" transparent="1" />
            
            <widget name="info_bar" position="10,690" size="484,20" font="Regular;16" halign="center" valign="center" foregroundColor="#ffff00" backgroundColor="#181818" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["event_list"] = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
        
        # Font Configuration for Sidebar
        self["event_list"].l.setFont(0, gFont("Regular", 22)) # Channel Name
        self["event_list"].l.setFont(1, gFont("Regular", 18)) # Event/Time
        self["event_list"].l.setFont(2, gFont("Regular", 14)) # Sat Info
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
def Plugins(**kwargs): return [PluginDescriptor(name=f"What to Watch v{VERSION}", description="AI EPG Browser", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main)]

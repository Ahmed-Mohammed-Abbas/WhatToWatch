# ============================================================================
#  Plugin: What to Watch (Enhanced Intelligence Edition)
#  Author: reali22 (Enhanced by design refactor)
#  Version: 2.2
# ============================================================================

import os, time, re, json
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
from enigma import (
    eEPGCache, eServiceReference, eServiceCenter,
    eListboxPythonMultiContent, gFont,
    RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER,
    loadPNG, quitMainloop
)
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Plugins.Plugin import PluginDescriptor

VERSION = "2.2"
AUTHOR = "reali22"

PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/WhatToWatch/")
ICON_PATH = os.path.join(PLUGIN_PATH, "icons")
PLUGIN_FILE_PATH = os.path.join(PLUGIN_PATH, "plugin.py")

# ----------------------------------------------------------------------------
# WEIGHTED OFFLINE KNOWLEDGE BASE
# ----------------------------------------------------------------------------

WEIGHTED_DB = {
    "sport": {"Sports": 10}, "football": {"Sports": 10}, "match": {"Sports": 5},
    "live": {"Sports": 2, "Music": 1}, "vs": {"Sports": 3},
    "bein": {"Sports": 20}, "espn": {"Sports": 20}, "ssc": {"Sports": 15},
    "movie": {"Movies": 10}, "film": {"Movies": 10}, "cinema": {"Movies": 10},
    "hbo": {"Movies": 15}, "mbc 2": {"Movies": 20}, "aflam": {"Movies": 15},
    "news": {"News": 15}, "breaking": {"News": 5}, "bbc": {"News": 10},
    "cnn": {"News": 15}, "jazeera": {"News": 15}, "france 24": {"News": 15},
    "kids": {"Kids": 10}, "cartoon": {"Kids": 15}, "disney": {"Kids": 15},
    "spacetoon": {"Kids": 20}, "mbc 3": {"Kids": 20},
    "doc": {"Documentary": 10}, "history": {"Documentary": 10},
    "discovery": {"Documentary": 15}, "animal": {"Documentary": 10},
    "music": {"Music": 15}, "song": {"Music": 10}, "mtv": {"Music": 15},
    "quran": {"Religious": 20}, "islam": {"Religious": 10},
    "series": {"Shows": 10}, "episode": {"Shows": 5},
    "drama": {"Shows": 8}
}

ADULT_KEYWORDS = [
    "xxx","18+","porn","sex","erotic","nude","playboy","brazzers",
    "adult","hardcore","blue movie","redlight"
]

CATEGORY_NIBBLES = {
    "Movies": 0x1, "News": 0x2, "Shows": 0x3, "Sports": 0x4,
    "Kids": 0x5, "Music": 0x6, "Religious": 0x7, "Documentary": 0x9
}

# ----------------------------------------------------------------------------
# INTELLIGENT CLASSIFICATION ENGINE
# ----------------------------------------------------------------------------

def is_adult_content(text):
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in ADULT_KEYWORDS)

def calculate_category_score_advanced(text):
    scores = {k: 0 for k in CATEGORY_NIBBLES}
    if not text:
        return scores

    t = text.lower()

    # Phrase-level match (strongest)
    for key, impact in WEIGHTED_DB.items():
        if " " in key and key in t:
            for cat, pts in impact.items():
                scores[cat] += pts * 1.5
            t = t.replace(key, " ")

    # Token-level match
    tokens = re.split(r'[\W_]+', t)
    for tok in tokens:
        if tok in WEIGHTED_DB:
            for cat, pts in WEIGHTED_DB[tok].items():
                scores[cat] += pts

    return scores

def classify_content(channel, title, description):
    if is_adult_content(channel) or is_adult_content(title):
        return None, None

    ch = calculate_category_score_advanced(channel)
    ti = calculate_category_score_advanced(title)
    ds = calculate_category_score_advanced(description)

    final = {}
    for cat in CATEGORY_NIBBLES:
        final[cat] = (
            ch[cat] * 1.6 +
            ti[cat] * 1.0 +
            ds[cat] * 0.6
        )

    # LIVE boost
    if "live" in title.lower():
        final["Sports"] += 3
        final["News"] += 2

    best = max(final, key=final.get)
    score = final[best]

    if score < 3:
        return "General/Other", 0x0

    return best, CATEGORY_NIBBLES[best]

# ----------------------------------------------------------------------------
# ICON HANDLING
# ----------------------------------------------------------------------------

def get_genre_icon(n):
    mapping = {
        0x1: "movies.png", 0x2: "news.png", 0x3: "show.png",
        0x4: "sports.png", 0x5: "kids.png", 0x6: "music.png",
        0x7: "arts.png", 0x9: "science.png"
    }
    path = os.path.join(ICON_PATH, mapping.get(n, "default.png"))
    return loadPNG(path) if os.path.exists(path) else None

# ----------------------------------------------------------------------------
# SORTING: FRESHNESS METRIC
# ----------------------------------------------------------------------------

def program_freshness(entry):
    payload = entry[0]
    start, duration = payload[5], payload[6]
    now = int(time.time())

    if start > now:
        return float("inf")
    if now > start + duration:
        return float("inf")

    return now - start

# ----------------------------------------------------------------------------
# LIST ENTRY BUILDER
# ----------------------------------------------------------------------------

def build_entry(cat, ch, sat, title, ref, nib, start, dur):
    now = int(time.time())
    progress = ""
    color = 0xFFFFFF
    if start <= now <= start + dur and dur > 0:
        pct = int(((now - start) / float(dur)) * 100)
        progress = f"{pct}%"
        color = 0x00FF00 if pct < 80 else 0xFF4040

    return [
        (cat, ch, sat, title, ref, start, dur),
        MultiContentEntryPixmapAlphaTest((10,7),(50,50), get_genre_icon(nib)),
        MultiContentEntryText((70,2),(520,30),0,RT_HALIGN_LEFT|RT_VALIGN_CENTER,f"{ch} ({sat})",0xFFFFFF),
        MultiContentEntryText((70,34),(520,28),1,RT_HALIGN_LEFT|RT_VALIGN_CENTER,title,0xA0A0A0),
        MultiContentEntryText((610,2),(90,60),1,RT_HALIGN_LEFT|RT_VALIGN_CENTER,time.strftime("%H:%M", time.localtime(start)),0x00FFFF),
        MultiContentEntryText((710,2),(160,60),1,RT_HALIGN_LEFT|RT_VALIGN_CENTER,cat,0xFFFF00),
        MultiContentEntryText((880,2),(90,60),1,RT_HALIGN_RIGHT|RT_VALIGN_CENTER,progress,color),
    ]

# ----------------------------------------------------------------------------
# EVENT SCANNER
# ----------------------------------------------------------------------------

def get_events():
    epg = eEPGCache.getInstance()
    sc = eServiceCenter.getInstance()
    root = eServiceReference('1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
    bl = sc.list(root)
    out, seen = [], set()

    for bref, _ in bl.getContent("SN", True):
        srv = sc.list(eServiceReference(bref))
        for sref, name in srv.getContent("SN", True):
            ev = epg.lookupEventTime(eServiceReference(sref), -1)
            if not ev:
                continue

            title = ev.getEventName()
            desc = (ev.getShortDescription() or "") + " " + (ev.getExtendedDescription() or "")
            cat, nib = classify_content(name, title, desc)
            if cat is None:
                continue

            start, dur = ev.getBeginTime(), ev.getDuration()
            key = re.sub(r'\W+', '', name.lower())
            if key in seen:
                continue

            seen.add(key)
            out.append(build_entry(cat, name, "", title, sref, nib, start, dur))

    return out

# ----------------------------------------------------------------------------
# UI SCREEN
# ----------------------------------------------------------------------------

class WhatToWatchScreen(Screen):
    skin = """
    <screen position="center,center" size="1080,720" title="What To Watch v2.2">
        <widget name="list" position="10,10" size="1060,650"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = MenuList([], content=eListboxPythonMultiContent)
        self["list"].l.setFont(0, gFont("Regular",28))
        self["list"].l.setFont(1, gFont("Regular",24))
        self["list"].l.setItemHeight(65)

        self.sort_mode = "fresh"

        self["actions"] = ActionMap(
            ["OkCancelActions","MenuActions"],
            {
                "ok": self.zap,
                "menu": self.toggle_sort,
                "cancel": self.close
            }, -1
        )

        self.onLayoutFinish.append(self.load)

    def load(self):
        self.data = get_events()
        self.apply_sort()

    def apply_sort(self):
        if self.sort_mode == "fresh":
            self.data.sort(key=program_freshness)
        self["list"].setList(self.data)

    def toggle_sort(self):
        self.sort_mode = "fresh"
        self.apply_sort()

    def zap(self):
        cur = self["list"].getCurrent()
        if cur:
            self.session.nav.playService(eServiceReference(cur[0][4]))

# ----------------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------------

def main(session, **kwargs):
    session.open(WhatToWatchScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="What To Watch v2.2",
            description="Smart Offline EPG Browser",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]
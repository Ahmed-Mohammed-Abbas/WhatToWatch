from Plugins.Plugin import PluginDescriptor
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
import os

# --- Plugin Definition ---
PLUGIN_NAME = "WhatToWatch"
PLUGIN_VERSION = "2.9"
PLUGIN_DESC = "Discover what to watch (Category & Satellite Sort)"
PLUGIN_ICON = "icon.png"

class WhatToWatchMain(Screen):
    skin = """
    <screen name="WhatToWatchMain" position="center,center" size="1200,600" title="What To Watch">
        <widget name="list" position="20,20" size="800,500" scrollbarMode="showOnDemand" />
        <widget name="info" position="840,20" size="340,500" font="Regular;22" halign="left" valign="top" />
        
        <eLabel position="20,540" size="290,5" backgroundColor="#FF0000" />
        <widget name="key_red" position="20,550" size="290,25" zPosition="1" font="Regular;20" halign="center" backgroundColor="#1f1f1f" transparent="1" />
        
        <eLabel position="310,540" size="290,5" backgroundColor="#00FF00" />
        <widget name="key_green" position="310,550" size="290,25" zPosition="1" font="Regular;20" halign="center" backgroundColor="#1f1f1f" transparent="1" />
        
        <eLabel position="600,540" size="290,5" backgroundColor="#FFFF00" />
        <widget name="key_yellow" position="600,550" size="290,25" zPosition="1" font="Regular;20" halign="center" backgroundColor="#1f1f1f" transparent="1" />
        
        <eLabel position="890,540" size="290,5" backgroundColor="#0000FF" />
        <widget name="key_blue" position="890,550" size="290,25" zPosition="1" font="Regular;20" halign="center" backgroundColor="#1f1f1f" transparent="1" />
    </screen>
    """

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self.setTitle("What To Watch - v" + PLUGIN_VERSION)

        # --- Dummy Data for Demonstration ---
        # Format: (Display Name, Category, Satellite)
        self.full_list = [
            ("Premier League - MNU vs LIV", "Sports", "Astra 19.2E"),
            ("BBC News", "News", "Astra 28.2E"),
            ("Discovery Channel", "Documentary", "Hotbird 13E"),
            ("La Liga - RMA vs BAR", "Sports", "Astra 19.2E"),
            ("CNN International", "News", "Hotbird 13E"),
            ("Nat Geo Wild", "Documentary", "Astra 28.2E"),
            ("Serie A - JUV vs MIL", "Sports", "Hotbird 13E"),
            ("Al Jazeera", "News", "Nilesat 7W")
        ]
        
        self.current_list = list(self.full_list)
        self["list"] = MenuList(self.getDisplayList())
        self["info"] = Label("Select an item for details.")

        # Button Labels
        self["key_red"] = Label("Exit")
        self["key_green"] = Label("Refresh")
        self["key_yellow"] = Label("Category: All") # Dynamic Label
        self["key_blue"] = Label("Options")

        # Logic State
        self.categories = ["All", "Sports", "News", "Documentary"]
        self.current_category_index = 0

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.okClicked,
            "cancel": self.close,
            "red": self.close,
            "green": self.refreshData,
            "yellow": self.toggleCategory,  # Yellow: Sort/Filter by Category
            "blue": self.showOptions      # Blue: Options Menu
        }, -1)

    def getDisplayList(self):
        # Helper to format list for MenuList
        return [x[0] for x in self.current_list]

    def refreshData(self):
        # Reset to full list and default view
        self.current_list = list(self.full_list)
        self.current_category_index = 0
        self["key_yellow"].setText("Category: All")
        self["list"].setList(self.getDisplayList())
        self["info"].setText("List refreshed.")

    def okClicked(self):
        idx = self["list"].getSelectedIndex()
        if idx >= 0:
            item = self.current_list[idx]
            details = "Event: %s\nCategory: %s\nSatellite: %s" % (item[0], item[1], item[2])
            self["info"].setText(details)

    # --- YELLOW BUTTON: Cycle Categories ---
    def toggleCategory(self):
        # Cycle index
        self.current_category_index = (self.current_category_index + 1) % len(self.categories)
        cat = self.categories[self.current_category_index]
        
        # Update Label
        self["key_yellow"].setText("Category: " + cat)
        
        # Filter List
        if cat == "All":
            self.current_list = list(self.full_list)
        else:
            self.current_list = [x for x in self.full_list if x[1] == cat]
            
        self["list"].setList(self.getDisplayList())

    # --- BLUE BUTTON: Options Menu ---
    def showOptions(self):
        options = [
            ("Sort by Satellite", "sort_sat"),
            ("Sort by Name", "sort_name"),
            ("Check for Updates", "update"),
            ("About", "about")
        ]
        self.session.openWithCallback(self.handleOption, ChoiceBox, title="Options", list=options)

    def handleOption(self, choice):
        if choice:
            action = choice[1]
            if action == "sort_sat":
                # Sort current list by Satellite (index 2)
                self.current_list.sort(key=lambda x: x[2])
                self["list"].setList(self.getDisplayList())
                self["info"].setText("Sorted by Satellite.")
            elif action == "sort_name":
                # Sort current list by Name (index 0)
                self.current_list.sort(key=lambda x: x[0])
                self["list"].setList(self.getDisplayList())
                self["info"].setText("Sorted by Name.")
            elif action == "update":
                self.runUpdate()
            elif action == "about":
                self.session.open(MessageBox, "WhatToWatch Plugin\nVersion 2.9", MessageBox.TYPE_INFO)

    def runUpdate(self):
        # Execute the update command (same as your terminal command)
        cmd = "wget --no-check-certificate https://github.com/Ahmed-Mohammed-Abbas/WhatToWatch/archive/refs/heads/main.zip -O /tmp/update.zip && unzip -o /tmp/update.zip -d /tmp/ && cp -r /tmp/WhatToWatch-main/* /usr/lib/enigma2/python/Plugins/Extensions/WhatToWatch/ && rm -rf /tmp/update.zip /tmp/WhatToWatch-main"
        os.system(cmd)
        self.session.open(MessageBox, "Update command sent.\nPlease restart GUI to apply changes.", MessageBox.TYPE_INFO)

def main(session, **kwargs):
    session.open(WhatToWatchMain)

def Plugins(**kwargs):
    return PluginDescriptor(
        name=PLUGIN_NAME,
        description=PLUGIN_DESC,
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=PLUGIN_ICON,
        fnc=main
    )

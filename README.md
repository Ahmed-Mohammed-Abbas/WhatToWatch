# WhatToWatch
 install:
cd /usr/lib/enigma2/python/Plugins/Extensions && rm -rf WhatToWatch && wget --no-check-certificate https://github.com/Ahmed-Mohammed-Abbas/WhatToWatch/archive/refs/heads/main.zip -O WhatToWatch.zip && unzip WhatToWatch.zip && mv WhatToWatch-main WhatToWatch && rm WhatToWatch.zip && killall -9 enigma2


-Version: 2.0
This update (v2.0) introduces the most comprehensive categorization engine yet. It includes:

Massive Satellite Database: Added over 200+ new keywords covering Hot Bird 13E, Astra 19.2E, and Nilesat 7W.

New "Religious" Category: Automatically detects Islamic and Christian channels (Quran, Sunnah, CTV, Iqraa, etc.) and groups them under "Arts/Culture/Religion" (0x7).

Refined Logic:

News: Now catches international variants like DW, France 24, TRT, Sky News, and Arabic news Al Hadath, Al Ekhbariya.

Sports: Expanded to include AD Sports, Dubai Sports, Sharjah Sports, Arryadia, Polsat Sport, Match!, etc.

Movies: Fixed detection for Zee Aflam, B4U, Rotana, MBC Bollywood, Sky Cinema, Fox Movies.


-Version: 2.1
This is a major architectural upgrade (v2.1).

I have replaced the old "simple list" checks with a "Weighted Scoring Engine" (Offline AI).

🧠 How the "Offline AI" Works (v2.1)
Instead of just looking for a word, the plugin now scores the channel name and program description.

Example: "Sky Cinema Action"

"Sky" = +1 General

"Cinema" = +10 Movies

"Action" = +5 Movies

Result: Movies Score: 15 (Winner!)

This method is "fuzzy" and works across Arabic, English, French, German, Italian, and Spanish simultaneously without needing an internet connection.


- Version: 3.0
- What to Watch plugin. 🚀 New Features & Enhancements (v3.0)
 * Crash-Proof Update System: Implemented a "Safe Mode" for the update function using try/except blocks. This prevents the system from crashing (Green Screen of Death) if the update server is unreachable or the file is missing.
 * Enhanced Connectivity: Added the --no-check-certificate flag to download commands, ensuring compatibility with older Enigma2 boxes that have outdated SSL certificates.
 * Optimized Sidebar UI:
   * Expanded Dimensions: Increased screen width to 700px and height to 860px to display more content without scrolling.
   * Tight Layout: Reduced visual gaps between the Time, Icon, Channel Name, and Category columns for a cleaner, modern look.
   * Smart Fit: Adjusted text column widths to prevent channel names and event titles from being cut off.
 * Pinning System: Added a "Pin Channel" feature (via the Options menu) to keep your favorite channels permanently at the top of the list, marked with a star (★).
 * Intelligent Categorization:
   * Massive Database: Expanded the internal database to automatically recognize hundreds of additional channels (Sports, Kids, Movies, News, etc.).
   * Smart Abbreviations: Long category names are automatically abbreviated (e.g., "Documentary" -> "Doc.", "Entertainment" -> "Ent.") to save screen space.
 * Tiered Sorting Logic: Channels are sorted by Pinned Status -> Category -> Channel Name for the most intuitive browsing experience.

- Version 3.3
🚀 Upgrade Your E2 Experience: What to Watch v3.3 is Here! 📺
I have completely overhauled the What to Watch plugin to make it the ultimate EPG and Reminder tool for your Enigma2 receiver. Stop scrolling aimlessly and start watching!
✨ New & Powerful Features:
🎨 Stunning Visuals:
 * Traffic Light Progress: Progress bars change color (🟢 Green <35%, 🟡 Yellow <66%, 🔴 Red >66%) so you know exactly how much time is left.
 * Visual Highlights: Channel names turn Green when a reminder is set and Yellow when pinned.
 * Transparent Mode: New option in settings to make the background transparent for a modern look.
 * Smart Picons: Auto-resizing and smart searching for channel logos.
🔔 Advanced Reminders:
 * Smart Alerts: Choose between Notification or Auto-Zap.
 * Weekly Repeat: Never miss an episode of your favorite series.
 * Integrated Watchlist: Press the Green Button to see your personal "My Watchlist" view instantly.
 * Crystal Clear Sound: Fixed audio alerts using ALSA for notification sounds without static noise.
⚡ Speed & Control:
 * Chronological Sorting: Channels are sorted by start time, showing you what starts soonest.
 * Time Travel: Press the Red Button to instantly toggle time slots (+1h, +2h, +4h, etc.).
 * Smart Context Menu: Press OK to decide: Zap immediately or Set/Remove a reminder.
 * Power Shortcuts: Long-press OK to instantly toggle reminders on/off.
🛠️ Reliability:
 * Crash Fixes: Enhanced stability and smarter menus that adapt if a program has already started.
 * Clear All: One-click option to wipe all old notifications.
👇 Download the update now and take control of your TV!



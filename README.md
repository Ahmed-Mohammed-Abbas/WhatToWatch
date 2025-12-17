# WhatToWatch
Version: 2.0
This update (v2.0) introduces the most comprehensive categorization engine yet. It includes:

Massive Satellite Database: Added over 200+ new keywords covering Hot Bird 13E, Astra 19.2E, and Nilesat 7W.

New "Religious" Category: Automatically detects Islamic and Christian channels (Quran, Sunnah, CTV, Iqraa, etc.) and groups them under "Arts/Culture/Religion" (0x7).

Refined Logic:

News: Now catches international variants like DW, France 24, TRT, Sky News, and Arabic news Al Hadath, Al Ekhbariya.

Sports: Expanded to include AD Sports, Dubai Sports, Sharjah Sports, Arryadia, Polsat Sport, Match!, etc.

Movies: Fixed detection for Zee Aflam, B4U, Rotana, MBC Bollywood, Sky Cinema, Fox Movies.

Version: 2.1
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

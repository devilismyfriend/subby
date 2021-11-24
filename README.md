# subby
 Extract PGS/VOBSUB/ASS Embedded Subtitles from video

REQUIREMNETS:

Install Tesseract OCR 5.0 and additional languages

Install Java runtime

Pip install the requirements.txt

Currently only runs on Windows.


Subby is a companion script/tool for Plex server owners or just people that want to streamline subtitle OCR extraction from their media files.

Subby has two methods of operation:

"python3 main.py --plex"

Starts a plex scan using the config.ini paramaters, it will scan all libraries and pass any items with subtitles to subby.

Subby will then find out if the file has PGS/ASS/VOBSUB and if they exist while the file has no SRT file in the same directory, it will extract it from the video using OCR

"python3 main.py "D:/movie.mkv""

This will process whichever file your pointing it to, extracting subtitles if there's no existing SRT files



config.ini - options:

notifyPlex - if true, after the plex scan and subtitle extraction subby will send an update notification to Plex to look for updates on the processed items and only on the processed items.

only4k - Plex scan will collect only 4k items for processing.

exportEmbeddedSRTs - if embedded subs are SRTs, this flag will tell subby to extract it.

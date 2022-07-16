# subby
 Extract PGS/VOBSUB/ASS Embedded Subtitles from video to SRT

# Requirements:
- Install Tesseract OCR 5.0 and additional languages
- Install Java runtime
- Pip install the requirements.txt (`pip install -r requirements.txt)

# Usage
Subby is a companion script/tool for Plex server owners or just people that want to streamline subtitle OCR extraction from their media files.

## Modes
Subby has two methods of operation:

```shell
python3 main.py --plex
```

Starts a plex scan using the `config.ini parameters, it will scan all libraries and pass any items with subtitles to subby.

Subby will then find out if the file has PGS/ASS/VOBSUB and if they exist while the file has no SRT file in the same directory, it will extract it from the video using OCR

```shell
python3 main.py D:/movie.mkv
```

This will process whichever file you're pointing it to, extracting subtitles if there's no existing SRT files present.

## Config

- `notifyPlex`: if true, after the plex scan and subtitle extraction subby will send an update notification to Plex to look for updates on the processed items and only on the processed items.
- `only4k`: Plex scan will collect only 4k items for processing.
- `exportEmbeddedSRTs`: if embedded subs are SRTs, this flag will tell subby to extract it.

## Dependencies
This tool uses:
- MkvToolNix (must be installed for Linux)
- BDSup2Sup
- AssToSrt
- ImageMaker
- PgsReader

#!/usr/bin/env python3

from logging import exception
import os
import subprocess
import json
import pytesseract
from langcodes import Language

from .pgsreader import PGSReader
from .imagemaker import make_image
from PIL import Image
from pysrt import SubRipFile, SubRipItem, SubRipTime
from tqdm import tqdm
import logging
import errno
import signal
import functools
import asstosrt

#from wrapt_timeout_decorator import *
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def language_is_supported(lang):
    for tesseract_lang in pytesseract.get_languages(config=''):
        if Language.get(tesseract_lang) == Language.get(lang):
            return tesseract_lang
    return False


def start_subtitle_extraction(file_path,tesseract_path,export_Esrt,wantedLangs,mkvToolsPath,BDSup2Path):
    pytesseract.pytesser    = fr'{tesseract_path}'
    mkvToolsPath = mkvToolsPath.replace("\\","/")
    BDSup2SubPath = BDSup2Path.replace("\\","/")
    wantedSubs = wantedLangs
    exportSRT = export_Esrt
    status = None

    def OCRprocessor(supFile,srtFile,language='eng'):
        pgs = PGSReader(supFile)
        srt = SubRipFile()

        # get all DisplaySets that contain an image
        logging.info(bcolors.WARNING + "Loading DisplaySets..." + bcolors.ENDC)
        try:
            allsets = [ds for ds in tqdm(pgs.iter_displaysets())]
        except Exception as e:
            logging.error(bcolors.FAIL + "Error: Loading DisplaySets failed!, moving on" + bcolors.ENDC)
            return None

        logging.warning(bcolors.WARNING + f"Running OCR on {len(allsets)} DisplaySets and building SRT file..." + bcolors.ENDC)

        subText = ""
        subStart = 0
        subIndex = 0

        for ds in tqdm(allsets):
            if ds.has_image:
                # get Palette Display Segment
                #check if pallte is empty

                if len(ds.pds) != 0:
                    #continue
                    if len(ds.ods) != 0:
                        #continue
                        pds = ds.pds[0]
                        # get Object Display Segment
                        ods = ds.ods[0]
                        img = make_image(ods, pds,swap=False)
                        if img != None:
                            img = img.convert('L')
                            img = Image.eval(img, lambda x: 255 if x > 100 else 0)
                            img = img.convert('RGB')
                            img = Image.eval(img, lambda x: 255 if x < 128 else 0)
                            subText = pytesseract.image_to_string(img, lang=language, config='--psm 6')
                            subText = fixOCR(subText,language)
                            subStart = ods.presentation_timestamp
                        else:
                            logging.error(bcolors.FAIL + "No Object Display Segment found, skipping" + bcolors.ENDC)
                            subStart = ods.presentation_timestamp
                            subText = ' '
                else:
                    logging.warning(bcolors.FAIL + "No Palette Display Segment found, skipping" + bcolors.ENDC)
                    subIndex += 1
            else:
                startTime = SubRipTime(milliseconds=int(subStart))
                endTime = SubRipTime(milliseconds=int(ds.end[0].presentation_timestamp))
                srt.append(SubRipItem(subIndex, startTime, endTime, subText[:-1]))
                subIndex += 1
        return srt, srtFile

    def fixOCR(sub,language='eng'):
        if language == 'eng':
            logging.debug("Fixing OCR...")
            if '-' in sub.split(' ')[0]:
                sub = sub.replace('-', '')
            if 'VW' in sub.split(' ')[0]:
                sub = sub.replace('VW', 'W')
            if '|' in sub:
                sub = sub.replace('|', 'I')
            if "i'" in sub:
                sub = sub.replace("i'", "I'")
            if 'Ls' in sub.split(' ')[0]:
                sub = sub.replace('Ls', 'Is')
            if 'Lf' in sub.split(' ')[0]:
                sub = sub.replace('Lf', 'If')
            return sub
        return sub

    def extract_mkv_subs(filePath,trackID,lang,default=False,forced=False,SDH=False,type="pgs"):
        tesseract_lang = language_is_supported(lang)
        if tesseract_lang:
            if forced == True:
                replaceExtensionSup = '.' + lang + '.forced.sup'
                replaceExtensionSrt = '.' + lang + '.forced.srt'
            if SDH == True:
                replaceExtensionSup = '.' + lang + '.SDH.sup'
                replaceExtensionSrt = '.' + lang + '.SDH.srt'
            if default == True:
                replaceExtensionSup = '.' + lang + '.default.sup'
                replaceExtensionSrt = '.' + lang + '.default.srt'
            else:
                replaceExtensionSup = '.' + lang + '.sup'
                replaceExtensionSrt = '.' + lang + '.srt'
            if type == "vob":
                if forced == True:
                    replaceExtensionVOB = '.' + lang + '.forced.idx'
                else:
                    replaceExtensionVOB = '.' + lang + '.idx'
            if type == "srt":
                if forced == True:
                    replaceExtensionSUBRIP = '.' + lang + '.forced.srt'
                else:
                    replaceExtensionSUBRIP = '.' + lang + '.srt'
            if type == "ass":
                if forced == True:
                    replaceExtensionASS = '.' + lang + '.forced.ass'
                else:
                    replaceExtensionASS = '.' + lang + '.ass'
            try:
                # if replaceExtensionSrt exists, skip
                if os.path.isfile(filePath.replace('.mkv',replaceExtensionSrt)) or os.path.isfile(filePath.replace('.mkv',replaceExtensionSrt).replace(lang,lang[:-1])):
                    logging.info(bcolors.WARNING + "SRT file already exists. Skipping..." + bcolors.ENDC)
                    return None
                if type == "pgs":
                    extract_subtitle(filePath, replaceExtensionSup, trackID)
                if type == "vob":
                    extract_subtitle(filePath, replaceExtensionVOB, trackID)
                if type == "srt":
                    if exportSRT == True:
                        logging.info(bcolors.WARNING + "Starting embedded subtitles extraction..." + bcolors.ENDC)
                        extract_subtitle(filePath, replaceExtensionSUBRIP, trackID)
                        logging.info(bcolors.OKGREEN + "SRT extracted..." + bcolors.ENDC)
                        return True
                    else:
                        logging.info(bcolors.FAIL + "SRT embedded export is not wanted, skipping." + bcolors.ENDC)
                        return None
                if type == "ass":
                    logging.info(bcolors.WARNING + "Starting ASS subtitles extraction and conversion..." + bcolors.ENDC)
                    if os.path.isfile(filePath.replace('.mkv',replaceExtensionASS)) == False:
                        subprocess.call([mkvToolsPath+"mkvextract", "tracks", filePath,
                                         str(trackID) + ":" + filePath.replace(".mkv", replaceExtensionASS)])

                    try:
                        ass_file = open(filePath.replace(".mkv", replaceExtensionASS),encoding="utf8")
                        srt_str = asstosrt.convert(ass_file)
                        #save srt file
                        srt_file = open(filePath.replace(".mkv", replaceExtensionSrt), "w",encoding="utf8")
                        srt_file.write(srt_str)
                        srt_file.close()
                        #close ass file
                        ass_file.close()
                        os.remove(filePath.replace(".mkv", replaceExtensionASS))
                        logging.info(bcolors.OKGREEN + "SRT extracted..." + bcolors.ENDC)

                        return True
                    except Exception as e: # name the Exception `e`
                        logging.error("Failed with:", e) # look what it says
                        logging.error(bcolors.FAIL + "ASS Extraction/Conversion failed, skipping." + bcolors.ENDC)
                        return None
                if os.path.isfile(filePath.replace('.mkv',replaceExtensionSrt)) == False:
                    if type == "vob":
                        if os.path.isfile(filePath.replace('.mkv',replaceExtensionVOB)):
                            try:
                                subprocess.call(["java","-jar",BDSup2SubPath,"-i",'{}'.format(filePath.replace(".mkv", replaceExtensionVOB)),"-o", '{}'.format(filePath.replace(".mkv", replaceExtensionSup))])
                            except:
                                logging.error(bcolors.FAIL + "BDSup2Sub failed to convert VOBSUB to SRT, check your pathing to BDSup2Sub or restart if you just installed everything." + bcolors.ENDC)
                                return None
                        else:
                            logging.warning(bcolors.FAIL + "No VOBSUB file found. Skipping, Path may have bad characters" + bcolors.ENDC)
                            return None
                    logging.info(bcolors.WARNING + "Running OCR..." + bcolors.ENDC)
                    OCR = OCRprocessor(filePath.replace(".mkv", replaceExtensionSup),filePath.replace(".mkv", replaceExtensionSrt),tesseract_lang)
                    logging.info(bcolors.WARNING + "Converting to SRT..." + bcolors.ENDC)
                    if OCR != None:
                        srtFile = OCR[1]
                        srt =  OCR[0]
                        logging.info(bcolors.WARNING + "Saving SRT..." + bcolors.ENDC)
                        srt.save(srtFile, encoding='utf-8')
                        #delete sup file
                        logging.info(bcolors.WARNING + "Deleting SUP file..." + bcolors.ENDC)
                        if type == "vob":
                            try:
                                os.remove(filePath.replace(".mkv", replaceExtensionVOB))
                                sub = filePath.replace(".mkv", replaceExtensionVOB).replace(".idx", ".sub")
                                #os.remove(filePath.replace(".mkv", replaceExtensionVOB))
                                os.remove(sub)
                            except Exception as e:
                                logging.error(bcolors.FAIL + "Error deleting VOBSUB file: {}".format(e) + bcolors.ENDC)
                        os.remove(filePath.replace(".mkv", replaceExtensionSup))
                        logging.info(bcolors.OKGREEN + "SRT extracted!" + bcolors.ENDC)
                        return True
                    else:
                        logging.error(bcolors.FAIL + "Keeping the SUP file for later usage" + bcolors.ENDC)
                        return None
            except subprocess.CalledProcessError:
                logging.error(bcolors.FAIL + "ERROR: Could not extract subtitles" + bcolors.ENDC)
                return None
        else:
            logging.warning(bcolors.FAIL + "Language track {} not supported, Skipping".format(lang) + bcolors.ENDC)

    def extract_subtitle(filePath, extension, trackID):
        logging.info(bcolors.WARNING + "Starting embedded subtitles extraction..." + bcolors.ENDC)
        subtitle_file = filePath.replace('.mkv', extension)
        if os.path.isfile(subtitle_file) == False:
            logging.debug("Will run command: %s %s %s %s", mkvToolsPath + "mkvextract", "tracks", filePath,
                          str(trackID) + ":" + filePath.replace(".mkv", extension))
            subprocess.call([mkvToolsPath + "mkvextract", "tracks", filePath,
                             str(trackID) + ":" + filePath.replace(".mkv", extension)])
        else:
            logging.debug("File %s already exists, skipping extracting", subtitle_file)

    #@timeout(15)        
    def getProcessOutput(cmd):
        logging.debug('Will run command: %s', cmd)
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE)
        #process.wait()
        data, err = process.communicate()
        if process.returncode == 0:
            return data.decode('utf-8')
        else:
            logging.error(bcolors.FAIL + "Error: %s", err)
        return ""


    """ Returns the track ID of the SRT subtitles track"""
    cmd = mkvToolsPath + 'mkvmerge -i ' + '"{}"'.format(file_path) +' -F json'

    data = getProcessOutput(cmd)
    found = False
    if data:
        logging.debug(data)
        data = json.loads(data)
        for track in data['tracks']:
            if track['type'] == 'subtitles':
                found = True
                logging.debug(bcolors.OKGREEN + "Found subtitle track: {}".format(track['id']) + bcolors.ENDC)
                if 'pgs' in track['codec'].lower() or 'vobsub' in track['codec'].lower() or 'srt' in track['codec'].lower() or 'SubStationAlpha' in track['codec']:
                    trackID = track['id']
                    logging.debug(trackID)
                    lang = track['properties']['language']
                    logging.debug(bcolors.OKGREEN + "Language: {}".format(lang) + bcolors.ENDC)
                    if lang in wantedSubs or wantedSubs == 'all':
                        if 'track_name' in track['properties'].keys():
                            name = track['properties']['track_name']
                        else:
                            name = 'vobsub'
                        logging.debug("Keys: %s", track.keys())
                        default_track = 'default_track' in track['properties'].keys() and track['properties']['default_track']
                        forced_track = 'forced_track' in track['properties'].keys() and track['properties']['forced_track']
                        sdh = 'sdh' in name.lower()
                        if 'pgs' in track['codec'].lower():
                            logging.info(bcolors.OKGREEN + "Found {} PGS Default".format(lang.capitalize()) + bcolors.ENDC)
                            status = extract_mkv_subs(file_path,trackID,lang,default=default_track,forced=forced_track,SDH=sdh,type='pgs')
                        if 'vobsub' in track['codec'].lower():
                            logging.info(bcolors.OKGREEN + "Found {} VOBSUB Default".format(lang.capitalize()) + bcolors.ENDC)
                            status = extract_mkv_subs(file_path,trackID,lang,default=default_track,forced=forced_track,SDH=sdh,type='vob')
                        if 'srt' in track['codec'].lower():
                            logging.info(bcolors.OKGREEN + "Found {} SRT Default".format(lang.capitalize()) + bcolors.ENDC)
                            status = extract_mkv_subs(file_path,trackID,lang,default=default_track,forced=forced_track,SDH=sdh,type='srt')
                        if 'SubStationAlpha' in track['codec']:
                            logging.info(bcolors.OKGREEN + "Found {} ASS Default".format(lang.capitalize()) + bcolors.ENDC)
                            status = extract_mkv_subs(file_path,trackID,lang,default=default_track,forced=forced_track,SDH=sdh,type='ass')
                    else:
                        logging.info(bcolors.WARNING + "Skipping language {} due to preference".format(lang.capitalize()) + bcolors.ENDC)
                else:
                    logging.error(bcolors.FAIL + "Unsupported subtitle format, skipping" + bcolors.ENDC)
                    continue
    if found == False:
        logging.error(bcolors.FAIL + "No Subtitle tracks" + bcolors.ENDC)
    return status
            

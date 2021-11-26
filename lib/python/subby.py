#!/usr/bin/env python3

from logging import exception
import os
import subprocess
import json
import pytesseract
from .pgsreader import PGSReader
from .imagemaker import make_image
from PIL import Image
from pysrt import SubRipFile, SubRipItem, SubRipTime
from tqdm import tqdm
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

def start_subtitle_extraction(file_path,tesseract_path,export_Esrt,wantedLangs,mkvToolsPath,BDSup2Path):
    pytesseract.pytesseract.tesseract_cmd = fr'{tesseract_path}'
    mkvToolsPath = mkvToolsPath.replace("\\","/")
    BDSup2SubPath = BDSup2Path.replace("\\","/")
    wantedSubs = wantedLangs
    exportSRT = export_Esrt
    status = None
    
    def OCRprocessor(supFile,srtFile,language='eng'):
        pgs = PGSReader(supFile)
        srt = SubRipFile()
        
        # get all DisplaySets that contain an image
        print(bcolors.WARNING + "    Loading DisplaySets..." + bcolors.ENDC)
        try:
            allsets = [ds for ds in tqdm(pgs.iter_displaysets())]
        except Exception as e:
            print(bcolors.FAIL + "    Error: Loading DisplaySets failed!, moving on" + bcolors.ENDC)
            return None
        
        print(bcolors.WARNING + f"    Running OCR on {len(allsets)} DisplaySets and building SRT file..." + bcolors.ENDC)

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
                            print(bcolors.FAIL + "    No Object Display Segment found, skipping" + bcolors.ENDC)
                            subStart = ods.presentation_timestamp
                            subText = ' '
                else:
                    print(bcolors.FAIL + "    No Palette Display Segment found, skipping" + bcolors.ENDC)
                    subIndex += 1
            else:
                startTime = SubRipTime(milliseconds=int(subStart))
                endTime = SubRipTime(milliseconds=int(ds.end[0].presentation_timestamp))
                srt.append(SubRipItem(subIndex, startTime, endTime, subText[:-1]))
                subIndex += 1
        return srt, srtFile

    def fixOCR(sub,language='eng'):
        if language == 'eng':
            #print("    Fixing OCR...")
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
        if lang in pytesseract.get_languages(config=''):
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
                    print(bcolors.WARNING + "    SRT file already exists. Skipping..." + bcolors.ENDC)
                    return None
                if type == "pgs":
                    print(bcolors.WARNING+"    Starting embedded subtitles extraction..." + bcolors.ENDC)
                    if os.path.isfile(filePath.replace('.mkv',replaceExtensionSup)) == False:
                        subprocess.call([mkvToolsPath+"mkvextract", "tracks", filePath,
                                        str(trackID) + ":" + filePath.replace(".mkv", replaceExtensionSup)])
                if type == "vob":
                    print(bcolors.WARNING + "    Starting embedded subtitles extraction..." + bcolors.ENDC)
                    if os.path.isfile(filePath.replace('.mkv',replaceExtensionVOB)) == False:
                        subprocess.call([mkvToolsPath+"mkvextract", "tracks", filePath,
                                        str(trackID) + ":" + filePath.replace(".mkv", replaceExtensionVOB)])
                if type == "srt":
                    
                    if exportSRT == True:
                        print(bcolors.WARNING + "    Starting embedded subtitles extraction..." + bcolors.ENDC)
                        if os.path.isfile(filePath.replace('.mkv',replaceExtensionSUBRIP)) == False:
                            subprocess.call([mkvToolsPath+"mkvextract", "tracks", filePath,
                                            str(trackID) + ":" + filePath.replace(".mkv", replaceExtensionSUBRIP)])
                            print(bcolors.OKGREEN + "    SRT extracted..." + bcolors.ENDC)
                            return True
                    else:
                        print(bcolors.FAIL + "    SRT embedded export is not wanted, skipping." + bcolors.ENDC)
                        return None
                if type == "ass":
                    print(bcolors.WARNING + "    Starting ASS subtitles extraction and conversion..." + bcolors.ENDC)
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
                        print(bcolors.OKGREEN + "    SRT extracted..." + bcolors.ENDC)
                        
                        return True
                    except Exception as e: # name the Exception `e`
                        print ("Failed with:", e) # look what it says
                        print(bcolors.FAIL + "    ASS Extraction/Conversion failed, skipping." + bcolors.ENDC)
                        return None                     
                if os.path.isfile(filePath.replace('.mkv',replaceExtensionSrt)) == False:
                    if type == "vob":
                        if os.path.isfile(filePath.replace('.mkv',replaceExtensionVOB)):
                            try:
                                subprocess.call(["java","-jar",BDSup2SubPath,"-i",'{}'.format(filePath.replace(".mkv", replaceExtensionVOB)),"-o", '{}'.format(filePath.replace(".mkv", replaceExtensionSup))])
                            except:
                                print(bcolors.FAIL + "    BDSup2Sub failed to convert VOBSUB to SRT, check your pathing to BDSup2Sub or restart if you just installed everything." + bcolors.ENDC)
                                return None
                        else:
                            print(bcolors.FAIL + "    No VOBSUB file found. Skipping, Path may have bad characters" + bcolors.ENDC)
                            return None
                    print(bcolors.WARNING + "    Running OCR..." + bcolors.ENDC)
                    OCR = OCRprocessor(filePath.replace(".mkv", replaceExtensionSup),filePath.replace(".mkv", replaceExtensionSrt),lang)
                    print(bcolors.WARNING + "    Converting to SRT..." + bcolors.ENDC)
                    if OCR != None:
                        srtFile = OCR[1]
                        srt =  OCR[0]
                        print(bcolors.WARNING + "    Saving SRT..." + bcolors.ENDC)
                        srt.save(srtFile, encoding='utf-8')
                        #delete sup file
                        print(bcolors.WARNING + "    Deleting SUP file..." + bcolors.ENDC)
                        if type == "vob":
                            try:
                                os.remove(filePath.replace(".mkv", replaceExtensionVOB))
                                sub = filePath.replace(".mkv", replaceExtensionVOB).replace(".idx", ".sub")
                                #os.remove(filePath.replace(".mkv", replaceExtensionVOB))
                                os.remove(sub)
                            except Exception as e:
                                print(bcolors.FAIL + "    Error deleting VOBSUB file: {}".format(e) + bcolors.ENDC)   
                        os.remove(filePath.replace(".mkv", replaceExtensionSup))
                        print(bcolors.OKGREEN + "    SRT extracted!" + bcolors.ENDC)
                        return True
                    else:
                        print(bcolors.FAIL + "    Keeping the SUP file for later usage" + bcolors.ENDC)
                        return None
            except subprocess.CalledProcessError:
                print(bcolors.FAIL + "    ERROR: Could not extract subtitles" + bcolors.ENDC)
                return None
        else:
            print (bcolors.FAIL + "Language track {} not supported, Skipping".format(lang) + bcolors.ENDC)
    
    #@timeout(15)        
    def getProcessOutput(cmd):
        #print(cmd)
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE)
        #process.wait()
        data, err = process.communicate()
        if process.returncode == 0:
            return data.decode('utf-8')
        else:
            print(bcolors.FAIL + "Error:", err + bcolors.ENDC)
        return ""


    """ Returns the track ID of the SRT subtitles track"""
    cmd = mkvToolsPath + 'mkvmerge -i ' + '"{}"'.format(file_path) +' -F json'
    
    data = getProcessOutput(cmd)
    if data:
        #print(data)
        found = False
        data = json.loads(data)
        for track in data['tracks']:
            
            if track['type'] == 'subtitles':
                found = True
                if 'pgs' in track['codec'].lower() or 'vobsub' in track['codec'].lower() or 'srt' in track['codec'].lower() or 'SubStationAlpha' in track['codec']:
                    trackID = track['id']
                    #print(trackID)
                    lang = track['properties']['language']
                    if lang in wantedSubs or wantedSubs == 'all':
                        if 'track_name' in track['properties'].keys():
                            name = track['properties']['track_name']
                        else:
                            name = 'vobsub'
                        #print(track.keys())
                        if 'default_track' in track['properties'].keys():
                            if track['properties']['default_track'] == True and 'forced' not in name.lower() and track['properties']['forced_track'] == False:
                                if 'pgs' in track['codec'].lower():
                                    print(bcolors.OKGREEN + "    Found {} PGS Default".format(lang.capitalize()) + bcolors.ENDC)
                                    status = extract_mkv_subs(file_path,trackID,lang,default=True,forced=False,SDH=False,type='pgs')
                                if 'vobsub' in track['codec'].lower():
                                    print(bcolors.OKGREEN + "    Found {} VOBSUB Default".format(lang.capitalize()) + bcolors.ENDC)
                                    status = extract_mkv_subs(file_path,trackID,lang,default=True,forced=False,SDH=False,type='vob')
                                if 'srt' in track['codec'].lower():
                                    print(bcolors.OKGREEN + "    Found {} SRT Default".format(lang.capitalize()) + bcolors.ENDC)
                                    status = extract_mkv_subs(file_path,trackID,lang,default=True,forced=False,SDH=False,type='srt')
                                if 'SubStationAlpha' in track['codec']:
                                    print(bcolors.OKGREEN + "    Found {} ASS Default".format(lang.capitalize()) + bcolors.ENDC)
                                    status = extract_mkv_subs(file_path,trackID,lang,default=True,forced=False,SDH=False,type='ass')
                        elif 'forced' in name.lower() and track['properties']['default_track'] == False:
                            if 'pgs' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} PGS Forced".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=True,SDH=False,type='pgs')
                            if 'vobsub' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} VOBSUB Forced".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=True,SDH=False,type='vob')
                            if 'srt' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} SRT Forced".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=True,SDH=False,type='srt')
                            if 'SubStationAlpha' in track['codec']:
                                print(bcolors.OKGREEN + "    Found {} ASS Forced".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=True,SDH=False,type='ass')
                        elif 'sdh' in name.lower() and track['properties']['default_track'] == False:
                            if 'pgs' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {}(SDH) PGS ".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=True,type='pgs')
                            if 'vobsub' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {}(SDH) VOBSUB".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=True,type='vob')
                            if 'srt' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {}(SDH) SRT".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=True,type='srt')
                            if 'SubStationAlpha' in track['codec']:
                                print(bcolors.OKGREEN + "    Found {} ASS".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=True,type='ass')
                        else:
                            if 'pgs' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} PGS".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=False,type='pgs')
                            if 'vobsub' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} VOBSUB".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=False,type='vob')
                            if 'srt' in track['codec'].lower():
                                print(bcolors.OKGREEN + "    Found {} SRT".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=False,type='srt')
                            if 'SubStationAlpha' in track['codec']:
                                print(bcolors.OKGREEN + "    Found {} ASS".format(lang.capitalize()) + bcolors.ENDC)
                                status = extract_mkv_subs(file_path,trackID,lang,default=False,forced=False,SDH=False,type='ass')
                    else:
                        print(bcolors.WARNING + "    Skipping language {} due to preference".format(lang.capitalize()) + bcolors.ENDC)  
                else:
                    print(bcolors.FAIL + "    Unsupported subtitle format, skipping" + bcolors.ENDC)
                    continue
    if found == False:        
        print(bcolors.FAIL + "    No Subtitle tracks" + bcolors.ENDC)
    return status
            

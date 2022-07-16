import os
import sys
import configparser
import time
from lib.python.subby import start_subtitle_extraction
from lib.python.plexScanner import startScan
from lib.python.plexScanner import getPlexSectionID
import subprocess
import logging
from logging import config

log_config = {
    "version":1,
    "root":{
        "handlers" : ["console"],
        "level": "INFO"
    },
    "handlers":{
        "console":{
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "INFO"
        }
    },
    "formatters":{
        "std_out": {
            "format": "%(asctime)s : %(levelname)s : %(module)s : %(funcName)s : %(lineno)d : (Process Details : (%(process)d, %(processName)s), Thread Details : (%(thread)d, %(threadName)s))\nLog : %(message)s",
            "datefmt":"%d-%m-%Y %I:%M:%S"
        }
    },
}

config.dictConfig(log_config)
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

class Main:
    
    def __init__(self):
        self.logo = '''
         ___ _   _ ___ _____   __    __  
        / __| | | | _ ) _ ) \ / /  __ \ \ 
        \__ \ |_| | _ \ _ \\ V /   |___| |
        |___/\___/|___/___/ |_|   |___| |
                                     /_/ 
        '''
        #check if the config file exists
        self.script_path = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile(self.script_path + '/config.ini'):
            #load the config file
            config = configparser.ConfigParser()
            config.read(self.script_path + '/config.ini')

            #--- SETUP ---
            logging.debug(bcolors.FAIL + "Loading Configs" + bcolors.ENDC)

            #plex variables
            self.plex_host = config['plex']['serverAddress']
            self.plex_token = config['plex']['serverToken']
            self.plex_port = config['plex']['serverPort']
            self.plex_libraries = config['plex']['serverLibaries'].split(',')
            self.only4k = self.str_to_bool(config['subby']['only4K'].capitalize())

            #making sure no unwanted spaces are in the libraries
            for lib in self.plex_libraries:
                index = self.plex_libraries.index(lib)
                if ' ' in lib[0]:
                    lib = self.plex_libraries[index] = lib[1:]
                if ' ' in lib[-1]:
                    self.plex_libraries[index] = lib[:-1]
            self.plex_media_path = config['plex']['plexPath']
            self.plex_local_path = config['plex']['localPath']

            #determine if the plex media path is on linux or windows
            if self.plex_media_path != "":
                #check which os seperator is used
                if '/' in self.plex_media_path:
                    self.plex_sep = 'lnx'
                else:
                    self.plex_sep = 'win'
            
            self.plex_notify = self.str_to_bool(config['plex']['notifyPlex'].capitalize())
            logging.info(bcolors.OKGREEN + 'Plex config loaded!' + bcolors.ENDC)

            #subby variables
            self.tesseract_path = config['subby']['pathToTesseractEXE']
            self.export_srt = self.str_to_bool(config['subby']['exportEmbeddedSRTs'].capitalize())

            logging.debug(bcolors.OKGREEN + 'Subby config loaded!' + bcolors.ENDC)

            #get wanted languages
            self.wanted_languages = config['subby']['wantedLanguages']
            if self.wanted_languages == '':
                self.wanted_languages = 'all'
            elif ',' in self.wanted_languages:
                self.wanted_languages = self.wanted_languages.split(',')
                for lang in self.wanted_languages:
                    index = self.wanted_languages.index(lang)
                    if ' ' in lang[0]:
                        lang = self.wanted_languages[index] = lang[1:]
                    if ' ' in lang[-1]:
                        self.wanted_languages[index] = lang[:-1]
            
            #set local bin paths
            if os.name == 'nt':
                self.mkvToolsPath = self.script_path + '/lib/bin/mkvtools/'
            else:
                logging.info("Linux system, make sure to install mkvtoolnix and bins are in /usr/bin/")
                self.mkvToolsPath = '/usr/bin/'

            #set local java paths
            self.BDSup2SubPath = self.script_path + '/lib/java/BDSup2Sub.jar'

            #-- END SETUP --

            #check the command line arguments
            print(self.logo)
            if len(sys.argv) > 1:
                if '-v' in sys.argv or '--verbose' in sys.argv:
                    self.set_debug_level()
                if sys.argv[1] == '--plex':
                    logging.debug(bcolors.WARNING + 'Scanning Plex for items with subtitles, please wait.' + bcolors.ENDC)
                    for library in self.plex_libraries:
                        if self.plex_notify == True:
                            collectExtracts = []
                        print( bcolors.WARNING +' Scanning library: ' + library + ', Please wait :D' + bcolors.ENDC)
                        self.sectionID = getPlexSectionID(self.plex_host, self.plex_port, self.plex_token, library)
                        print(bcolors.OKGREEN + ' Library ID: ' + self.sectionID + bcolors.ENDC)
                        items = self.plex_scan(library=library)
                        if items != None:
                            print(bcolors.WARNING + '    Plex scan complete for {}, Processing {} items, estimated time for completeion is {} hours'.format(library,len(items), len(items) * 5 / 60 * 0.75) + bcolors.ENDC)
                            if len(items) > 0:
                                for item in items:
                                    print(bcolors.WARNING + '    Processing {}'.format(item) + bcolors.ENDC)
                                    #print(os.path.dirname(item))
                                    extract = start_subtitle_extraction(item,self.tesseract_path, self.export_srt, self.wanted_languages, self.mkvToolsPath, self.BDSup2SubPath)
                                    if extract != None:
                                        if self.plex_notify == True:
                                            file = os.path.dirname(item.replace(self.plex_local_path,self.plex_media_path))
                                            if self.plex_sep == 'win':
                                                file = file.replace('/','\\')
                                            else:
                                                file = file.replace('\\','/')
                                            collectExtracts.append(file)
                                            #self.notify_plex(item.replace(self.plex_local_path,self.plex_media_path))
                        if len(collectExtracts) > 0:
                            #time.sleep(10)
                            collectExtracts = list(set(collectExtracts))
                            for i in collectExtracts:
                                time.sleep(3)
                                self.notify_plex(i)
                        else:
                            logging.info(bcolors.OKGREEN + 'No extractions made' + bcolors.ENDC)
                else:
                    start_subtitle_extraction(sys.argv[1],self.tesseract_path, self.export_srt, self.wanted_languages, self.mkvToolsPath, self.BDSup2SubPath)
            else:
                logging.info(bcolors.WARNING + 'No arguments given, use --plex to toggle plex scan or give a path to a file to process, ex: "D:/blahblah.mkv"' + bcolors.ENDC)

    def set_debug_level(self):
        level = logging.DEBUG
        logger = logging.getLogger()
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)

    def notify_plex(self,plexFilePath):
        
        curlUrl = 'http://{}/library/sections/{}/refresh?path={}&X-Plex-Token={}'.format(self.plex_host+':'+self.plex_port,self.sectionID,plexFilePath,self.plex_token).replace(' ','%20')
        cmd = "curl \"{}""\"".format(curlUrl)
        logging.info(bcolors.WARNING + 'Notifying Plex of changes, curl command is: {}'.format(cmd) + bcolors.ENDC)
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE)
        #process.wait()
        data, err = process.communicate()
        if process.returncode == 0:
            return data.decode('utf-8')
        else:
            logging.error("Error:", err)
            return ""

    def plex_scan(self,library):
        scan = startScan(self.plex_host, self.plex_port, self.plex_token, self.plex_media_path, self.plex_local_path,self.only4k, library)
        return scan
    
    def str_to_bool(self,s):
        if s == 'True':
            return True
        elif s == 'False':
            return False
    
main = Main()
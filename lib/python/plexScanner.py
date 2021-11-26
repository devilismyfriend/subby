import os
#if plexapi doesn't exist, install it
try:
    from plexapi.server import PlexServer
except ImportError:
    print('plexapi is not installed, installing now, if this is failling, install PlexAPI into pip')
    import pip
    pip.main(['install', 'PlexAPI'])
    from plexapi.server import PlexServer
import sys
from tqdm import tqdm
#function to connect to plex api
def connect_to_plex(server_name,port, token):
    plex = PlexServer('http://' + server_name + ':{}'.format(port), token)
    return plex

#function to find content with highest bitrate and delete the rest
def find_content(server, section, plexPath, localPath,only4K):
    collection = []
    #get all media files in section
    if only4K == False:
        allMedia = server.library.section(section).all()
        #print(allMedia)
    else:
        allMedia = server.library.section(section).search(resolution='4k')
        #print(allMedia)
    for item in tqdm(range(len(allMedia))):
        #print(allMedia[item])
        #
        item = allMedia[item-1]
        
        #check if item is a movie
        if item.type == 'movie':
            #reload movie metadata to get subtitle streams
            item.reload()
            for media in item.media:
                #check if media is 4k
                
                for part in media.parts:
                    #check if part has subtitles
                    if len(part.subtitleStreams()) > 0:
                        #print('Found subtitles on ' + item.title)
                        #print(media.parts[0].file.replace(plexPath,localPath))
                        #check if file exists
                        lower = [str(x).lower() for x in part.subtitleStreams()]
                        if 'srt' not in lower or 'subrip' not in lower:
                            if os.path.isfile(media.parts[0].file.replace(plexPath,localPath)):
                                #print('Found subtitle file on ' + item.title)
                                collection.append(media.parts[0].file.replace(plexPath,localPath))
                            else:
                                #print('Could not find file, make sure you used the correct local path or media path, or clean plex database')
                                #print(media.parts[0].file.replace(plexPath,localPath))
                                continue
        #check if item is a show
        if item.type == 'show':
            for episode in item.episodes():
                #reload episode metadata to get subtitle streams
                episode.reload()
                for media in episode.media:
                    for part in media.parts:
                        #check if part has subtitles
                        lower = [str(x).lower() for x in part.subtitleStreams()]
                        if 'srt' not in lower or 'subrip' not in lower:
                            if len(part.subtitleStreams()) > 0:
                                print('Found subtitles on ' + item.title + ' : ' + str(episode.seasonNumber) + 'x' + str(episode.index))
                                if os.path.isfile(media.parts[0].file.replace(plexPath,localPath)):
                                    collection.append(media.parts[0].file.replace(plexPath,localPath))
                                else:
                                    print('Could not find file, make sure you used the correct local path or media path, or clean plex database')
                                    continue
    return collection              

def startScan(serverIP,port, serverToken,plexPath,localPath,only4K,library):
    #print(plexPath)
    #print(localPath)
    #connect to plex server
    try:
        plex = connect_to_plex(serverIP,port, serverToken)
    except Exception as e:
        #print os error if connection fails
        print('Could not connect to plex server, check your config')
        print(e)
        return None
    #get all media files in section if item has subtitles
    try:
        content = find_content(plex,library,plexPath,localPath,only4K)
    except Exception as e:
        print(e)
        print('Could not find content, check that your libraries are named correctly in the config')
        return None
    #return file paths
    return content

def getPlexSectionID(serverIP,port, serverToken,libraryName):
    #get plex section id
    try:
        plex = connect_to_plex(serverIP,port, serverToken)
    except Exception as e:
        #print os error if connection fails
        print('Could not connect to plex server, check your config')
        print(e)
        return None
    #get library id
    try:
        library = plex.library.section(libraryName)
        #print(library)
        return str(library.key)
    except Exception as e:
        print('Could not find library, check that your libraries are named correctly in the config')
        print(e)
        return None

# -*- coding: utf-8 -*-
import json
import xbmc
import xbmcaddon
import xbmcvfs
import sys
from base64 import b64encode
from resources.lib.comaddon import dialog, addon, addonManager, VSlog, isMatrix
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.util import QuotePlus


class UpNext:
    
    
    # Prépare le lien du prochain épisode d'une série
    def nextEpisode(self, guiElement):
        
        if not self.use_up_next():
            return
        
        # tester s'il s'agit d'une série 
        tvShowTitle = guiElement.getItemValue('tvshowtitle')
        if not tvShowTitle:
            return      

        oInputParameterHandler = cInputParameterHandler()
        nextEpisodeFunc = oInputParameterHandler.getValue('nextEpisodeFunc')
 

        sSiteName = oInputParameterHandler.getValue('sourceID')
        if not sSiteName:
            return 

        sSeason = str(guiElement.getSeason())
        if not sSeason:
            return

        sEpisode = str(guiElement.getEpisode())
        if not sEpisode:
            return
        
        numEpisode = int(sEpisode)
        sNextEpisode = '%02d' % (numEpisode+1)

        SeasonUrl = oInputParameterHandler.getValue('SeasonUrl')
        nextSeasonFunc = oInputParameterHandler.getValue('nextSeasonFunc')
        sHosterIdentifier = oInputParameterHandler.getValue('sHosterIdentifier')

        sUrl = self.getEpisodeFromSeason(tvShowTitle, sSeason, sNextEpisode, oInputParameterHandler)
        if not sUrl:
            return 

        

        nextTitle = tvShowTitle.replace(' & ', ' and ')   # interdit dans un titre
        nextTitle += ' - ' + 'S%sE%s' %(sSeason, sNextEpisode)
        
        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('sMovieTitle', nextTitle)
        oOutputParameterHandler.addParameter('sTitle', nextTitle)
        oOutputParameterHandler.addParameter('sCat', 8) # épisode
        oOutputParameterHandler.addParameter('sEpisode', sNextEpisode)
        oOutputParameterHandler.addParameter('siteUrl', sUrl)
        oOutputParameterHandler.addParameter('sId', sSiteName)
        oOutputParameterHandler.addParameter('sourceID', sSiteName)
        oOutputParameterHandler.addParameter('SeasonUrl', SeasonUrl)
        oOutputParameterHandler.addParameter('nextSeasonFunc', nextSeasonFunc)
        oOutputParameterHandler.addParameter('sHosterIdentifier', sHosterIdentifier)
        
        if nextEpisodeFunc:
            try:
                sParams = oOutputParameterHandler.getParameterAsUri()
                sys.argv[2] = '?site=%s&function=%s&title=%s&%s' % (sSiteName, nextEpisodeFunc, nextTitle, sParams)
                plugins = __import__('resources.sites.%s' % sSiteName, fromlist=[sSiteName])
                function = getattr(plugins, nextEpisodeFunc)
                function()

            except Exception as e:
                VSlog('upnext - could not load site: ' + sSiteName + ' error: ' + str(e))
                return
				
        nextLinkFunc = oInputParameterHandler.getValue('nextLinkFunc')
        if nextLinkFunc:
            links = cGui().getEpisodeListing()
            if links[0]:
                sUrl = links[0][0]
                try:
                    siteUrl, sParams = sUrl.split('&', 1)
                    sys.argv[2] = '?site=%s&%s' % (sSiteName, sParams)
                    plugins = __import__('resources.sites.%s' % sSiteName, fromlist=[sSiteName])
                    function = getattr(plugins, nextLinkFunc)
                    function()

                except Exception as e:
                    VSlog('upnext - could not load site: ' + sSiteName + ' error: ' + str(e))
                    return
               
        try:
            sMediaUrl = ''
            for sUrl, listItem, _ in cGui().getEpisodeListing():
                siteUrl, params = sUrl.split('&', 1)
                aParams = dict(param.split('=') for param in params.split('&'))

                if not 'sMediaUrl' in aParams:
                    continue

                sMediaUrl = aParams['sMediaUrl']

                if sHosterIdentifier:
                    if 'sHosterIdentifier' not in aParams:
                        continue
                    sHosterID = aParams['sHosterIdentifier']
                    if sHosterID != sHosterIdentifier:
                        continue
							
                if 'sSeason' in aParams:
                    season = aParams['sSeason']
                    if season != sSeason:
                        continue           # La saison est connue mais ce n'est pas la bonne 

                if 'sEpisode' in aParams:
                    episode = aParams['sEpisode']
                    if episode != sNextEpisode:
                        continue           # L'épisode est connue mais ce n'est pas le bon
                    
                break

            if not sMediaUrl:
                return

            oOutputParameterHandler.addParameter('sFav', 'play')
            oOutputParameterHandler.addParameter('sMediaUrl', str(sMediaUrl))
            oOutputParameterHandler.addParameter('nextEpisodeFunc', nextEpisodeFunc)
            oOutputParameterHandler.addParameter('nextLinkFunc', nextLinkFunc)
            
            
            sParams = oOutputParameterHandler.getParameterAsUri()
            url = 'plugin://plugin.video.matrix/?site=cHosterGui&function=play&%s' % sParams
            
            sThumbnail = guiElement.getThumbnail()
            
            nextInfo = dict(
                current_episode=dict(
                    episodeid=numEpisode,
                    tvshowid=0,
                    showtitle=tvShowTitle,
                    title=tvShowTitle,
                    art={
                        'thumb': sThumbnail,
                        'tvshow.clearart': '',
                        'tvshow.clearlogo': '',
                        'tvshow.fanart': guiElement.getFanart(),
                        'tvshow.landscape': '',
                        'tvshow.poster': guiElement.getPoster(),
                    },
                    season=sSeason,
                    episode= '%02d' % numEpisode,
                    plot='',
                ),
                next_episode=dict(
                    episodeid=numEpisode+1,
                    tvshowid=0,
                    showtitle=tvShowTitle,
                    title=nextTitle,
                    art={
                        'thumb': sThumbnail,
                        'tvshow.clearart': '',
                        'tvshow.clearlogo': '',
                        'tvshow.fanart': guiElement.getFanart(),
                        'tvshow.landscape': '',
                        'tvshow.poster': guiElement.getPoster(),
                    },
                    season=sSeason,
                    episode= sNextEpisode,
                    plot='',
                ),
                play_url=url    # provide either `play_info` or `play_url`
            )
 
            self.notifyUpnext(nextInfo)
        except Exception as e:
            VSlog('UpNext : %s' % e)
         
    # Retrouve le prochain épisode d'une série depuis l'url de la Season
    def getEpisodeFromSeason(self, sSeasonTitle, sSeason, sNextEpisode, oInputParameterHandler):

        sSiteName = oInputParameterHandler.getValue('sourceID')
        nextSeasonFunc = oInputParameterHandler.getValue('nextSeasonFunc')
        SeasonUrl = oInputParameterHandler.getValue('SeasonUrl')
        sHosterIdentifier = oInputParameterHandler.getValue('sHosterIdentifier')

        oOutputParameterHandler = cOutputParameterHandler()
        oOutputParameterHandler.addParameter('siteUrl', SeasonUrl)
        oOutputParameterHandler.addParameter('sId', sSiteName)
        oOutputParameterHandler.addParameter('sMovieTitle', sSeasonTitle)
        oOutputParameterHandler.addParameter('sHosterIdentifier', sHosterIdentifier)

        try:
            sParams = oOutputParameterHandler.getParameterAsUri()
            sys.argv[2] = '?site=%s&function=%s&%s' % (sSiteName, nextSeasonFunc, sParams)
            plugins = __import__('resources.sites.%s' % sSiteName, fromlist=[sSiteName])
            function = getattr(plugins, nextSeasonFunc)
            function()
            
        except Exception as e:
            VSlog('could not load site: ' + sSiteName + ' error: ' + str(e))
            return None

        for sUrl, listItem, _ in cGui().getEpisodeListing():
            siteUrl, params = sUrl.split('&', 1)
            aParams = dict(param.split('=') for param in params.split('&'))
            if 'sSeason' in aParams:
                season = aParams['sSeason']
                if season != sSeason:   # La Season est connue mais ce n'est pas la bonne 
                    continue
            if 'sEpisode' in aParams:
                episode = aParams['sEpisode']
                if episode==sNextEpisode:
                    siteUrl = aParams['siteUrl']
                    nextEpisodeURL = aParams['nextEpisode'] if 'nextEpisode' in aParams else None
                    return siteUrl

        return None

    # Envoi des info à l'addon UpNext
    def notifyUpnext(self, data):
        
        try:
            next_data = json.dumps(data)
            # if not isinstance(next_data, bytes):
            next_data = next_data.encode('utf-8')
            data = b64encode(next_data)
            if isMatrix():
                data = data.decode('ascii')
        
            jsonrpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "JSONRPC.NotifyAll",
                "params": {
                    "sender": "%s.SIGNAL" % 'plugin.video.matrix',
                    "message": 'upnext_data',
                    "data": [data],
                }
            }
        
            request = json.dumps(jsonrpc_request)
            response = xbmc.executeJSONRPC(request)
            response = json.loads(response)
            return response['result'] == 'OK'

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False


    # Charge l'addon UpNext, ou l'installe à la demande
    def use_up_next(self):
        
        addons = addon()
        if addons.getSetting('upnext') == 'false':
            return False
        
        upnext_id = 'service.upnext'
        try:
            # tente de charger UpNext pour tester sa présence
            xbmcaddon.Addon(upnext_id)
            return True
        except RuntimeError:    # Addon non installé ou désactivé
            if not dialog().VSyesno(addons.VSlang(30505)): # Voulez-vous l'activer ?
                addons.setSetting('upnext', 'false')
                return False

            addon_xml = xbmc.translatePath('special://home/addons/%s/addon.xml' % upnext_id)
            if xbmcvfs.exists(addon_xml):  # si addon.xml existe, add-on présent mais désactivé

                # Impossible d'activer UpNext ou si on confirme de ne pas vouloir l'utiliser
                if not addonManager().enableAddon(upnext_id):
                    addons.setSetting('upnext', 'false')
                    return False

                return True # addon activé
            else:                          # UpNext non installé, on l'installe et on l'utilise
                addonManager().installAddon(upnext_id)
                # ce n'est pas pris en compte à l'installation de l'addon, donc return False, il faudra attendre le prochain épisode
                return False    
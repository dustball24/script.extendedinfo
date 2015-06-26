# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui
from Utils import *
from TheMovieDB import *
from YouTube import *
from omdb import *
from ImageTools import *
import threading
from BaseClasses import DialogBaseInfo
from WindowManager import wm
from OnClickHandler import OnClickHandler

ch = OnClickHandler()

class DialogVideoInfo(DialogBaseInfo):

    @busy_dialog
    def __init__(self, *args, **kwargs):
        super(DialogVideoInfo, self).__init__(*args, **kwargs)
        if not ADDON.getSetting("first_start_infodialog"):
            ADDON.setSetting("first_start_infodialog", "True")
            xbmcgui.Dialog().ok(heading=ADDON_NAME,
                                line1=ADDON.getLocalizedString(32140),
                                line2=ADDON.getLocalizedString(32141))
        # self.ch = OnClickHandler()
        self.tmdb_id = kwargs.get('id')
        imdb_id = kwargs.get('imdb_id')
        self.name = kwargs.get('name')
        if not self.tmdb_id:
            self.tmdb_id = get_movie_tmdb_id(imdb_id=imdb_id,
                                             dbid=self.dbid,
                                             name=self.name)
        if not self.tmdb_id:
            notify(ADDON.getLocalizedString(32143))
            return None
        data = extended_movie_info(movie_id=self.tmdb_id,
                                   dbid=self.dbid)
        if data:
            self.info, self.data = data
        else:
            notify(ADDON.getLocalizedString(32143))
            return None
        log("Blur image %s with radius %i" % (self.info["thumb"], 25))
        youtube_thread = GetYoutubeVidsThread(search_str="%s %s, movie" % (self.info["Label"], self.info["year"]),
                                              hd="",
                                              order="relevance",
                                              limit=15)
        sets_thread = SetItemsThread(self.info["SetId"])
        self.omdb_thread = FunctionThread(get_omdb_movie_info, self.info["imdb_id"])
        lists_thread = FunctionThread(self.sort_lists, self.data["lists"])
        self.omdb_thread.start()
        sets_thread.start()
        youtube_thread.start()
        lists_thread.start()
        vid_id_list = [item["key"] for item in self.data["videos"]]
        crew_list = merge_dict_lists(self.data["crew"])
        if "dbid" not in self.info:
            self.info['Poster'] = get_file(self.info["Poster"])
        filter_thread = FilterImageThread(self.info["thumb"], 25)
        filter_thread.start()
        lists_thread.join()
        self.data["lists"] = lists_thread.listitems
        cert_list = get_certification_list("movie")
        for item in self.data["releases"]:
            if item["iso_3166_1"] in cert_list:
                language = item["iso_3166_1"]
                certification = item["certification"]
                language_certs = cert_list[language]
                hit = dictfind(language_certs, "certification", certification)
                if hit:
                    item["meaning"] = hit["meaning"]
        sets_thread.join()
        self.set_listitems = sets_thread.listitems
        self.setinfo = sets_thread.setinfo
        id_list = sets_thread.id_list
        self.data["similar"] = [item for item in self.data["similar"] if item["id"] not in id_list]
        youtube_thread.join()
        youtube_vids = [item for item in youtube_thread.listitems if item["youtube_id"] not in vid_id_list]
        filter_thread.join()
        self.info['ImageFilter'] = filter_thread.image
        self.info['ImageColor'] = filter_thread.imagecolor
        self.listitems = [(1000, create_listitems(self.data["actors"], 0)),
                          (150, create_listitems(self.data["similar"], 0)),
                          (250, create_listitems(self.set_listitems, 0)),
                          (450, create_listitems(self.data["lists"], 0)),
                          (550, create_listitems(self.data["studios"], 0)),
                          (650, create_listitems(self.data["releases"], 0)),
                          (750, create_listitems(crew_list, 0)),
                          (850, create_listitems(self.data["genres"], 0)),
                          (950, create_listitems(self.data["keywords"], 0)),
                          (1050, create_listitems(self.data["reviews"], 0)),
                          (1150, create_listitems(self.data["videos"], 0)),
                          (1250, create_listitems(self.data["images"], 0)),
                          (1350, create_listitems(self.data["backdrops"], 0)),
                          (350, create_listitems(youtube_vids, 0))]

    def onInit(self):
        super(DialogVideoInfo, self).onInit()
        HOME.setProperty("movie.ImageColor", self.info["ImageColor"])
        self.window.setProperty("type", "Movie")
        pass_dict_to_skin(data=self.info,
                          prefix="movie.",
                          window_id=self.window_id)
        self.fill_lists()
        pass_dict_to_skin(data=self.setinfo,
                          prefix="movie.set.",
                          window_id=self.window_id)
        self.update_states(False)
        self.join_omdb = JoinOmdbThread(self.omdb_thread, self.window_id)
        self.join_omdb.start()

    def onAction(self, action):
        super(DialogVideoInfo, self).onAction(action)

    @ch.click(1000)
    @ch.click(750)
    def open_actor_info(self):
        wm.open_actor_info(prev_window=self,
                           actor_id=self.control.getSelectedItem().getProperty("id"))

    @ch.click(150)
    @ch.click(250)
    def open_movie_info(self):
        wm.open_movie_info(prev_window=self,
                           movie_id=self.control.getSelectedItem().getProperty("id"),
                           dbid=self.control.getSelectedItem().getProperty("dbid"))

    @ch.click(1250)
    @ch.click(1350)
    def open_image(self):
        image = self.control.getSelectedItem().getProperty("original")
        wm.open_slideshow(image=image)

    @ch.click(350)
    @ch.click(1150)
    @ch.click(10)
    @busy_dialog
    def play_video(self):
        listitem = xbmcgui.ListItem(xbmc.getLocalizedString(20410))
        listitem.setInfo('video', {'title': xbmc.getLocalizedString(20410),
                                   'Genre': ADDON.getLocalizedString(32070)})
        if self.control_id == 10:
            youtube_id = self.getControl(1150).getListItem(0).getProperty("youtube_id")
        else:
            youtube_id = self.control.getSelectedItem().getProperty("youtube_id")
        if youtube_id:
            PLAYER.play_youtube_video(youtube_id=youtube_id,
                                      listitem=self.control.getSelectedItem(),
                                      window=self)
        else:
            notify(ADDON.getLocalizedString(32052))

    @ch.click(550)
    def open_company_list(self):
        company_id = self.control.getSelectedItem().getProperty("id")
        company_name = self.control.getSelectedItem().getLabel()
        filters = [{"id": company_id,
                    "type": "with_companies",
                    "typelabel": xbmc.getLocalizedString(20388),
                    "label": company_name}]
        wm.open_video_list(prev_window=self,
                           filters=filters)

    @ch.click(1050)
    def show_review(self):
        author = self.control.getSelectedItem().getProperty("author")
        text = "[B]%s[/B][CR]%s" % (author, clean_text(self.control.getSelectedItem().getProperty("content")))
        wm.open_textviewer(header=xbmc.getLocalizedString(207),
                           text=text,
                           color=self.info['ImageColor'])

    @ch.click(950)
    def open_keyword_list(self):
        keyword_id = self.control.getSelectedItem().getProperty("id")
        keyword_name = self.control.getSelectedItem().getLabel()
        filters = [{"id": keyword_id,
                    "type": "with_keywords",
                    "typelabel": ADDON.getLocalizedString(32114),
                    "label": keyword_name}]
        wm.open_video_list(prev_window=self,
                           filters=filters)

    @ch.click(850)
    def open_genre_list(self):
        genre_id = self.control.getSelectedItem().getProperty("id")
        genre_name = self.control.getSelectedItem().getLabel()
        filters = [{"id": genre_id,
                    "type": "with_genres",
                    "typelabel": xbmc.getLocalizedString(135),
                    "label": genre_name}]
        wm.open_video_list(prev_window=self,
                           filters=filters)

    @ch.click(650)
    def open_cert_list(self):
        country = self.control.getSelectedItem().getProperty("iso_3166_1")
        certification = self.control.getSelectedItem().getProperty("certification")
        year = self.control.getSelectedItem().getProperty("year")
        filters = [{"id": country,
                    "type": "certification_country",
                    "typelabel": ADDON.getLocalizedString(32153),
                    "label": country},
                   {"id": certification,
                    "type": "certification",
                    "typelabel": ADDON.getLocalizedString(32127),
                    "label": certification},
                   {"id": year,
                    "type": "year",
                    "typelabel": xbmc.getLocalizedString(345),
                    "label": year}]
        wm.open_video_list(prev_window=self,
                           filters=filters)

    @ch.click(450)
    def open_cert_list(self):
        list_id = self.control.getSelectedItem().getProperty("id")
        list_title = self.control.getSelectedItem().getLabel()
        wm.open_video_list(prev_window=self,
                           mode="list",
                           list_id=list_id,
                           filter_label=list_title)

    @ch.click(6002)
    def show_list_dialog(self):
        listitems = [ADDON.getLocalizedString(32134), ADDON.getLocalizedString(32135)]
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        account_lists = get_account_lists()
        for item in account_lists:
            listitems.append("%s (%i)" % (item["name"], item["item_count"]))
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32136), listitems)
        if index == -1:
            pass
        elif index == 0:
            wm.open_video_list(prev_window=self,
                               mode="favorites")
        elif index == 1:
            wm.open_video_list(prev_window=self,
                               mode="rating")
        else:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
            list_id = account_lists[index - 2]["id"]
            list_title = account_lists[index - 2]["name"]
            xbmc.executebuiltin("Dialog.Close(busydialog)")
            wm.open_video_list(prev_window=self,
                               mode="list",
                               list_id=list_id,
                               filter_label=list_title,
                               force=True)


    @ch.click(132)
    def show_plot(self):
        wm.open_textviewer(header=xbmc.getLocalizedString(207),
                           text=self.info["Plot"],
                           color=self.info['ImageColor'])


    @ch.click(6001)
    def set_rating_dialog(self):
        rating = get_rating_from_user()
        if rating:
            send_rating_for_media_item(media_type="movie",
                                       media_id=self.tmdb_id,
                                       rating=rating)
            self.update_states()

    @ch.click(6005)
    def add_to_list_dialog(self):
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        listitems = [ADDON.getLocalizedString(32139)]
        account_lists = get_account_lists()
        for item in account_lists:
            listitems.append("%s (%i)" % (item["name"], item["item_count"]))
        listitems.append(ADDON.getLocalizedString(32138))
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        index = xbmcgui.Dialog().select(heading=ADDON.getLocalizedString(32136),
                                        listitems=listitems)
        if index == 0:
            listname = xbmcgui.Dialog().input(heading=ADDON.getLocalizedString(32137),
                                              type=xbmcgui.INPUT_ALPHANUM)
            if listname:
                list_id = create_list(listname)
                xbmc.sleep(1000)
                change_list_status(list_id=list_id,
                                   movie_id=self.tmdb_id,
                                   status=True)
        elif index == len(listitems) - 1:
            self.remove_list_dialog(account_lists)
        elif index > 0:
            change_list_status(account_lists[index - 1]["id"], self.tmdb_id, True)
            self.update_states()

    @ch.click(6003)
    def change_list_status(self):
        if self.data["account_states"]["favorite"]:
            change_fav_status(media_id=self.info["id"],
                              media_type="movie",
                              status="false")
        else:
            change_fav_status(media_id=self.info["id"],
                              media_type="movie",
                              status="true")
        self.update_states()

    @ch.click(6006)
    def open_rating_list(self):
        wm.open_video_list(prev_window=self,
                           mode="rating")

    @ch.click(9)
    def play_movie_resume(self):
        self.close()
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %s }, "options":{ "resume": %s } }, "id": 1 }' % (str(self.info['dbid']), "true"))

    @ch.click(8)
    def play_movie_no_resume(self):
        self.close()
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %s }, "options":{ "resume": %s } }, "id": 1 }' % (str(self.info['dbid']), "false"))


    def onClick(self, control_id):
        ch.serve(control_id, self)

    def sort_lists(self, lists):
        if not self.logged_in:
            return lists
        account_list = get_account_lists(10)  # use caching here, forceupdate everywhere else
        own_lists = []
        misc_lists = []
        id_list = [item["id"] for item in account_list]
        for item in lists:
            if item["id"] in id_list:
                item["account"] = "True"
                own_lists.append(item)
            else:
                misc_lists.append(item)
        # own_lists = [item for item in lists if item["id"] in id_list]
        # misc_lists = [item for item in lists if item["id"] not in id_list]
        return own_lists + misc_lists

    def update_states(self, forceupdate=True):
        if forceupdate:
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            self.update = extended_movie_info(self.tmdb_id, self.dbid, 0)
            self.data["account_states"] = self.update["account_states"]
        if self.data["account_states"]:
            if self.data["account_states"]["favorite"]:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32155))
                self.window.setProperty("movie.favorite", "True")
            else:
                self.window.setProperty("FavButton_Label", ADDON.getLocalizedString(32154))
                self.window.setProperty("movie.favorite", "")
            if self.data["account_states"]["rated"]:
                self.window.setProperty("movie.rated", str(self.data["account_states"]["rated"]["value"]))
            else:
                self.window.setProperty("movie.rated", "")
            self.window.setProperty("movie.watchlist", str(self.data["account_states"]["watchlist"]))
            # notify(str(self.data["account_states"]["rated"]["value"]))

    def remove_list_dialog(self, account_lists):
        listitems = []
        for item in account_lists:
            listitems.append("%s (%i)" % (item["name"], item["item_count"]))
        prettyprint(account_lists)
        index = xbmcgui.Dialog().select(ADDON.getLocalizedString(32138), listitems)
        if index >= 0:
            # change_list_status(account_lists[index]["id"], self.tmdb_id, False)
            remove_list(account_lists[index]["id"])
            self.update_states()

    @ch.click(445)
    def show_manage_dialog(self):
        manage_list = []
        movie_id = str(self.info.get("dbid", ""))
        # filename = self.info.get("File", False)
        imdb_id = str(self.info.get("imdb_id", ""))
        if movie_id:
            manage_list += [[xbmc.getLocalizedString(413), "RunScript(script.artwork.downloader,mode=gui,mediatype=movie,dbid=" + movie_id + ")"],
                            [xbmc.getLocalizedString(14061), "RunScript(script.artwork.downloader, mediatype=movie, dbid=" + movie_id + ")"],
                            [ADDON.getLocalizedString(32101), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ",extrathumbs)"],
                            [ADDON.getLocalizedString(32100), "RunScript(script.artwork.downloader,mode=custom,mediatype=movie,dbid=" + movie_id + ")"]]
        else:
            manage_list += [[ADDON.getLocalizedString(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=" + imdb_id + ")||Notification(script.extendedinfo,%s))" % ADDON.getLocalizedString(32059)]]
        # if xbmc.getCondVisibility("system.hasaddon(script.tvtunes)") and movie_id:
        #     manage_list.append([ADDON.getLocalizedString(32102), "RunScript(script.tvtunes,mode=solo&amp;tvpath=$ESCINFO[Window.Property(movie.File)]&amp;tvname=$INFO[Window.Property(movie.TVShowTitle)])"])
        if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and movie_id:
            manage_list.append([ADDON.getLocalizedString(32103), "RunScript(script.libraryeditor,DBID=" + movie_id + ")"])
        manage_list.append([xbmc.getLocalizedString(1049), "Addon.OpenSettings(script.extendedinfo)"])
        listitems = [item[0] for item in manage_list]
        selection = xbmcgui.Dialog().select(heading=ADDON.getLocalizedString(32133),
                                            list=listitems)
        if selection > -1:
            for item in manage_list[selection][1].split("||"):
                xbmc.executebuiltin(item)


class JoinOmdbThread(threading.Thread):

    def __init__(self, omdb_thread, window_id):
        threading.Thread.__init__(self)
        self.omdb_thread = omdb_thread
        self.window_id = window_id

    def run(self):
        self.omdb_thread.join()
        if xbmcgui.getCurrentWindowDialogId() == self.window_id:
            pass_dict_to_skin(data=self.omdb_thread.listitems,
                              prefix="movie.omdb.",
                              window_id=self.window_id)


class SetItemsThread(threading.Thread):

    def __init__(self, set_id=""):
        threading.Thread.__init__(self)
        self.set_id = set_id

    def run(self):
        if self.set_id:
            self.listitems, self.setinfo = get_set_movies(self.set_id)
            self.id_list = [item["id"] for item in self.listitems]
        else:
            self.id_list = []
            self.listitems = []
            self.setinfo = {}

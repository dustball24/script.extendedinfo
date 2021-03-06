# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import threading

import xbmc
import xbmcgui

from resources.lib import TheMovieDB as tmdb
from resources.lib import omdb
from resources.lib.WindowManager import wm
from DialogVideoInfo import DialogVideoInfo

from kodi65 import imagetools
from kodi65 import addon
from kodi65 import utils
from kodi65 import kodijson
from ActionHandler import ActionHandler

ID_LIST_SIMILAR = 150
ID_LIST_SETS = 250
ID_LIST_YOUTUBE = 350
ID_LIST_LISTS = 450
ID_LIST_STUDIOS = 550
ID_LIST_CERTS = 650
ID_LIST_CREW = 750
ID_LIST_GENRES = 850
ID_LIST_KEYWORDS = 950
ID_LIST_ACTORS = 1000
ID_LIST_REVIEWS = 1050
ID_LIST_VIDEOS = 1150
ID_LIST_IMAGES = 1250
ID_LIST_BACKDROPS = 1350

ID_BUTTON_PLAY_NORESUME = 8
ID_BUTTON_PLAY_RESUME = 9
ID_BUTTON_TRAILER = 10
ID_BUTTON_SETRATING = 6001
ID_BUTTON_OPENLIST = 6002
ID_BUTTON_ADDTOLIST = 6005
ID_BUTTON_RATED = 6006

ch = ActionHandler()


def get_window(window_type):

    class DialogMovieInfo(DialogVideoInfo, window_type):
        TYPE = "Movie"
        TYPE_ALT = "movie"
        LISTS = [(ID_LIST_ACTORS, "actors"),
                 (ID_LIST_SIMILAR, "similar"),
                 (ID_LIST_SETS, "sets"),
                 (ID_LIST_LISTS, "lists"),
                 (ID_LIST_STUDIOS, "studios"),
                 (ID_LIST_CERTS, "releases"),
                 (ID_LIST_CREW, "crew"),
                 (ID_LIST_GENRES, "genres"),
                 (ID_LIST_KEYWORDS, "keywords"),
                 (ID_LIST_REVIEWS, "reviews"),
                 (ID_LIST_VIDEOS, "videos"),
                 (ID_LIST_IMAGES, "images"),
                 (ID_LIST_BACKDROPS, "backdrops")]

        # BUTTONS = [ID_BUTTON_OPENLIST,
        #            ID_BUTTON_ADDTOLIST]

        def __init__(self, *args, **kwargs):
            super(DialogMovieInfo, self).__init__(*args, **kwargs)
            data = tmdb.extended_movie_info(movie_id=kwargs.get('id'),
                                            dbid=self.dbid)
            if not data:
                return None
            self.info, self.lists, self.states = data
            sets_thread = SetItemsThread(self.info.get_property("set_id"))
            self.omdb_thread = utils.FunctionThread(function=omdb.get_movie_info,
                                                    param=self.info.get_property("imdb_id"))
            self.omdb_thread.start()
            sets_thread.start()
            self.info.update_properties(imagetools.blur(self.info.get_art("thumb")))
            if not self.info.get_info("dbid"):
                self.info.set_art("poster", utils.get_file(self.info.get_art("poster")))
            sets_thread.join()
            self.info.update_properties({"set.%s" % k: v for k, v in sets_thread.setinfo.iteritems()})
            set_ids = [item.get_property("id") for item in sets_thread.listitems]
            self.lists["similar"] = [i for i in self.lists["similar"] if i.get_property("id") not in set_ids]
            self.lists["sets"] = sets_thread.listitems

        def onInit(self):
            super(DialogMovieInfo, self).onInit()
            super(DialogMovieInfo, self).update_states()
            self.get_youtube_vids("%s %s, movie" % (self.info.label,
                                                    self.info.get_info("year")))
            self.join_omdb_async()

        def onClick(self, control_id):
            super(DialogMovieInfo, self).onClick(control_id)
            ch.serve(control_id, self)

        def set_buttons(self):
            super(DialogMovieInfo, self).set_buttons()
            condition = self.info.get_info("dbid") and int(self.info.get_property("percentplayed")) > 0
            self.set_visible(ID_BUTTON_PLAY_RESUME, condition)
            self.set_visible(ID_BUTTON_PLAY_NORESUME, self.info.get_info("dbid"))
            self.set_visible(ID_BUTTON_TRAILER, self.info.get_info("trailer"))
            # self.set_visible(ID_BUTTON_SETRATING, True)
            # self.set_visible(ID_BUTTON_RATED, True)

        @ch.click(ID_BUTTON_TRAILER)
        def play_trailer(self, control_id):
            listitem = self.info.get_listitem()
            youtube_id = self.info.get_property("trailer")
            wm.play_youtube_video(youtube_id=youtube_id,
                                  listitem=listitem,
                                  window=self)

        @ch.click(ID_LIST_STUDIOS)
        def open_company_list(self, control_id):
            filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                        "type": "with_companies",
                        "typelabel": addon.LANG(20388),
                        "label": self.FocusedItem(control_id).getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(ID_LIST_REVIEWS)
        def show_review(self, control_id):
            author = self.FocusedItem(control_id).getProperty("author")
            text = "[B]%s[/B][CR]%s" % (author, self.FocusedItem(control_id).getProperty("content"))
            xbmcgui.Dialog().textviewer(heading=addon.LANG(207),
                                        text=text)

        @ch.click(ID_LIST_KEYWORDS)
        def open_keyword_list(self, control_id):
            filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                        "type": "with_keywords",
                        "typelabel": addon.LANG(32114),
                        "label": self.FocusedItem(control_id).getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(ID_LIST_GENRES)
        def open_genre_list(self, control_id):
            filters = [{"id": self.FocusedItem(control_id).getProperty("id"),
                        "type": "with_genres",
                        "typelabel": addon.LANG(135),
                        "label": self.FocusedItem(control_id).getLabel().decode("utf-8")}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(ID_LIST_CERTS)
        def open_cert_list(self, control_id):
            info = self.FocusedItem(control_id).getVideoInfoTag()
            filters = [{"id": self.FocusedItem(control_id).getProperty("iso_3166_1"),
                        "type": "certification_country",
                        "typelabel": addon.LANG(32153),
                        "label": self.FocusedItem(control_id).getProperty("iso_3166_1")},
                       {"id": self.FocusedItem(control_id).getProperty("certification"),
                        "type": "certification",
                        "typelabel": addon.LANG(32127),
                        "label": self.FocusedItem(control_id).getProperty("certification")},
                       {"id": str(info.getYear()),
                        "type": "year",
                        "typelabel": addon.LANG(345),
                        "label": str(info.getYear())}]
            wm.open_video_list(prev_window=self,
                               filters=filters)

        @ch.click(ID_LIST_LISTS)
        def open_lists_list(self, control_id):
            wm.open_video_list(prev_window=self,
                               mode="list",
                               list_id=self.FocusedItem(control_id).getProperty("id"),
                               filter_label=self.FocusedItem(control_id).getLabel().decode("utf-8"))

        @ch.click(ID_BUTTON_OPENLIST)
        def show_list_dialog(self, control_id):
            wm.show_busy()
            movie_lists = tmdb.get_account_lists()
            listitems = ["%s (%i)" % (i["name"], i["item_count"]) for i in movie_lists]
            listitems = [addon.LANG(32134), addon.LANG(32135)] + listitems
            wm.hide_busy()
            index = xbmcgui.Dialog().select(addon.LANG(32136), listitems)
            if index == -1:
                pass
            elif index < 2:
                wm.open_video_list(prev_window=self,
                                   mode="favorites" if index == 0 else "rating")
            else:
                wm.open_video_list(prev_window=self,
                                   mode="list",
                                   list_id=movie_lists[index - 2]["id"],
                                   filter_label=movie_lists[index - 2]["name"],
                                   force=True)

        @ch.click(ID_BUTTON_ADDTOLIST)
        def add_to_list_dialog(self, control_id):
            wm.show_busy()
            account_lists = tmdb.get_account_lists()
            listitems = ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
            listitems.insert(0, addon.LANG(32139))
            listitems.append(addon.LANG(32138))
            wm.hide_busy()
            index = xbmcgui.Dialog().select(heading=addon.LANG(32136),
                                            list=listitems)
            if index == 0:
                listname = xbmcgui.Dialog().input(heading=addon.LANG(32137),
                                                  type=xbmcgui.INPUT_ALPHANUM)
                if not listname:
                    return None
                list_id = tmdb.create_list(listname)
                xbmc.sleep(1000)
                tmdb.change_list_status(list_id=list_id,
                                        movie_id=self.info.get_property("id"),
                                        status=True)
            elif index == len(listitems) - 1:
                self.remove_list_dialog(account_lists)
            elif index > 0:
                tmdb.change_list_status(account_lists[index - 1]["id"], self.info.get_property("id"), True)
                self.update_states()

        @ch.click(ID_BUTTON_RATED)
        def open_rating_list(self, control_id):
            wm.open_video_list(prev_window=self,
                               mode="rating")

        @ch.click(ID_BUTTON_PLAY_RESUME)
        def play_movie_resume(self, control_id):
            self.exit_script()
            xbmc.executebuiltin("Dialog.Close(movieinformation)")
            kodijson.play_media("movie", self.info["dbid"], True)

        @ch.click(ID_BUTTON_PLAY_NORESUME)
        def play_movie_no_resume(self, control_id):
            self.exit_script()
            xbmc.executebuiltin("Dialog.Close(movieinformation)")
            kodijson.play_media("movie", self.info["dbid"], False)

        def get_manage_options(self):
            options = []
            movie_id = str(self.info.get("dbid", ""))
            imdb_id = str(self.info.get("imdb_id", ""))
            if movie_id:
                call = "RunScript(script.artwork.downloader,mediatype=movie,dbid={}%s)".format(movie_id)
                options += [[addon.LANG(413), call % "mode=gui"],
                            [addon.LANG(14061), call % ""],
                            [addon.LANG(32101), call % "mode=custom,extrathumbs"],
                            [addon.LANG(32100), call % "mode=custom"]]
            else:
                options += [[addon.LANG(32165), "RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?imdb_id=" + imdb_id + ")||Notification(script.extendedinfo,%s))" % addon.LANG(32059)],
                            [addon.LANG(32170), "RunPlugin(plugin://plugin.video.trakt_list_manager/watchlist/movies/add?imdb_id=" + imdb_id + ")"]]
            if xbmc.getCondVisibility("system.hasaddon(script.libraryeditor)") and movie_id:
                options.append([addon.LANG(32103), "RunScript(script.libraryeditor,DBID=%s)" % movie_id])
            options.append([addon.LANG(1049), "Addon.OpenSettings(script.extendedinfo)"])
            return options

        def update_states(self):
            xbmc.sleep(2000)  # delay because MovieDB takes some time to update
            _, __, self.states = tmdb.extended_movie_info(movie_id=self.info.get_property("id"),
                                                          dbid=self.dbid,
                                                          cache_time=0)
            super(DialogMovieInfo, self).update_states()

        def remove_list_dialog(self, account_lists):
            listitems = ["%s (%i)" % (d["name"], d["item_count"]) for d in account_lists]
            index = xbmcgui.Dialog().select(addon.LANG(32138), listitems)
            if index >= 0:
                tmdb.remove_list(account_lists[index]["id"])
                self.update_states()

        @utils.run_async
        def join_omdb_async(self):
            self.omdb_thread.join()
            utils.dict_to_windowprops(data=self.omdb_thread.listitems,
                                      prefix="omdb.",
                                      window_id=self.window_id)

    class SetItemsThread(threading.Thread):

        def __init__(self, set_id=""):
            threading.Thread.__init__(self)
            self.set_id = set_id

        def run(self):
            if self.set_id:
                self.listitems, self.setinfo = tmdb.get_set_movies(self.set_id)
            else:
                self.listitems = []
                self.setinfo = {}

    return DialogMovieInfo

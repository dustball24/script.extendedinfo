# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
import xbmc


from resources.lib import TheMovieDB as tmdb
from DialogBaseInfo import DialogBaseInfo

from kodi65 import addon
from kodi65 import utils
from ActionHandler import ActionHandler


BUTTONS = [8, 9, 10, 6001, 6002, 6003, 6005, 6006]

ID_BUTTON_PLOT = 132
ID_BUTTON_MANAGE = 445
ID_BUTTON_SETRATING = 6001
ID_BUTTON_FAV = 6003

ch = ActionHandler()


class DialogVideoInfo(DialogBaseInfo):

    def __init__(self, *args, **kwargs):
        super(DialogVideoInfo, self).__init__(*args, **kwargs)

    def onClick(self, control_id):
        super(DialogVideoInfo, self).onClick(control_id)
        ch.serve(control_id, self)

    def set_buttons(self):
        for button_id in BUTTONS:
            self.set_visible(button_id, False)

    @ch.click(ID_BUTTON_PLOT)
    def show_plot(self, control_id):
        xbmcgui.Dialog().textviewer(heading=addon.LANG(207),
                                    text=self.info.get_info("plot"))

    def get_manage_options(self):
        return []

    def get_identifier(self):
        return self.info.get_property("id")

    @ch.click(ID_BUTTON_MANAGE)
    def show_manage_dialog(self, control_id):
        options = self.get_manage_options()
        selection = xbmcgui.Dialog().select(heading=addon.LANG(32133),
                                            list=[i[0] for i in options])
        if selection == -1:
            return None
        for item in options[selection][1].split("||"):
            xbmc.executebuiltin(item)

    @ch.click(ID_BUTTON_FAV)
    def change_list_status(self, control_id):
        tmdb.change_fav_status(media_id=self.info.get_property("id"),
                               media_type=self.TYPE_ALT,
                               status=str(not bool(self.states["favorite"])).lower())
        self.update_states()

    @ch.click(ID_BUTTON_SETRATING)
    def set_rating_dialog(self, control_id):
        rating = utils.input_userrating()
        if tmdb.set_rating(media_type=self.TYPE_ALT,
                           media_id=self.get_identifier(),
                           rating=rating,
                           dbid=self.info.get("dbid")):
            self.update_states()

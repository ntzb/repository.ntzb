"""Emit patches/<addon id>/*.json from an extracted pristine add-on tree.

Usage: gendescriptors.py <addon id> <extracted tree> <patches dir>

Counts and context hashes are measured, never hand-written: the one hand-typed
count in an earlier draft was wrong, and it was the only number in the design.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patchlib

SKIN = "skin.arctic.fuse.3"
SCRAPER = "metadata.themoviedb.org.python.ntzb"
HELPER = "plugin.video.themoviedb.helper"
MODULE = "script.module.jurialmunkey"
IDAN = "plugin.video.idanplus"

SETTING = "View.DisableClearlogoTitle"
FONT_ADDON = "resource.font.af3hebrew"
INFO = "1080i/Includes_Info.xml"
SKINSET = "1080i/Includes_SkinSettings.xml"
FONTXML = "1080i/Font.xml"
EXPRXML = "1080i/Includes_Expressions.xml"

IMAGE_ANCHOR = '<control type="image">\n                    <height>info_title_logo_h</height>'

SETTINGS_ANCHOR = (
    "            <onclick>Skin.ToggleSetting(View.UseDetailedListLabels)</onclick>\n"
    "        </include>\n"
)

SETTINGS_BUTTON = SETTINGS_ANCHOR + """
        <include content="Settings_Button" description="Clearlogo title">
            <param name="dialog">false</param>
            <param name="window">skinsettings</param>
            <param name="baseid">$PARAM[baseid]</param>
            <param name="id">900</param>
            <param name="slevel">1</param>
            <param name="control">radiobutton</param>
            <label>Logo</label>
            <onclick>Skin.ToggleSetting(%s)</onclick>
            <selected>!Skin.HasSetting(%s)</selected>
        </include>
""" % (SETTING, SETTING)


def title_edits():
    yield INFO, "replace", IMAGE_ANCHOR, IMAGE_ANCHOR.replace(
        '<control type="image">\n',
        '<control type="image">\n                    <visible>!Skin.HasSetting(%s)</visible>\n' % SETTING)
    # Anchored on '>' throughout: '!String.IsEmpty(X)' contains 'String.IsEmpty(X)',
    # and widening the expectation to absorb that would rewrite the negated line,
    # inverting the negation across the new OR.
    for art in ("clearlogo", "tvshow.clearlogo", "artist.clearlogo"):
        f = "<visible>String.IsEmpty($PARAM[container]$PARAM[listitem].Art(%s))</visible>" % art
        w = ("<visible>[String.IsEmpty($PARAM[container]$PARAM[listitem].Art(%s)) | "
             "Skin.HasSetting(%s)]</visible>" % (art, SETTING))
        yield INFO, "replace", f, w
    f = "<visible>![!String.IsEmpty($PARAM[croplogo]) + $EXP[Exp_TMDbHelper_IsCrop]]</visible>"
    w = ("<visible>[![!String.IsEmpty($PARAM[croplogo]) + $EXP[Exp_TMDbHelper_IsCrop]] | "
         "Skin.HasSetting(%s)]</visible>" % SETTING)
    yield INFO, "replace", f, w
    yield SKINSET, "insert", SETTINGS_ANCHOR, SETTINGS_BUTTON


DBTYPES = " | ".join(
    "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,%s)" % t
    for t in ("movie", "tvshow", "episode", "season", "video"))

GENRE_SETTING = "InfoTags.DisableGenre"   # absent: genre. present: age rating.

GENRE_ANCHOR = "                    <!-- Year -->"

# Kodi joins ListItem.Genre with " / " and offers no way to index it, so the first
# genre is recovered by prefix-matching the joined string. Longer names first: both
# "Action" and "Action & Adventure" would match a StartsWith on "Action".
GENRES = (
    "Action & Adventure", "מדע בדיוני ופנטזיה", "Sci-Fi & Fantasy", "Science Fiction",
    "מלחמה ופוליטיקה", "War & Politics", "אקשן והרפתקאות", "Documentary", "סרט טלויזיה",
    "מדע בדיוני", "Adventure", "Animation", "דוקומנטרי", "TV Movie", "Thriller", "הרפתקאות",
    "Fantasy", "History", "Mystery", "Reality", "Romance", "Western", "אנימציה", "דיבורים",
    "הסטוריה", "מסתורין", "ריאליטי", "Action", "Comedy", "Family", "Horror", "מוסיקה", "מערבון",
    "פנטזיה", "קומדיה", "רומנטי", "Crime", "Drama", "Music", "חדשות", "ילדים", "מותחן", "מלחמה",
    "משפחה", "Kids", "News", "Soap", "Talk", "אימה", "אקשן", "דרמה", "סבון", "War", "פשע",
)

_GENRE_LABEL = """                    <include content="Info_Line_Label">
                        <param name="colordiffuse">$PARAM[colordiffuse]</param>
                        <param name="label">%s</param>
                        <param name="visible">!Skin.HasSetting(%s) + %s + [%s | $PARAM[override]]</param>
                    </include>
"""


def _genre_labels():
    # No TMDb genre contains "/", so a slash in the joined string means more than one.
    multi = "String.Contains($PARAM[container]$PARAM[listitem].Genre,/)"
    yield _GENRE_LABEL % (
        "$INFO[$PARAM[container]$PARAM[listitem].Genre]", GENRE_SETTING,
        "!String.IsEmpty($PARAM[container]$PARAM[listitem].Genre) + !" + multi, DBTYPES)
    for g in GENRES:
        x = g.replace("&", "&amp;")   # these land inside XML attributes and text
        cond = "%s + String.StartsWith($PARAM[container]$PARAM[listitem].Genre,%s)" % (multi, x)
        yield _GENRE_LABEL % (x, GENRE_SETTING, cond, DBTYPES)


GENRE_BLOCK = ("                    <!-- Genre -->\n"
               + "".join(_genre_labels()) + "\n" + GENRE_ANCHOR)

MPAA_FIND = '<param name="visible">!String.IsEmpty($PARAM[container]$PARAM[listitem].MPAA) + ['
MPAA_WITH = ('<param name="visible">Skin.HasSetting(%s) + '
             '!String.IsEmpty($PARAM[container]$PARAM[listitem].MPAA) + [' % GENRE_SETTING)

GENRE_TOGGLE_ANCHOR = (
    "            <onclick>Skin.ToggleSetting(InfoTags.DisableStarRating)</onclick>\n"
    "            <selected>!Skin.HasSetting(InfoTags.DisableStarRating)</selected>\n"
    "        </include>\n"
)

GENRE_TOGGLE = GENRE_TOGGLE_ANCHOR + """        <include content="Settings_Button" description="Genre instead of age rating">
            <param name="dialog">false</param>
            <param name="window">skinsettings</param>
            <param name="baseid">$PARAM[baseid]</param>
            <param name="id">901</param>
            <param name="control">radiobutton</param>
            <label>Genre</label>
            <onclick>Skin.ToggleSetting(%s)</onclick>
            <selected>!Skin.HasSetting(%s)</selected>
        </include>
""" % (GENRE_SETTING, GENRE_SETTING)


def genre_edits():
    yield INFO, "insert", GENRE_ANCHOR, GENRE_BLOCK
    yield INFO, "replace", MPAA_FIND, MPAA_WITH
    yield SKINSET, "insert", GENRE_TOGGLE_ANCHOR, GENRE_TOGGLE


SKELETON_SETTING = "InfoTags.DisableMetaSkeleton"   # absent: placeholder. present: nothing.
SKELETON_DEBUG = "InfoTags.DebugMetaSkeleton"       # present: the monitor's live state in the row.

# TMDb Helper already says when it is working, and it says it twice, for two different
# halves of the row: lib/monitor/listitemtools.py sets IsUpdating around the blocking
# details build ("Set a property for skins to check if item details are updating") and
# lib/monitor/listitemfinaliser.py sets IsUpdatingRatings around the ratings thread that
# follows it, both through jurialmunkey.window.WindowPropertySetter.get_property with
# prefix="TMDbHelper" and window_id=10000, hence Window(Home).
#
# Which flag bounds which field is not a guess: baseview_factories/.../ratings.py is the
# only producer of the rating properties, of Top250 and -- through omdb/mapping.py's
# oscar_wins -- of Oscar_Wins, and it runs inside that ratings thread; Status arrives with
# the details instead, api/tmdb/mapping.py mapping it to an infolabel that
# monitor/common.py set_properties() writes during the blocking build. So ratings and
# awards are stale until IsUpdatingRatings clears, and Status only until IsUpdating does.
#
# No id property says which item the values on screen belong to. Both candidates move with
# the cursor, ahead of the values: base_tmdb_id is copied off the focused listitem by the
# images monitor on every poll, and monitor.tmdb_id is set by
# ListItemMonitorFinaliser.get_item() before the details build it introduces -- so either
# one matches again while the previous item's ratings are still on screen, and comparing
# it against ListItem.UniqueID(tmdb) would report fresh exactly when the row is stalest.
# The flags are the only honest answer, and they are the whole answer: the monitor
# overwrites properties rather than clearing them first, so whatever is drawn between a
# flag going up and coming down belongs to the item the cursor has already left.
SKELETON_EXPR_ANCHOR = (
    '    <expression name="Exp_TMDbHelper_IsCrop">'
    '[Skin.HasSetting(TMDbHelper.EnableCrop)]</expression>\n')

_IS_SET = "!String.IsEmpty(Window(Home).Property(TMDbHelper.%s))"

SKELETON_EXPR = SKELETON_EXPR_ANCHOR + (
    '    <expression name="Exp_TMDbHelper_IsSkeleton">'
    '[$EXP[Exp_TMDbHelper_IsData] + !Skin.HasSetting(%s)]</expression>\n'
    '    <expression name="Exp_TMDbHelper_IsStaleDetails">'
    '[$EXP[Exp_TMDbHelper_IsSkeleton] + %s]</expression>\n'
    '    <expression name="Exp_TMDbHelper_IsStaleRatings">'
    '[$EXP[Exp_TMDbHelper_IsSkeleton] + [%s | %s]]</expression>\n'
    % (SKELETON_SETTING, _IS_SET % "IsUpdating",
       _IS_SET % "IsUpdating", _IS_SET % "IsUpdatingRatings"))

# The stale value has to leave before the placeholder can stand in for it, and it has to
# leave on the same timer, or a step of the cursor that resolves inside the debounce
# blanks the row for a second. A Hidden animation does that and nothing else: Kodi holds a
# control VISIBLE -- laid out, opaque -- for the whole of its hide animation
# (GUIControl.cpp UpdateStates, ANIM_TYPE_HIDDEN), while a Visible animation still inside
# its delay leaves the control DELAYED, which IsVisible() reports as not visible and
# GUIControlGroupList skips when it lays the row out. So for the first second nothing
# moves and nothing changes; then the value fades out as the placeholder fades in, over
# the same 200ms. If the values arrive first the queued animation is reset and the row
# just updates, which is every cached item.
#
# Conditional, because Info_Meta_Object draws the rest of the row too -- album, birthday,
# end time -- and those come from Kodi rather than from the service and must keep
# disappearing the instant they stop applying. GetAnimation() checks the condition before
# queueing, so an unmet one means no animation and an immediate hide, which is also what
# an unresolved $EXP would degrade to.
OBJECT_PARAM_ANCHOR = ('    <include name="Info_Meta_Object">\n'
                       '        <param name="font">font_main</param>\n')

OBJECT_PARAM = OBJECT_PARAM_ANCHOR + '        <param name="stale">false</param>\n'

STALE_ANIM = (
    '                <animation type="Hidden" condition="$PARAM[stale]" reversible="false">\n'
    '                    <effect type="fade" start="100" end="0" time="200" delay="1000" />\n'
    '                </animation>\n')

# One per control the include draws -- the icon, the label, and the spacer holding the gap
# to the next field open -- each anchored on a line of its own rather than on the closing
# tag they share, so that the anchor survives the insertion. Leaving the spacer out would
# shift the rest of the row by its four pixels for the second the other two are still up.
OBJECT_ANCHORS = (
    '                <bordersize>$PARAM[bordersize]</bordersize>\n',
    '                <texturenofocus />\n',
    '                <width>-4</width>\n',
)

RATINGS_FIND = ('                <param name="visible">[$PARAM[visible]] + '
                '!String.IsEmpty(Window(Home).Property(TMDbHelper.$PARAM[service].')

RATINGS_WITH = (
    '                <param name="stale">$EXP[Exp_TMDbHelper_IsStaleRatings]</param>\n'
    '                <param name="visible">!$EXP[Exp_TMDbHelper_IsStaleRatings] + '
    '[$PARAM[visible]] + '
    '!String.IsEmpty(Window(Home).Property(TMDbHelper.$PARAM[service].')

STATUS_FIND = (
    '                        <param name="visible">'
    '[[String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | '
    'String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | '
    'String.IsEqual($PARAM[container]$PARAM[listitem].DBType,episode) | $PARAM[override_tvshow]] + '
    '!String.IsEmpty(Window(Home).Property(TMDbHelper.$PARAM[service].Status))]</param>\n')

STATUS_WITH = (
    '                        <param name="stale">$EXP[Exp_TMDbHelper_IsStaleDetails]</param>\n'
    + STATUS_FIND.replace('<param name="visible">[[',
                          '<param name="visible">!$EXP[Exp_TMDbHelper_IsStaleDetails] + [['))

AWARDS_FIND = (
    '                        <param name="visible">'
    '[String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | $PARAM[override_movie]] + '
    '!String.IsEmpty(Window(Home).Property(TMDbHelper.$PARAM[service].Oscar_Wins))</param>\n')

AWARDS_WITH = (
    '                        <param name="stale">$EXP[Exp_TMDbHelper_IsStaleRatings]</param>\n'
    + AWARDS_FIND.replace('<param name="visible">[String.IsEqual',
                          '<param name="visible">!$EXP[Exp_TMDbHelper_IsStaleRatings] + [String.IsEqual'))

SKELETON_DEF_ANCHOR = '    <include name="Info_Meta_Item_Row">'

# Borrowed wholesale from the skin's own placeholder, Widget_Busy_BlankItem /
# Widget_Busy in Includes_Widgets.xml: a 24px common/widget_text.png bar at
# main_fg_12, faded in by a Visible animation with reversible="false" so that
# hiding it is instant rather than a reversed fade. Only the timings differ --
# 1000ms against the widgets' 200ms, because the service polls every 200ms
# (POLL_MIN_INCREMENT) and a step of the cursor that resolves well inside a second
# must not blink. The delay restarts whenever the flags go up again, which is once
# per item; held down across a run of items they stay set and it stays up rather
# than starting the wait over. The pulse is the nearest thing Kodi has to a
# shimmer: no skin sweeps a gradient, because groups do not clip their children.
SKELETON_DEF = """    <include name="Info_Meta_Skeleton">
        <param name="width">96</param>
        <definition>
            <control type="group" description="Placeholder held while TMDbHelper is still answering for this item">
                <width>$PARAM[width]</width>
                <height>40</height>
                <visible>$PARAM[visible]</visible>
                <visible>$EXP[Exp_TMDbHelper_IsStaleRatings]</visible>
                <animation type="Visible" reversible="false">
                    <effect type="fade" start="0" end="100" time="200" delay="1000" />
                </animation>
                <control type="image">
                    <top>8</top>
                    <bottom>8</bottom>
                    <texture colordiffuse="main_fg_12" border="12">common/widget_text.png</texture>
                    <animation type="Conditional" condition="true" reversible="false" loop="true">
                        <effect type="fade" start="100" end="45" time="900" pulse="true" reversible="false" />
                    </animation>
                </control>
            </control>
        </definition>
    </include>

""" + SKELETON_DEF_ANCHOR

SKELETON_ROW_ANCHOR = "                    <!-- Ratings -->"

_SKELETON_ITEM = """                    <include content="Info_Meta_Skeleton" condition="$EXP[Exp_TMDbHelper_IsData]">
                        <param name="visible">[%s] + !String.IsEmpty(Skin.String(CustomRating.%s.Item%02d))</param>
                    </include>
"""

# One bar per rating slot the user has actually configured, mirroring the six
# Info_Meta_Ratings instances it sits above, so the placeholder is the shape of what is
# coming rather than a guess. Status and awards get no bar of their own: a rating slot is
# a promise the user made, but whether the next item carries a status or an Oscar is not
# known until it lands, and a bar that resolves to nothing is worse than a field that was
# never drawn. They do leave with the rest, on the same timer.
_SKELETON_DBTYPES = (
    ("Movies", "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | $PARAM[override_movie]"),
    ("TVShows", "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | "
                "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override_tvshow]"),
)

SKELETON_ROW = ("                    <!-- Ratings Placeholder -->\n"
                + "".join(_SKELETON_ITEM % (cond, content, n)
                          for content, cond in _SKELETON_DBTYPES for n in (1, 2, 3))
                + "\n" + SKELETON_ROW_ANCHOR)

# The timings above are reasoned from the service's source, not measured on a running
# Kodi, so the row can show its own workings: every property the condition is built out
# of, live, behind a second setting that is off by default. base_tmdb_id and
# monitor.tmdb_id are in there to be watched rather than used -- if either ever lagged the
# values instead of leading them, it would show up here first.
SKELETON_DEBUG_ANCHOR = ("\n                </control>\n            </control>\n        </definition>\n"
                         '    </include>\n\n    <include name="Info_Meta_Grouplist_Definition">')

_DEBUG_FIELDS = (
    ("upd", "Window(Home).Property(TMDbHelper.IsUpdating)"),
    ("rat", "Window(Home).Property(TMDbHelper.IsUpdatingRatings)"),
    ("mon", "Window(Home).Property(TMDbHelper.ListItem.monitor.tmdb_id)"),
    ("det", "Window(Home).Property(TMDbHelper.ListItem.tmdb_id)"),
    ("base", "Window(Home).Property(TMDbHelper.ListItem.base_tmdb_id)"),
    ("cur", "$PARAM[container]$PARAM[listitem].UniqueID(tmdb)"),
    ("imdb", "Window(Home).Property(TMDbHelper.$PARAM[service].IMDb_Rating)"),
    ("sta", "Window(Home).Property(TMDbHelper.$PARAM[service].Status)"),
)

SKELETON_DEBUG_BLOCK = ("""
                    <!-- Skeleton Debug -->
                    <include content="Info_Meta_Object" condition="$EXP[Exp_TMDbHelper_IsData]">
                        <param name="bordersize">-12</param>
                        <param name="icon">special://skin/extras/icons/bug.png</param>
                        <param name="label">%s</param>
                        <param name="visible">Skin.HasSetting(%s)</param>
                        <param name="max_width">1200</param>
                    </include>
""" % (" ".join("%s:$INFO[%s]" % (k, v) for k, v in _DEBUG_FIELDS), SKELETON_DEBUG)
    + SKELETON_DEBUG_ANCHOR[1:])

SKELETON_TOGGLE_ANCHOR = (
    "            <onclick>SetProperty(CustomDialogSettingsItems,"
    "DialogCustom_Ratings_TVShows_Items,Home)</onclick>\n"
    "            <onclick>ActivateWindow(1118)</onclick>\n"
    "            <visible>$EXP[Exp_TMDbHelper_IsData]</visible>\n"
    "        </include>\n")

SKELETON_TOGGLE = SKELETON_TOGGLE_ANCHOR + """
        <include content="Settings_Button" description="Ratings loading placeholder">
            <param name="dialog">false</param>
            <param name="window">skinsettings</param>
            <param name="baseid">$PARAM[baseid]</param>
            <param name="id">902</param>
            <param name="control">radiobutton</param>
            <label>Loading placeholder</label>
            <onclick>Skin.ToggleSetting(%s)</onclick>
            <selected>!Skin.HasSetting(%s)</selected>
            <visible>$EXP[Exp_TMDbHelper_IsData]</visible>
        </include>
        <include content="Settings_Button" description="Loading placeholder debug readout">
            <param name="dialog">false</param>
            <param name="window">skinsettings</param>
            <param name="baseid">$PARAM[baseid]</param>
            <param name="id">903</param>
            <param name="control">radiobutton</param>
            <label>Loading placeholder debug</label>
            <onclick>Skin.ToggleSetting(%s)</onclick>
            <selected>Skin.HasSetting(%s)</selected>
            <visible>$EXP[Exp_TMDbHelper_IsData] + !Skin.HasSetting(%s)</visible>
        </include>
""" % (SKELETON_SETTING, SKELETON_SETTING, SKELETON_DEBUG, SKELETON_DEBUG, SKELETON_SETTING)


def skeleton_edits():
    yield EXPRXML, "insert", SKELETON_EXPR_ANCHOR, SKELETON_EXPR
    yield INFO, "insert", OBJECT_PARAM_ANCHOR, OBJECT_PARAM
    for anchor in OBJECT_ANCHORS:
        yield INFO, "insert", anchor, STALE_ANIM + anchor
    yield INFO, "replace", RATINGS_FIND, RATINGS_WITH
    yield INFO, "replace", STATUS_FIND, STATUS_WITH
    yield INFO, "replace", AWARDS_FIND, AWARDS_WITH
    yield INFO, "insert", SKELETON_DEF_ANCHOR, SKELETON_DEF
    yield INFO, "insert", SKELETON_ROW_ANCHOR, SKELETON_ROW
    yield INFO, "insert", SKELETON_DEBUG_ANCHOR, SKELETON_DEBUG_BLOCK
    yield SKINSET, "insert", SKELETON_TOGGLE_ANCHOR, SKELETON_TOGGLE


def font_edits():
    for weight in ("Regular", "Bold"):
        f = "resource://resource.font.robotocjksc/Inter-Unicode-%s.ttf" % weight
        yield FONTXML, "replace", f, f.replace("resource.font.robotocjksc", FONT_ADDON)
    yield "addon.xml", "insert", "    </requires>", \
        '        <import addon="%s" version="1.1.0" />\n    </requires>' % FONT_ADDON


HELPER_TMDBAPI = "resources/tmdbhelper/lib/api/tmdb/api.py"
HELPER_BASEITEM = "resources/tmdbhelper/lib/items/database/baseitem_factories/concrete_classes/baseclass.py"
HELPER_MAPPINGS = "resources/tmdbhelper/lib/items/database/mappings.py"
HELPER_LISTITEM = "resources/tmdbhelper/lib/items/listitem.py"
HELPER_GENRES = "resources/tmdbhelper/lib/query/database/genres.py"

# TMDb localises the item itself -- title, plot, poster_path, cast and crew names,
# studios, genres -- from the language query parameter, and the add-on derives that
# parameter, the artwork and video language preferences, and the art tables' language
# lookup from this one property. Pinning it to English is the whole of "everything in
# English": nothing downstream has to be patched back. iso_country is left alone, so
# self.language keeps meaning he-IL and region still selects Israeli certifications
# and Israeli watch providers.
ISO_LANGUAGE_FIND = """    @property
    def iso_language(self):
        return self.language[:2]
"""

ISO_LANGUAGE_WITH = """    @property
    def iso_language(self):
        return 'en'
"""


def helper_english_metadata_edits():
    yield HELPER_TMDBAPI, "replace", ISO_LANGUAGE_FIND, ISO_LANGUAGE_WITH


IS_TRANSLATION_FIND = """    @property
    def is_translation(self):
        if self.cache_refresh == 'force':
            return True
        if self.cache_translations:
            return True
        if get_setting('force_english_plot_fallback'):
            return True
        return False
"""

IS_TRANSLATION_WITH = """    @property
    def is_translation(self):
        return True
"""

# get_info() runs once per item, on a cache miss, on the response that
# append_to_response has already carried the translations in -- so the plot is
# swapped before the row is written and every later read is free. item['item'] is
# the media row and item['translation'] the rows the same response produced; a type
# without a plot column drops the key when the row is assembled.
GET_INFO_ANCHOR = """    def get_info(self, data, **kwargs):
        self.data = data
        self.item = self.get_empty_item()
        self.item = self.map_item(self.item, data)
        self.item = self.map_dict(self.item, data)
"""

GET_INFO_WITH = """    def set_translated_plot(self, item):
        iso_language = self.language[:2]
        for i in item['translation']:
            if i['iso_language'] != iso_language:
                continue
            if i['plot']:
                item['item']['plot'] = i['plot']
            break
        return item

""" + GET_INFO_ANCHOR + """        self.item = self.set_translated_plot(self.item)
"""

# merge_two_dicts(details, self) keeps self, so the plot mapped straight off the
# list response outranks the one the details cache just translated. Title and
# tvshowtitle are already exempted here for the same reason; plot joins them.
PLOT_OVERRIDE_ANCHOR = (
    "        self.infolabels['tvshowtitle'] = details.get('infolabels', {})"
    ".get('tvshowtitle') or self.infolabels.get('tvshowtitle')\n")

PLOT_OVERRIDE_WITH = PLOT_OVERRIDE_ANCHOR + (
    "        self.infolabels['plot'] = details.get('infolabels', {})"
    ".get('plot') or self.infolabels.get('plot')\n")


def helper_translated_plot_edits():
    # 'translations' rides along on the details call every uncached item already
    # makes, so the Hebrew plot costs a bigger response rather than another request.
    # Unconditional rather than behind the existing plot-fallback setting: rows
    # already cached without them then fail the baseitem.translation cache condition
    # and are refetched once.
    yield HELPER_BASEITEM, "replace", IS_TRANSLATION_FIND, IS_TRANSLATION_WITH
    yield HELPER_MAPPINGS, "insert", GET_INFO_ANCHOR, GET_INFO_WITH
    yield HELPER_LISTITEM, "insert", PLOT_OVERRIDE_ANCHOR, PLOT_OVERRIDE_WITH


# Genre names never come from the item: both the list mapper's genre_ids and the
# details mapper's genres array are reduced to ids and looked up in one id->name map
# that this function fills and the genres table caches for thirty days. So asking for
# that map in the add-on's own language -- the only request that still does -- is the
# whole of "genres in Hebrew", for two requests a month and no per-item cost.
# configure_request_kwargs() overwrites language unconditionally, hence building the
# url the way get_response_json does rather than passing a keyword it would discard.
GENRES_FIND = """        def get_genres(tmdb_type):
            genres = self.tmdb_api.get_response_json('genre', tmdb_type, 'list') or {}
"""

GENRES_WITH = """        def get_genres(tmdb_type):
            requrl = self.tmdb_api.get_request_url('genre', tmdb_type, 'list', language=self.tmdb_api.language)
            genres = self.tmdb_api.get_api_request_json(requrl) or {}
"""


HELPER_ART_FIND = '        for artwork_type, artworks in items.items():\n            for artwork in artworks:'
HELPER_ART_WITH = "        for artwork_type, artworks in items.items():\n            if not isinstance(artworks, list):\n                continue  # TMDb mixes a scalar 'id' in with the artwork lists\n            for artwork in artworks:"


def helper_artwork_guard_edits():
    # get_art() is handed TMDb's whole "images" object and iterates every value,
    # but it carries a scalar alongside the lists. The TypeError aborts the item's
    # whole details fetch, so ratings never arrive and the row loads forever.
    yield HELPER_MAPPINGS, "replace", HELPER_ART_FIND, HELPER_ART_WITH

def helper_translated_genres_edits():
    yield HELPER_GENRES, "replace", GENRES_FIND, GENRES_WITH


MODULE_WINDOW = "resources/modules/jurialmunkey/window.py"

# xbmcgui.getCurrentWindowId() returns WINDOW_INVALID (9999) whenever the window
# history is empty, which is where a skin reload leaves it when the window that was
# active was one of the skin's own -- CApplicationSkinHandling::LoadSkin remembers the
# id, UnloadSkin deletes the custom windows and purges them from the history, and
# ActivateWindow() on the remembered id then finds nothing to activate and returns
# without pushing anything back. GetActiveWindow() answers WINDOW_INVALID from then on.
#
# That id is the one value get_current_window() can return that xbmcgui.Window()
# refuses: CGUIWindowManager::GetWindow() returns nullptr for 0 and WINDOW_INVALID
# before it even looks the id up, the constructor throws WindowException, and the SWIG
# wrapper writes "EXCEPTION: Window id does not exist" at LOGERROR on the way out. The
# except RuntimeError around each call swallows the exception but not the log line, and
# nothing in the loop clears the condition, so TMDb Helper's two 0.2s pollers spend two
# window property reads each per iteration writing ~20 errors a second until Kodi is
# killed.
#
# The same excludelist the dialog id is already filtered against is the fix: both
# xbmcgui calls answer WINDOW_INVALID for "nothing here", and only one of them was
# checked. 10000 is what every other fallback in this module uses, and it is where Kodi
# itself lands whenever it cannot restore a window.
#
# Window.IsVisible(id) is not the probe to use. It resolves to
# CGUIWindowManager::IsWindowActive(id, false), which is true when id matches
# GetActiveWindow() or sits in m_activeDialogs -- and both branches of
# get_current_window() return exactly one of those, WINDOW_INVALID included. It would be
# true for every value the function can produce, including the one that throws.
MODULE_FIND = """def get_current_window(get_dialog=True):
    dialog = xbmcgui.getCurrentWindowDialogId() if get_dialog else None
    return dialog if dialog not in DIALOG_ID_EXCLUDELIST else xbmcgui.getCurrentWindowId()
"""

MODULE_WITH = """def get_current_window(get_dialog=True):
    dialog = xbmcgui.getCurrentWindowDialogId() if get_dialog else None
    if dialog not in DIALOG_ID_EXCLUDELIST:
        return dialog
    window = xbmcgui.getCurrentWindowId()
    # Both calls answer WINDOW_INVALID when there is nothing to report, and asking
    # xbmcgui.Window() for that id logs an error every time. Fall back to home.
    return window if window not in DIALOG_ID_EXCLUDELIST else 10000
"""


def module_window_edits():
    yield MODULE_WINDOW, "replace", MODULE_FIND, MODULE_WITH


def build(tree, pid, upstream, absent, gen):
    edits = []
    for rel, kind, find, with_ in gen():
        with open(os.path.join(tree, rel), "rb") as fh:
            buf = fh.read()
        n = buf.count(find.encode("utf-8"))
        if n == 0:
            raise SystemExit("%s: anchor not found: %r" % (rel, find[:70]))
        edits.append({
            "file": rel, "kind": kind, "count": n,
            "contexts": patchlib.context_hashes(buf, find.encode("utf-8")),
            "find": find, "with": with_,
        })
        print("  %-32s %-8s x%-3d %s" % (rel.rsplit("/", 1)[-1], kind, n, find[:52].replace("\n", "\n")))
    return {"id": pid, "upstream": upstream, "absent": absent, "edits": edits}


TMDB = "python/lib/tmdbscraper/tmdb.py"

TITLE_FIND = "            'title': movie['title'],"
TITLE_WITH = "            'title': movie_fallback.get('title') or movie['title'],"

ART_FIND = "        available_art = _parse_artwork(movie, collection, self.urls, self.language)"
ART_WITH = "        available_art = _parse_artwork(movie, collection, self.urls, 'en')"


def english_title_edits():
    # _gather_details() already fetches the untranslated movie unconditionally, for
    # its artwork and as the plot fallback, so preferring its title costs no extra
    # request: with the scraper set to he-IL this gives English titles, Hebrew plots.
    yield TMDB, "replace", TITLE_FIND, TITLE_WITH
    # _build_image_list_with_fallback puts the scraper language first, so he-IL
    # would pick Hebrew posters. Artwork is chosen in English regardless of the
    # text language; the existing "any image" fallback still covers films with none.
    yield TMDB, "replace", ART_FIND, ART_WITH


IDAN_IPTV = "resources/lib/iptv.py"
IDAN_KAN = "resources/lib/kan.py"


def _crlf(*lines):
    """idanplus ships its python with CRLF endings and tab indentation. Spelling
    the endings out here is what keeps a patch drafted against an LF upstream
    from being written into one of these files."""
    return "".join(line + "\r\n" for line in lines)


IDAN_LOGO_FIND = _crlf(
    "\t\t\tif channel.get('my_image', '') == '':",
    "\t\t\t\ttvg_logo = 'special://home/addons/{0}/resources/images/{1}'"
    ".format(common.AddonID, channel['image'])",
)

IDAN_LOGO_WITH = _crlf(
    "\t\t\tif channel.get('my_image', '') == '':",
    "\t\t\t\timage = channel['image']",
    "\t\t\t\t# Every image in channels.json is an absolute url, and",
    "\t\t\t\t# GetChannelIconFullPath() already hands it to Kodi as it stands.",
    "\t\t\t\t# Only the m3u prefixed the add-on's own images directory onto it.",
    "\t\t\t\ttvg_logo = image if image.startswith('http://') or image.startswith('https://')"
    " else 'special://home/addons/{0}/resources/images/{1}'.format(common.AddonID, image)",
)

IDAN_IMAGE_FIND = _crlf(
    "def GetImageLink(imageUrl, imageName):",
    "    i = imageUrl.find('?')",
)

IDAN_IMAGE_WITH = _crlf(
    "def GetImageLink(imageUrl, imageName):",
    "    # Several callers hand the url straight out of the page or the mobile api",
    "    # with the Hebrew path still raw, and kan answers 404 to those. Quoting here",
    "    # covers every caller at once; quoteNonASCII leaves ascii alone, so it never",
    "    # double-encodes and is a no-op for the callers that already quote.",
    "    imageUrl = common.quoteNonASCII(imageUrl)",
    "    i = imageUrl.find('?')",
)

IDAN_RADIO_FIND = _crlf(
    "                image = serie['media_group'][0]['media_item'][2]['src']",
)

IDAN_RADIO_WITH = _crlf(
    "                image = common.quoteNonASCII("
    "serie['media_group'][0]['media_item'][2]['src'])",
)


def idan_tvg_logo_edits():
    # The my_image branch below is left alone: main.ChangeChannelLogo() stores
    # whatever SaveLogo() returns, which is a bare filename, never a url.
    yield IDAN_IPTV, "replace", IDAN_LOGO_FIND, IDAN_LOGO_WITH


def idan_image_url_edits():
    # GetImageLink is the funnel: fifteen of the image call sites in kan.py go
    # through it, and four of them -- kids episodes, radio series from html,
    # podcasts and podcast episodes -- pass the url unquoted.
    yield IDAN_KAN, "replace", IDAN_IMAGE_FIND, IDAN_IMAGE_WITH
    # Two lists built from the mobile api -- radio series and podcasts -- are the
    # sites that never reach GetImageLink: each slices the query off the src and
    # hands the rest straight to Kodi. media_item[2] is the logo image, and kan
    # names those in Hebrew.
    yield IDAN_KAN, "replace", IDAN_RADIO_FIND, IDAN_RADIO_WITH


TARGETS = {
    SKIN: (
        ("001-text-title.json", "text-title", "PR to be offered to jurialmunkey",
         [[INFO, SETTING], [SKINSET, SETTING]], title_edits),
        ("002-font.json", "font", "jurialmunkey/resource.font.robotocjksc#3",
         [[FONTXML, FONT_ADDON], ["addon.xml", FONT_ADDON]], font_edits),
        ("004-meta-skeleton.json", "meta-skeleton", "feature request to be offered",
         [[EXPRXML, "Exp_TMDbHelper_IsSkeleton"], [EXPRXML, "Exp_TMDbHelper_IsStaleRatings"],
          [INFO, "Info_Meta_Skeleton"], [INFO, 'name="stale"'],
          [SKINSET, SKELETON_SETTING], [SKINSET, SKELETON_DEBUG]], skeleton_edits),
    ),
    SCRAPER: (
        ("001-english-title.json", "english-title", "PR to be offered to xbmc",
         [[TMDB, "movie_fallback.get('title')"], [TMDB, "self.urls, 'en')"]], english_title_edits),
    ),
    IDAN: (
        ("001-tvg-logo.json", "tvg-logo", "https://github.com/Fishenzon/repo/issues/310",
         [[IDAN_IPTV, "image.startswith('http://')"]], idan_tvg_logo_edits),
        ("002-kan-image-url.json", "kan-image-url",
         "https://github.com/Fishenzon/repo/issues/311",
         [[IDAN_KAN, "imageUrl = common.quoteNonASCII(imageUrl)"],
          [IDAN_KAN, "common.quoteNonASCII(serie['media_group']"]], idan_image_url_edits),
    ),
    MODULE: (
        ("001-window-id-loop.json", "window-id-loop",
         "https://github.com/jurialmunkey/script.module.jurialmunkey/issues/11",
         [[MODULE_WINDOW, "window = xbmcgui.getCurrentWindowId()"]], module_window_edits),
    ),
    HELPER: (
        ("001-english-metadata.json", "english-metadata",
         "jurialmunkey/plugin.video.themoviedb.helper#707, #1181",
         [[HELPER_TMDBAPI, "        return 'en'"]], helper_english_metadata_edits),
        ("002-translated-plot.json", "translated-plot", "PR to be offered to jurialmunkey",
         [[HELPER_MAPPINGS, "set_translated_plot"], [HELPER_LISTITEM, "self.infolabels['plot'] = details"]],
         helper_translated_plot_edits),
        ("003-translated-genres.json", "translated-genres", "PR to be offered to jurialmunkey",
         [[HELPER_GENRES, "get_request_url"]], helper_translated_genres_edits),
    ),
}


def main(target, tree, patchdir):
    outdir = os.path.join(patchdir, target)
    os.makedirs(outdir, exist_ok=True)
    for name, pid, upstream, absent, gen in TARGETS[target]:
        print("%s:" % name[:-len(".json")])
        desc = build(tree, pid, upstream, absent, gen)
        with open(os.path.join(outdir, name), "wb") as fh:
            fh.write((json.dumps(desc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        print("wrote %s/%s" % (target, name))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])

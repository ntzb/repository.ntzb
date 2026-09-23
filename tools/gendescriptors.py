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


def title_edits(tree):
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


def genre_edits(tree):
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
    'String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override_tvshow]] + '
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


def skeleton_edits(tree):
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


def font_edits(tree):
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


def helper_english_metadata_edits(tree):
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


def helper_translated_plot_edits(tree):
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


def helper_artwork_guard_edits(tree):
    # get_art() is handed TMDb's whole "images" object and iterates every value,
    # but it carries a scalar alongside the lists. The TypeError aborts the item's
    # whole details fetch, so ratings never arrive and the row loads forever.
    yield HELPER_MAPPINGS, "replace", HELPER_ART_FIND, HELPER_ART_WITH

def helper_translated_genres_edits(tree):
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


def module_window_edits(tree):
    yield MODULE_WINDOW, "replace", MODULE_FIND, MODULE_WITH

LISTSXML = "1080i/Includes_Lists.xml"
LAYOUTSXML = "1080i/Includes_Layouts.xml"
WIDGETSXML = "1080i/Includes_Widgets.xml"
ACTIONSXML = "1080i/Includes_Actions.xml"
LABELSXML = "1080i/Includes_Labels.xml"
IMAGESXML = "1080i/Includes_Images.xml"
GENROW = "shortcuts/generator/data/setup/widgets_include_row.xml"
GENWALL = "shortcuts/generator/data/setup/widgets_include_wall.xml"

# A widget style is a value stored on the shortcut node, mapped to a row include by one
# generator rule, named in two label variables and one image variable, and offered in one
# do_edit option list. That is exactly the set of places jurialmunkey touched to add
# Placard in 59d791a, and it is the set touched here -- plus the row include itself, the
# layout it draws with, and the busy placeholder the widget stands up while it loads.
#
# One entry per style offered: the value stored on the shortcut node, the option name in
# the picker, the base row and layout it copies, the art variable spelled into the row,
# and any row parameters overridden on the copy.
#
# A widget style is a value on the shortcut node, mapped to a row include by one generator
# rule, named in two label variables and one image variable, and offered in one do_edit
# option list. That is exactly the set of places jurialmunkey touched to add Placard in
# 59d791a, plus the row include itself, the layout it draws with, and the busy placeholder
# the widget stands up while it loads.
#
# The five-per-row variant is the same layout at 360 pitch instead of 450, which is 1800
# divided five ways rather than four; every stock pitch in Includes_Constants.xml is 1800
# over a whole number and this keeps that. item_h follows item_w at 16:9, the diffuse mask
# moves to the nearest stock landscape size, and itemlayout_h is deliberately left alone
# so the two label lines keep exactly the room they have at four per row.
#
# Measured against this library before it was built: at 320px roughly one line in five is
# too long to fit, against one in fourteen at 410px. Rearranging the two lines does not
# recover it -- the long show names and the long episode titles are not the same shows, so
# moving the episode number up trades two broken first lines for one saved second line.
_STYLES = (
    ("LandscapeShowArt", "Landscape with show title and art",
     "Landscape", "Layout_Landscape", "Image_Landscape_ShowArt", {}),
    ("LandscapeShowArtSmall", "Landscape with show title and art, five per row",
     "Landscape", None, "Image_Landscape_ShowArt",
     {"item_w": "320", "item_h": "180", "itemlayout_w": "360"}),
)

# The diffuse mask is sized per shape in the stock media, so the narrower cell takes the
# nearest one rather than stretching the 410-wide mask over a 320-wide image.
SMALL_DIFFUSE = "diffuse/landscape_w356_h200.png"
CONTROL_LINE = '        <param name="control">fixedlist</param>\n'
DIFFUSE_LINE = '        <param name="diffuse">%s</param>\n'

_ROW_LAYOUTS = {"Board": ("Layout_Landscape",), "Placard": ("Layout_Placard", "Layout_Flyer")}


def _styles():
    """(style value, option name, base) for every style offered, in menu order."""
    for style, name, base, _, _, _ in _STYLES:
        yield style, name, base


def _include_block(tree, rel, name):
    """The verbatim text of one <include name="..."> ... </include> from the tree.

    The copied layouts and rows are upstream's own, with include names and one label
    control changed. Lifting them out of the pristine tree at generation time is what
    keeps them upstream's own: a hand transcription is one typo away from a widget that
    looks almost right.
    """
    with open(os.path.join(tree, rel), "rb") as fh:
        buf = fh.read().decode("utf-8")
    head = '    <include name="%s">' % name
    i = buf.index(head)
    j = buf.index("\n    </include>\n", i) + len("\n    </include>\n")
    return buf[i:j]


def _swap(text, find, with_, count):
    if text.count(find) != count:
        raise SystemExit("derive: %r expected %d, found %d" % (find[:60], count, text.count(find)))
    return text.replace(find, with_)


def _span(text, start, end):
    """The text from `start` up to the following `end`."""
    i = text.index(start)
    return text[i:text.index(end, i)]


# Upstream stacks one control in the 80px label group: a textbox when use_label is false,
# a plain label when it is true. Both render the whole label as one run of text, and a
# textbox wraps rather than truncates, so a long episode name flowed onto a third line and
# was clipped with nothing to show for it. Two labels of their own give the show name a
# line and the episode name a line, and a label with a width truncates itself.
#
# scroll is tied to $PARAM[selected], Kodi's focusedlayout flag: the focused row scrolls
# the whole episode name past, every other row truncates. Upstream's Layout_Labels is
# never passed selected -- Layout_Landscape and its siblings keep it to themselves for the
# text colour -- so the copied layouts add the pass-through.
TWO_LABELS = """                    <control type="group">
                        <top>$PARAM[textbox_offset_y]</top>
                        <visible>![$PARAM[include_detailed_labels]]</visible>

                        <control type="label">
                            <width>$PARAM[item_w]</width>
                            <height>33</height>
                            <font>font_mini</font>
                            <label>$VAR[Label_ShowTitle_Upper]</label>
                            <align>left</align>
                            <include condition="$PARAM[selected]">Color_SelectedText</include>
                            <textcolor>main_fg_70</textcolor>
                        </control>

                        <control type="label">
                            <top>33</top>
                            <width>$PARAM[item_w]</width>
                            <height>33</height>
                            <font>font_mini</font>
                            <label>$VAR[Label_ShowTitle_Lower]</label>
                            <align>left</align>
                            <scroll>$PARAM[selected]</scroll>
                            <include condition="$PARAM[selected]">Color_SelectedText</include>
                            <textcolor>main_fg_70</textcolor>
                        </control>
                    </control>

"""

# Two variables rather than one so each line is measured and truncated on its own.
#
# The lower line is the episode number and the episode name, and the number carries the
# line on its own when there is no name to add. "No name" is two cases. An episode TMDb
# has no title for can arrive with the field empty, and it can arrive holding TMDb's own
# placeholder -- the string "Episode 7" -- because TMDb used to synthesise that for
# untitled episodes and still serves it on records scraped while it did. Neither says
# anything the number has not already said, so both collapse to "1x07". A show that
# genuinely titles its episodes "Episode 7" loses nothing worth keeping either.
#
# The number itself is $VAR[Label_Plot_Episode_Number], upstream's own formatter, which
# already zero-pads below ten and answers empty for anything that is not an episode.
#
# Anything that is not an episode -- a movie, a show, a PVR channel -- puts its label on
# the upper line and leaves the lower one empty, so a mixed widget looks as it always did.
_IS_SHOW_ITEM = ("!String.IsEmpty(ListItem.TVShowTitle) + "
                 "!String.IsEqual(ListItem.DBType,tvshow)")
_HAS_NUMBER = "!String.IsEmpty(ListItem.Season) + !String.IsEmpty(ListItem.Episode)"
_HAS_NAME = "!String.IsEmpty(ListItem.Title) + !String.StartsWith(ListItem.Title,Episode )"

SHOWTITLE_LABEL_VARS = """    <variable name="Label_ShowTitle_Upper">
        <value condition="%(show)s">$INFO[ListItem.TVShowTitle,,:]</value>
        <value>$INFO[ListItem.Label]</value>
    </variable>

    <variable name="Label_ShowTitle_Lower">
        <value condition="%(show)s + %(num)s + %(name)s">$VAR[Label_Plot_Episode_Number]$INFO[ListItem.Title, - ,]</value>
        <value condition="%(show)s + %(num)s">$VAR[Label_Plot_Episode_Number]</value>
        <value condition="%(show)s + %(name)s">$INFO[ListItem.Title]</value>
    </variable>

""" % {"show": _IS_SHOW_ITEM, "num": _HAS_NUMBER, "name": _HAS_NAME}

# tvshow.landscape first, and deliberately. metadatautils copies the show's landscape down
# onto the unprefixed key when the episode has none, so on these items 'landscape' is
# usually the same picture -- but only usually, and a library episode carrying its own
# landscape would answer with the episode's. season.landscape is a different picture again:
# on this library The White Lotus has a fanart.tv season card there, not the show's wide
# art. The episode still, which is what Image_Landscape prefers for an episode, is the one
# thing this variable must never return, so it is not in the chain at all -- the fallback
# is reached only by a show with no landscape and no fanart anywhere.
SHOWART_IMAGE_VAR = """    <variable name="Image_Landscape_ShowArt">
        <value condition="!String.IsEmpty(ListItem.Art(tvshow.landscape))">$INFO[ListItem.Art(tvshow.landscape)]</value>
        <value condition="!String.IsEmpty(ListItem.Art(landscape))">$INFO[ListItem.Art(landscape)]</value>
        <value condition="!String.IsEmpty(ListItem.Art(season.landscape))">$INFO[ListItem.Art(season.landscape)]</value>
        <value condition="!String.IsEmpty(ListItem.Art(tvshow.fanart))">$INFO[ListItem.Art(tvshow.fanart)]</value>
        <value condition="!String.IsEmpty(ListItem.Art(fanart))">$INFO[ListItem.Art(fanart)]</value>
        <value>$VAR[Image_Landscape]</value>
    </variable>

"""

LABEL_STYLE_ANCHOR = '    <variable name="Label_Widget_Style">\n'
LABEL_SHORTCUT_STYLE_ANCHOR = '    <variable name="Label_Shortcut_Widget_Style">\n'
IMAGE_STYLE_ANCHOR = '    <variable name="Image_Widget_Style">\n'

_STYLE_LABEL = '        <value condition="String.IsEqual(%s.Property(widget_style),%s)">%s</value>\n'
_STYLE_IMAGE = ('        <value condition="String.IsEqual(ListItem.Property(widget_style),%s)">'
                'special://skin/extras/icons/%s.png</value>\n')

# The icon beside the style name in the picker. Upstream has one per shape, so each new
# style borrows the one its base already uses rather than inventing artwork.
_STYLE_ICONS = {"Landscape": "view-landscape", "Board": "window-maximize-regular",
                "Poster": "view-poster", "Flyer": "window-maximize-regular",
                "Square": "view-square", "Placard": "window-maximize-regular"}


def _style_labels(listitem):
    return "".join(_STYLE_LABEL % (listitem, style, name) for style, name, _ in _styles())


def _style_images():
    return "".join(_STYLE_IMAGE % (style, _STYLE_ICONS[base]) for style, _, base in _styles())


# Appended to the pairs rather than put in front of them: do_edit preselects on the stored
# value rather than on position, and a user who has picked none of these should still land
# on the list they know.
WIDGETSTYLE_TAIL = "&amp;&amp;$LOCALIZE[736]&amp;&amp;True)</value>"
WIDGETSTYLE_PAIRS = "".join(
    "&amp;%s=%s" % (name, style) for style, name, _ in _styles()) + WIDGETSTYLE_TAIL

# The catch-all is the last rule in both files and is what upstream inserts ahead of, so
# anchoring on it puts the new rules where a merged upstream would have put them.
GENRULE_ANCHOR = ("        <rule>\n"
                  "            <condition>True</condition>\n"
                  "            <value>List_Landscape_Row</value>\n"
                  "        </rule>\n")

GENRULES = "".join(
    "        <rule>\n"
    "            <condition>{item_widget_style}==%s</condition>\n"
    "            <value>List_%s_Row</value>\n"
    "        </rule>\n" % (style, style)
    for style, _, _ in _styles()) + GENRULE_ANCHOR

# _Widget_Row stands up Widget_Busy_BlankItems__$PARAM[include] while the widget loads, so
# a row include with no placeholder of that name leaves an unresolved include in the log
# and an empty row on screen. Every new row keeps its base's shape, so each borrows that
# base's placeholder whole rather than restating its bars.
BUSY_ANCHOR = '    <include name="Widget_Busy_BlankItems__List_Landscape_Row">\n'

BUSY = "".join(
    '    <include name="Widget_Busy_BlankItems__List_%s_Row">\n'
    "        <include>Widget_Busy_BlankItems__List_%s_Row</include>\n"
    "    </include>\n" % (style, base)
    for style, _, base in _styles()) + BUSY_ANCHOR

LAYOUT_ANCHOR = '    <include name="Layout_Landscape">\n'
ROW_ANCHOR = '    <include name="List_Landscape_Row">\n'

LABELS_BRANCH_HEAD = ('                    <include content="Object_Control" '
                      'condition="![$PARAM[include_detailed_labels]] + ![$PARAM[use_label]]">')
LABELS_BRANCH_END = '                    <include content="Object_InfoCircle_Text_Top"'


def _labels_copy(tree):
    """Layout_Labels with its single label control replaced by two stacked ones.

    Layout_Labels hardcodes the item label in every branch, so there is no parameter to
    pass and a copy is the only additive way in. $VAR resolves per item inside an
    itemlayout, which is how upstream's own $VAR[Label_Landscape_Lower] already works.
    """
    labels = _include_block(tree, LAYOUTSXML, "Layout_Labels")
    labels = _swap(labels, '<include name="Layout_Labels">',
                   '<include name="Layout_Labels_ShowTitle">', 1)
    # The labels need a width to truncate against. Upstream sizes the group off left/right
    # and never needs item_w here, so the copy declares it with the landscape cell width
    # as the default for any caller that forgets.
    labels = _swap(labels, '        <param name="textbox_offset_y">7</param>\n',
                   '        <param name="textbox_offset_y">7</param>\n'
                   '        <param name="item_w">410</param>\n', 1)
    # Both Object_Control branches go, from the first of them to the detailed heading that
    # follows. The detailed branch below it is left exactly as upstream wrote it.
    old = _span(labels, LABELS_BRANCH_HEAD, LABELS_BRANCH_END)
    if old.count('<include content="Object_Control"') != 2:
        raise SystemExit("derive: Layout_Labels no longer has two label branches")
    return labels.replace(old, TWO_LABELS)


def nextup_edits(tree):
    layouts = [_labels_copy(tree)]
    for _, _, _, layout, _, _ in _STYLES:
        if not layout:
            continue
        text = _include_block(tree, LAYOUTSXML, layout)
        text = _swap(text, '<include name="%s">' % layout,
                     '<include name="%s_ShowTitle">' % layout, 1)
        text = _swap(text, '<include content="Layout_Labels"',
                     '<include content="Layout_Labels_ShowTitle"', 1)
        # selected and item_w have to reach the labels; upstream's call site passes
        # neither, because upstream's labels have no use for either.
        text = _swap(text, '                    <param name="item_h">$PARAM[item_h]</param>\n',
                     '                    <param name="item_h">$PARAM[item_h]</param>\n'
                     '                    <param name="item_w">$PARAM[item_w]</param>\n'
                     '                    <param name="selected">$PARAM[selected]</param>\n', 1)
        layouts.append(text)

    rows = []
    for style, _, base, _, art, overrides in _STYLES:
        row = _include_block(tree, LISTSXML, "List_%s_Row" % base)
        row = _swap(row, '<include name="List_%s_Row">' % base,
                    '<include name="List_%s_Row">' % style, 1)
        for layout in _ROW_LAYOUTS.get(base, ("Layout_%s" % base,)):
            row = _swap(row, '<param name="itemlayout_include">%s</param>' % layout,
                        '<param name="itemlayout_include">%s_ShowTitle</param>' % layout, 1)
        # Spelled out rather than left to $PARAM[icon] falling through to the layout
        # default: whether an empty parameter reaches the layout or the default does is
        # Kodi's business, and no row should be asking the question.
        row = _swap(row, '<param name="icon">$PARAM[icon]</param>',
                    '<param name="icon">$VAR[%s]</param>' % art, 1)
        for name, value in sorted(overrides.items()):
            old = '<param name="%s">view_%s_%s</param>' % (
                name, "poster" if name == "itemlayout_h" else base.lower(), name)
            row = _swap(row, old, '<param name="%s">%s</param>' % (name, value), 1)
        if overrides:
            row = _swap(row, CONTROL_LINE,
                        DIFFUSE_LINE % SMALL_DIFFUSE + CONTROL_LINE, 1)
        rows.append(row)

    yield LAYOUTSXML, "insert", LAYOUT_ANCHOR, "\n".join(layouts) + "\n" + LAYOUT_ANCHOR
    yield LISTSXML, "insert", ROW_ANCHOR, "\n".join(rows) + "\n" + ROW_ANCHOR
    yield WIDGETSXML, "insert", BUSY_ANCHOR, BUSY
    yield LABELSXML, "insert", LABEL_STYLE_ANCHOR, \
        SHOWTITLE_LABEL_VARS + LABEL_STYLE_ANCHOR + _style_labels("ListItem")
    yield LABELSXML, "insert", LABEL_SHORTCUT_STYLE_ANCHOR, \
        LABEL_SHORTCUT_STYLE_ANCHOR + _style_labels("Container(22001).ListItem")
    yield IMAGESXML, "insert", IMAGE_STYLE_ANCHOR, SHOWART_IMAGE_VAR + IMAGE_STYLE_ANCHOR + \
        _style_images()
    yield ACTIONSXML, "insert", WIDGETSTYLE_TAIL, WIDGETSTYLE_PAIRS
    yield GENROW, "insert", GENRULE_ANCHOR, GENRULES
    yield GENWALL, "insert", GENRULE_ANCHOR, GENRULES


def build(tree, pid, upstream, absent, gen):
    edits = []
    for rel, kind, find, with_ in gen(tree):
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


def english_title_edits(tree):
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


def idan_tvg_logo_edits(tree):
    # The my_image branch below is left alone: main.ChangeChannelLogo() stores
    # whatever SaveLogo() returns, which is a bare filename, never a url.
    yield IDAN_IPTV, "replace", IDAN_LOGO_FIND, IDAN_LOGO_WITH


def idan_image_url_edits(tree):
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
        ("005-nextup-widget-styles.json", "nextup-widget-styles", "feature request to be offered",
         [[LAYOUTSXML, "Layout_Labels_ShowTitle"], [LAYOUTSXML, "Layout_Landscape_ShowTitle"],
          [LISTSXML, "List_LandscapeShowArt_Row"],
          [WIDGETSXML, "Widget_Busy_BlankItems__List_LandscapeShowArt_Row"],
          [LABELSXML, "Label_ShowTitle_Upper"], [LABELSXML, "Label_ShowTitle_Lower"],
          [IMAGESXML, "Image_Landscape_ShowArt"], [ACTIONSXML, "LandscapeShowArt"],
          [GENROW, "LandscapeShowArt"], [GENWALL, "LandscapeShowArt"]],
         nextup_edits),
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

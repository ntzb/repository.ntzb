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
    "Action & Adventure", "Sci-Fi & Fantasy", "War & Politics", "Science Fiction", "TV Movie",
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family",
    "Fantasy", "History", "Horror", "Kids", "Music", "Mystery", "News", "Reality", "Romance",
    "Soap", "Talk", "Thriller", "War", "Western",
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

# TMDb Helper already says when it is working: lib/monitor/listitemtools.py sets
# IsUpdating around the blocking details build ("Set a property for skins to check
# if item details are updating") and lib/monitor/listitemfinaliser.py sets
# IsUpdatingRatings around the ratings thread, both under
# jurialmunkey.window.WindowPropertySetter.get_property's prefix="TMDbHelper".
# Comparing base_tmdb_id against ListItem.UniqueID(tmdb) would not do: the images
# monitor copies base_* straight off the focused listitem each poll, so it follows
# the cursor, not the fetch, and matches again long before the ratings land.
SKELETON_EXPR_ANCHOR = (
    '    <expression name="Exp_TMDbHelper_IsCrop">'
    '[Skin.HasSetting(TMDbHelper.EnableCrop)]</expression>\n')

SKELETON_EXPR = SKELETON_EXPR_ANCHOR + (
    '    <expression name="Exp_TMDbHelper_IsSkeleton">[$EXP[Exp_TMDbHelper_IsData] + '
    '!Skin.HasSetting(%s) + '
    '[!String.IsEmpty(Window(Home).Property(TMDbHelper.IsUpdating)) | '
    '!String.IsEmpty(Window(Home).Property(TMDbHelper.IsUpdatingRatings))]]</expression>\n'
    % SKELETON_SETTING)

# Everything the TMDbHelper-fed half of the meta row can draw. All of it empty is
# the only state the placeholder stands in for: the monitor overwrites properties
# rather than clearing them first, so when a value is on screen during a fetch it
# is the previous item's, and a placeholder beside it would be a second answer to
# the same question.
SKELETON_PROPS = (
    "MetaCritic_Rating", "RottenTomatoes_UserMeter", "RottenTomatoes_Rating", "Trakt_Rating",
    "IMDb_Rating", "TMDb_Rating", "MDBList_Rating", "Letterboxd_Rating", "MyAnimeList_Rating",
    "Status", "Oscar_Wins",
)

SKELETON_EMPTY = " + ".join(
    "String.IsEmpty(Window(Home).Property(TMDbHelper.$PARAM[service].%s))" % p
    for p in SKELETON_PROPS)

SKELETON_DEF_ANCHOR = '    <include name="Info_Meta_Item_Row">'

# Borrowed wholesale from the skin's own placeholder, Widget_Busy_BlankItem /
# Widget_Busy in Includes_Widgets.xml: a 24px common/widget_text.png bar at
# main_fg_12, faded in by a Visible animation with reversible="false" so that
# hiding it is instant rather than a reversed fade. Only the timings differ --
# 400ms against the widgets' 200ms, because the service polls every 200ms
# (POLL_MIN_INCREMENT) and a cursor step that resolves inside one poll must not
# blink. Held down the flags stay set and it simply stays up. The pulse is the
# nearest thing Kodi has to a shimmer: no skin sweeps a gradient, because groups
# do not clip their children.
SKELETON_DEF = """    <include name="Info_Meta_Skeleton">
        <param name="service">ListItem</param>
        <param name="width">96</param>
        <definition>
            <control type="group" description="Placeholder held until TMDbHelper has answered for this item">
                <width>$PARAM[width]</width>
                <height>40</height>
                <visible>$PARAM[visible]</visible>
                <visible>$EXP[Exp_TMDbHelper_IsSkeleton]</visible>
                <visible>%s</visible>
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

""" % SKELETON_EMPTY + SKELETON_DEF_ANCHOR

SKELETON_ROW_ANCHOR = "                    <!-- Ratings -->"

_SKELETON_ITEM = """                    <include content="Info_Meta_Skeleton" condition="$EXP[Exp_TMDbHelper_IsData]">
                        <param name="visible">[%s] + !String.IsEmpty(Skin.String(CustomRating.%s.Item%02d))</param>
                        <param name="service">$PARAM[service]</param>
                    </include>
"""

# One pill per rating slot the user has actually configured, mirroring the six
# Info_Meta_Ratings instances it sits above, so the placeholder is the shape of
# what is coming rather than a guess.
_SKELETON_DBTYPES = (
    ("Movies", "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,movie) | $PARAM[override_movie]"),
    ("TVShows", "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,tvshow) | "
                "String.IsEqual($PARAM[container]$PARAM[listitem].DBType,season) | $PARAM[override_tvshow]"),
)

SKELETON_ROW = ("                    <!-- Ratings Placeholder -->\n"
                + "".join(_SKELETON_ITEM % (cond, content, n)
                          for content, cond in _SKELETON_DBTYPES for n in (1, 2, 3))
                + "\n" + SKELETON_ROW_ANCHOR)

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
""" % (SKELETON_SETTING, SKELETON_SETTING)


def skeleton_edits():
    yield EXPRXML, "insert", SKELETON_EXPR_ANCHOR, SKELETON_EXPR
    yield INFO, "insert", SKELETON_DEF_ANCHOR, SKELETON_DEF
    yield INFO, "insert", SKELETON_ROW_ANCHOR, SKELETON_ROW
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


def helper_translated_genres_edits():
    yield HELPER_GENRES, "replace", GENRES_FIND, GENRES_WITH


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


TARGETS = {
    SKIN: (
        ("001-text-title.json", "text-title", "PR to be offered to jurialmunkey",
         [[INFO, SETTING], [SKINSET, SETTING]], title_edits),
        ("002-font.json", "font", "jurialmunkey/resource.font.robotocjksc#3",
         [[FONTXML, FONT_ADDON], ["addon.xml", FONT_ADDON]], font_edits),
        ("003-genre.json", "genre-in-infoline", "feature request to be offered",
         [[INFO, "<!-- Genre -->"], [INFO, GENRE_SETTING], [SKINSET, GENRE_SETTING]], genre_edits),
        ("004-meta-skeleton.json", "meta-skeleton", "feature request to be offered",
         [[EXPRXML, "Exp_TMDbHelper_IsSkeleton"], [INFO, "Info_Meta_Skeleton"],
          [SKINSET, SKELETON_SETTING]], skeleton_edits),
    ),
    SCRAPER: (
        ("001-english-title.json", "english-title", "PR to be offered to xbmc",
         [[TMDB, "movie_fallback.get('title')"], [TMDB, "self.urls, 'en')"]], english_title_edits),
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

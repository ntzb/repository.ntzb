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

SETTING = "View.DisableClearlogoTitle"
FONT_ADDON = "resource.font.af3hebrew"
INFO = "1080i/Includes_Info.xml"
SKINSET = "1080i/Includes_SkinSettings.xml"
FONTXML = "1080i/Font.xml"

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


def font_edits():
    for weight in ("Regular", "Bold"):
        f = "resource://resource.font.robotocjksc/Inter-Unicode-%s.ttf" % weight
        yield FONTXML, "replace", f, f.replace("resource.font.robotocjksc", FONT_ADDON)
    yield "addon.xml", "insert", "    </requires>", \
        '        <import addon="%s" version="1.1.0" />\n    </requires>' % FONT_ADDON


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
    ),
    SCRAPER: (
        ("001-english-title.json", "english-title", "PR to be offered to xbmc",
         [[TMDB, "movie_fallback.get('title')"], [TMDB, "self.urls, 'en')"]], english_title_edits),
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

# repository.ntzb

A personal Kodi add-on repository serving patched builds of **Arctic Fuse 3**, **TMDb Helper**
and Kodi's **TMDb movie scraper**, rebuilt automatically from each upstream release.

## What is patched

### skin.arctic.fuse.3

| # | change | upstream |
|---|---|---|
| 001 | a skin setting to show titles as text instead of clearlogo art, in library lists and the video OSD | PR to be offered |
| 002 | Hebrew final forms restored to the Unicode fontset | [robotocjksc#3](https://github.com/jurialmunkey/resource.font.robotocjksc/issues/3), [rsms/inter#903](https://github.com/rsms/inter/issues/903) |
| 003 | the first genre in the info line, in place of the age rating, behind a skin setting | feature request to be offered |
| 004 | a placeholder in the meta row while TMDb Helper is still fetching, behind a skin setting | feature request to be offered |

Patch 004 exists because the ratings, status and awards in the info row come from TMDb Helper's
service monitor, which answers a focus change some way after the cursor has moved: until it does,
the row is blank. The monitor already says when it is working — `TMDbHelper.IsUpdating` around the
blocking details build and `TMDbHelper.IsUpdatingRatings` around the ratings thread — so the patch
fills the gap with the skin's own `Widget_Busy_BlankItem` placeholder bar, one per rating slot the
user has configured, faded in after 400ms so a single step of the cursor never flashes it. It shows
only when the row is genuinely empty: the monitor overwrites properties rather than clearing them,
so a value on screen mid-fetch is the previous item's, and a placeholder beside it would be a second
answer to the same question.

Patch 002 exists because `resource.font.robotocjksc`'s `Inter-Unicode` fonts have no glyph for
U+05DA ך, U+05DD ם or U+05E5 ץ, so every Hebrew word ending in kaf, mem or tsadi loses its last
letter. The fonts are Inter 4.000 merged with DejaVu Sans 2.30 keyed on glyph name; Inter ships six
glyphs misnamed `uni05DA`, `uni05DD`, `uni05E5`, `uniFB47`, `uni25CE`, `uni200D` that are really
IPA letters, so the merge dropped the DejaVu originals and never mapped them. This repo ships
`resource.font.af3hebrew` with those six restored from the original donor, and repoints the skin's
fontset at it.

### metadata.themoviedb.org.python.ntzb

| # | change | upstream |
|---|---|---|
| 001 | the English title, whatever language the rest of the metadata is scraped in | PR to be offered |

The stock TMDb scraper returns the title in whichever language it is set to, so a Hebrew library
also gets Hebrew titles. It already fetches the untranslated movie a second time — for artwork, and
as the fallback for an empty plot — so preferring that copy's title costs no extra API call:

```diff
-            'title': movie['title'],
+            'title': movie_fallback.get('title') or movie['title'],
```

Set the scraper's language to `he-IL` and the result is English titles with Hebrew plots.

It is published under its own add-on id, so it installs beside the stock scraper instead of
fighting it for updates. Per movie source: context menu → **Change content** → **Choose information
provider** → *The Movie Database Python (ntzb)*, then **Settings** → **Preferred Language** `he-IL`,
with **Keep Original Title** off. Kodi then offers to refresh every item in the path; that rewrites
the scraped fields only — watched state and resume points hang off the file, not off the scraped
record, so they survive.

### plugin.video.themoviedb.helper

| # | change | upstream |
|---|--------|----------|
| 001 | every TMDb request made in English, whatever the add-on's language is set to | [#707](https://github.com/jurialmunkey/plugin.video.themoviedb.helper/issues/707), [#1181](https://github.com/jurialmunkey/plugin.video.themoviedb.helper/issues/1181) |
| 002 | the plot in the add-on's language, from the translations the details call already carries | PR to be offered |
| 003 | genre names in the add-on's language | PR to be offered |

**Set the add-on's language to Hebrew and leave it there.** It no longer means "scrape in
Hebrew"; it means *the plot and the genres in Hebrew, and the region Israeli*. Everything
else — titles, posters, cast, crew, studios, related titles — comes back English.

TMDb has one language parameter and it drives everything: titles, plots, `poster_path`,
cast and crew names, studios and genre names all come back in it, and
[#707](https://github.com/jurialmunkey/plugin.video.themoviedb.helper/issues/707) asked for
a split and was closed as impossible. An earlier version of this fork asked TMDb in Hebrew
and patched fields back to English one at a time; that lost, because `poster_path` on the
item is localised too and `include_image_language` only filters the separate `images`
array, so lists and *related movies* kept their Hebrew posters however many fields were
patched.

So it is inverted. Every request goes out in English, and the two things the user wants in
Hebrew are put back from data the add-on is already holding. One property is the whole of
the first half — the add-on derives the request language, the artwork and video language
preferences and the art tables' language lookup from it:

```diff
     def iso_language(self):
-        return self.language[:2]
+        return 'en'
```

`iso_country` is deliberately left alone, so the language setting still reads `he-IL`
everywhere else: requests go out as `en-IL`, and certifications and watch providers are
still chosen for Israel.

The plot rides along on the details call every uncached list item already makes, because
`append_to_response=translations` is fetched unconditionally — that is how the add-on's
English plot fallback works. Swapping it in at map time writes it straight into the cached
row, so the per-item cost is zero on every later read:

```diff
+        self.item = self.set_translated_plot(self.item)
```

One more line is needed for lists. `set_details` merges the cached details *under* the
item mapped from the list response, so the list's own plot would outrank the translated
one; title and tvshowtitle are already exempted there, and plot joins them.

Genres are not in the translations payload, and they are not taken from the item either:
both the list mapper's `genre_ids` and the details mapper's `genres` array are reduced to
ids and looked up in a single id→name map, which the add-on fetches from
`/genre/movie/list` and `/genre/tv/list` and caches in its `genres` table for thirty days.
Asking for *that* map in the add-on's own language is the whole of "genres in Hebrew" —
two requests a month, nothing per item:

```diff
-            genres = self.tmdb_api.get_response_json('genre', tmdb_type, 'list') or {}
+            requrl = self.tmdb_api.get_request_url('genre', tmdb_type, 'list', language=self.tmdb_api.language)
+            genres = self.tmdb_api.get_api_request_json(requrl) or {}
```

The url is built the way `get_response_json` builds it because
`configure_request_kwargs` overwrites `language` unconditionally and would discard a
keyword.

No extra request per item, in any of the three. The response for a list item — the
`basic` cache level — is within half a percent of what it was. A details lookup grows
3–17% (11–36 KB on a 200–400 KB response), and all of it is the `reviews` block: TMDb has
no Hebrew reviews and returns English ones, so it is content arriving rather than waste.

It is published under the **stock add-on id**, unlike the scraper. Arctic Fuse 3 imports
`plugin.video.themoviedb.helper` by name in a non-optional `<requires>`, the add-on's
Trakt token lives in its own settings, and it runs a background service that owns the
`TMDbHelper.*` window properties — so a renamed fork would need the skin rewritten around
it, would cost the user their Trakt login, and would have two services fighting over the
same properties.

Cached rows carry the language they were fetched under, and that is still `he-IL`, so the
add-on cannot tell the old Hebrew rows from the new English ones. **Delete
`addon_data/plugin.video.themoviedb.helper/database_07/` after updating** — otherwise
everything already cached stays Hebrew for up to thirty days.

**Upstreaming is the plan of record.** When a patch is merged upstream it is deleted here, not
maintained.

## How it works

`tools/build.py` downloads each upstream's released zip, gates every edit on an exact occurrence
count plus a hash of each match's surrounding lines, applies them byte-exact, and repacks. If any
gate rejects, nothing is published and the previous version keeps serving — so upstream drift shows
up as a failed build and an issue, never as a silently broken skin.

Descriptors are generated, never hand-written: `tools/gendescriptors.py <addon id> <extracted tree>
patches` measures the counts and hashes against a pristine tree and writes `patches/<addon id>/`.

Artifacts are release assets; only `addons.xml` and its checksum live on the `zips` / `zips22`
branches.

## Installing

1. Switch Kodi to another skin (Estuary).
2. Install `repository.ntzb-1.0.0.zip` via Add-ons → Install from zip file.
3. Open Arctic Fuse 3 → **Choose version** → pick the entry labelled **ntzb Repository**.
4. Switch back to Arctic Fuse 3.

Kodi records the repo an add-on came from and only ever checks that repo for updates, so step 3 is
what makes future updates arrive from here. Installing Arctic Fuse 3 from jurialmunkey's repository
again would silently drop both patches.

TMDb Helper is published under the stock id for the reasons above, so it needs the same treatment:
Add-ons → My add-ons → Video add-ons → TMDb Helper → **Choose version** → the entry labelled
**ntzb Repository**. Settings and the Trakt authorisation carry over untouched, because the add-on
id — and therefore its `addon_data` directory — is unchanged.

The scraper has no such conflict: it is a separate add-on id, installed from
Add-ons → Install from repository → ntzb Repository → Information providers → Movie information.

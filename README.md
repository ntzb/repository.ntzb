# repository.ntzb

A personal Kodi add-on repository serving patched builds of **Arctic Fuse 3**, **TMDb Helper**,
**jurialmunkey common**, Kodi's **TMDb movie scraper** and **עידן+ פלוס**, rebuilt automatically
from each upstream release.

## What is patched

### skin.arctic.fuse.3

| # | change | upstream |
|---|---|---|
| 001 | a skin setting to show titles as text instead of clearlogo art, in library lists and the video OSD | PR to be offered |
| 002 | Hebrew final forms restored to the Unicode fontset | [robotocjksc#3](https://github.com/jurialmunkey/resource.font.robotocjksc/issues/3), [rsms/inter#903](https://github.com/rsms/inter/issues/903) |
| 003 | the first genre in the info line, in place of the age rating, behind a skin setting | feature request to be offered |
| 004 | the stale half of the meta row held back behind a loading placeholder while TMDb Helper fetches, behind a skin setting | feature request to be offered |
| 005 | a landscape widget style that labels the row with the show name above the episode number and name, on the show's wide art | feature request to be offered |

Patch 005 exists because a widget labels an episode with the episode title and nothing else, and
in a *next episodes* widget that is the one field which does not say what the row is. "Special
Treatments" is a row about The White Lotus, and the only thing on screen that says so is a frame
grab. **Landscape with show title and art** puts the show name on the first line, the episode
number and name on the second, and draws the show's wide art instead of the episode still:

    Silo:
    3x05 - Memory

The number carries the second line on its own when there is no name to add:

    On Standby:
    1x07

"No name" is two cases. An episode TMDb has no title for can arrive with the field empty, and it
can arrive holding TMDb's own placeholder, the literal string `Episode 7`, because TMDb used to
synthesise that for untitled episodes and still serves it on records scraped while it did. Neither
says anything the number has not already said, so both collapse to the number. A show that
genuinely titles its episodes `Episode 7` loses nothing worth keeping either. The number is
`$VAR[Label_Plot_Episode_Number]`, upstream's own formatter, which zero-pads below ten already.

The two lines are two label controls rather than one run of text. Upstream stacks a single control
there, a textbox when `use_label` is false and a plain label when it is true, and a textbox wraps
rather than truncates, so a long episode name flowed onto a third line and was clipped with nothing
to show for it. A label given a width truncates itself, which is where the trailing dots come from;
Kodi draws three of them and the count is not a skin setting. The focused row scrolls the whole
line past instead, which is what `<scroll>` tied to the focused-layout flag buys. An item that is
not an episode -- a movie, a show, a PVR channel -- puts its label on the first line and leaves the
second empty, so a style picked for a mixed widget looks the way it always did.

The style does not replace the stock **Landscape**; it sits in the same list beside it. Seven more
shapes were built alongside it -- the same split on Poster, Flyer, Square, Placard and Board -- and
dropped once this one won. Re-adding any of them is one entry in `_STYLES` in
`tools/gendescriptors.py`, which drives the rows, the layouts, the busy placeholders, the generator
rules, the picker icons and the option list.

They are picked per widget, where every other widget setting is picked. Skin settings →
**Customise shortcuts and widgets** (or Settings → **Customise widgets**), pick the menu the widget
lives on down the left, **Widgets** on the right, then the widget itself, then **Style**. The new
entries sit at the end of the same list as Poster, Landscape, Square and the rest. Closing that
dialog rewrites the generated widget includes, and so does every Home load, so the choice takes
effect without a skin reload.

The art key is `tvshow.landscape`, and it is on the items rather than inferred. `VideoLibrary.
GetEpisodeDetails` returns the show's artwork alongside the episode's under a `tvshow.` prefix, and
`script.module.metadatautils` puts the whole dictionary on the listitem untouched. It also copies
the show's landscape down onto the bare `landscape` key when the episode has none, which is why the
stock style can look right on some items: on this library the two are the same url for every show
that has one. They are not the same key, though. A library episode that carries its own landscape
would answer with the episode's, and `season.landscape` is a third picture again, a per-season card
rather than the show's wide art. So the chain asks for `tvshow.landscape` first and treats
`landscape` as the fallback, not the other way round. The episode still is not in the chain at all.

Four of the twenty-seven shows in this library have no landscape at all, and they fall through to
`tvshow.fanart`, which is wide and is what the stock style would have shown for a show with no
episode thumbnail anyway.

The copied layouts and rows are upstream's own, with include names changed and, in the one label
layout they all share, the single label control replaced by the two. `tools/gendescriptors.py`
lifts them out of the pristine tree at generation time rather than restating them, so they cannot
drift from upstream by transcription. They are new includes rather than edits to the originals: the
stock widgets, the OSD playlist, the PVR guide and every hub row that uses them are left exactly as
they were. `git log -L` over `Layout_Labels` and `Layout_Landscape` shows one commit each, the
initial one, so what the copies can go stale against has not moved since the skin was released.

Every anchor is an `<include name="...">` or `<variable name="...">` declaration line, except the
two in the generator data, which are the catch-all rule each file ends with. Both kinds are the
most stable lines a skin file has. An include cannot be renamed without rewriting every call site,
and the catch-all is where upstream itself inserts ahead of, which is how Placard arrived in
`59d791a`. The new text is inserted whole at those points, so no upstream line is rewritten in
`Includes_Layouts.xml`, `Includes_Lists.xml`, `Includes_Widgets.xml`, `Includes_Labels.xml` or
`Includes_Images.xml`; the one line that is rewritten is the widget style option list in
`Includes_Actions.xml`, and the new options are appended to its tail.

The style names are plain English rather than `$LOCALIZE` ids. They ride inside a `RunPlugin()`
builtin that `script.skinvariables` splits on `&&` and then `unquote_plus`es, so they must avoid
`&`, `=`, `+` and brackets; and a numbered string would stake a claim on an id that upstream is
still handing out one at a time.

The non-landscape twins are there to be compared against each other and are expected to be dropped
once one of them wins. Dropping them is one edit to `_STYLES` in `tools/gendescriptors.py`.

Patch 004 exists because the ratings, status and awards in the info row come from TMDb Helper's
service monitor, which answers a focus change some way after the cursor has moved — three or four
seconds of it, in a TMDb Helper list. It does not blank the row while it works: the monitor
overwrites properties rather than clearing them first, so what stands there for those seconds is
the *previous* item's rating, presented as if it belonged to the item now under the cursor. That,
not the empty row, is the thing worth fixing.

The monitor says when it is working, and says it twice, for two different halves of the row:
`TMDbHelper.IsUpdating` is set around the blocking details build and `TMDbHelper.IsUpdatingRatings`
around the ratings thread that follows it. Which flag bounds which field is readable off the
add-on: the rating properties, `Top250` and `Oscar_Wins` all come out of the ratings thread, so they
are stale until `IsUpdatingRatings` clears; `Status` arrives with the details, so it is stale only
until `IsUpdating` does. There is no id property that would answer this more precisely — both
`ListItem.base_tmdb_id` and `ListItem.monitor.tmdb_id` are written ahead of the values they belong
to, so either one matches the cursor again while the previous item's ratings are still on screen.

So while a field is stale it leaves, and the skin's own `Widget_Busy_BlankItem` placeholder bar
stands in its place — one per rating slot the user has configured. Both movements are on the same
one-second timer, which is what keeps a cached item from flickering: the value hides behind a
`Hidden` animation, which Kodi holds visible and laid out for the whole of its delay, and the bar
appears behind a `Visible` animation, which Kodi leaves out of the layout for the whole of *its*
delay. For the first second nothing moves; after it, the stale value fades out as the bar fades in.
Status and awards leave on the same timer but get no bar of their own — a rating slot is a promise
the user configured, while whether the next item carries a status or an Oscar is not known until it
arrives.

The timings are reasoned from the add-on's source rather than measured on a device, so the row can
show its own workings: a second skin setting, off by default, adds a live readout of both flags,
the three id properties and a rating to the end of the row.

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

### script.module.jurialmunkey

| # | change | upstream |
|---|--------|----------|
| 001 | the window id filtered against the same excludelist as the dialog id, so a missing window stops writing an error to the log on every poll | [#11](https://github.com/jurialmunkey/script.module.jurialmunkey/issues/11) |

`get_current_window()` checks the dialog id against `DIALOG_ID_EXCLUDELIST` and returns the window
id unchecked. Both `xbmcgui` calls answer `WINDOW_INVALID` (9999) when there is nothing to report,
and only one of them was ever checked:

```diff
 def get_current_window(get_dialog=True):
     dialog = xbmcgui.getCurrentWindowDialogId() if get_dialog else None
-    return dialog if dialog not in DIALOG_ID_EXCLUDELIST else xbmcgui.getCurrentWindowId()
+    if dialog not in DIALOG_ID_EXCLUDELIST:
+        return dialog
+    window = xbmcgui.getCurrentWindowId()
+    return window if window not in DIALOG_ID_EXCLUDELIST else 10000
```

9999 is the one id `get_current_window()` can return that `xbmcgui.Window()` refuses:
`CGUIWindowManager::GetWindow()` answers `nullptr` for `0` and `WINDOW_INVALID` before it looks the
id up, the constructor throws, and the binding writes `EXCEPTION: Window id does not exist` at
LOGERROR on the way out. The three `except RuntimeError` guards in the module swallow the exception
but not the log write, and nothing clears the condition — so TMDb Helper's two pollers, both at
`POLL_MIN_INCREMENT = 0.2` and both reading two window properties an iteration (`ServicePause`, and
`WidgetContainer` because Arctic Fuse 3 sets `TMDbHelper.UseLocalWidgetContainer`), write about
twenty errors a second. Measured here: 19.1–19.5/s, with the UI locked up and the cursor smearing
until Kodi was killed.

Kodi gets into that state after a skin reload. `LoadSkin` remembers the active window id,
`UnloadSkin` deletes the skin's custom windows and purges them from the window history, and the
`ActivateWindow(currentWindowID)` at the end then finds nothing to activate and returns without
pushing anything back, so `GetActiveWindow()` answers `WINDOW_INVALID` from then on.

`Window.IsVisible(<id>)` looks like the obvious non-throwing probe, and is the wrong one. It
resolves to `CGUIWindowManager::IsWindowActive(id, false)`, true when the id matches
`GetActiveWindow()` or sits in `m_activeDialogs` — which is exactly what the two `xbmcgui` calls
return, `WINDOW_INVALID` included. It is true for every value the function can produce, the one
that throws among them, so it would never fire.

10000 is the fallback `get_property()` and `WindowPropertySetter` already use, and where Kodi lands
whenever it cannot restore a window, so the callers that compare the result against `WINDOW_IDS`
get a sensible answer instead of an id matching nothing. A working skin never reaches it: the
return value is unchanged for every id that names a real window.

Published under the **stock add-on id**, and for a harder reason than TMDb Helper's: it is a
declared `<requires>` of `plugin.video.themoviedb.helper`, `script.skinvariables` and
`script.texturemaker`, so a rename would leave all three unable to resolve their dependency. The
other two only use `get_property`, `set_to_windowprop`, `clear_windowprops` and `WindowProperty`,
none of which reach `get_current_window()`, so neither is affected by the patch either way.

### plugin.video.idanplus

| # | change | upstream |
|---|--------|----------|
| 001 | the channel logo in the generated m3u taken from `channels.json` as it stands when it is already a url | [Fishenzon/repo#310](https://github.com/Fishenzon/repo/issues/310) |
| 002 | Kan image urls percent-encoded, so the ones with Hebrew in the path resolve | [Fishenzon/repo#311](https://github.com/Fishenzon/repo/issues/311) |

Both are one-line mistakes with the same shape: a url that is already complete gets treated as
though it still needed assembling, or one that still needs escaping gets treated as though it were
already done.

`MakeIPTVlist()` builds `tvg-logo` by pasting `channel['image']` onto the end of the add-on's own
images directory. That was right when the images shipped with the add-on; it is not now, because
every one of the 84 entries in the current `channels.json` carries an absolute
`https://raw.githubusercontent.com/...` url, and the result is a `special://` path with a url
glued to it that resolves to nothing at all:

```diff
-                               tvg_logo = 'special://home/addons/{0}/resources/images/{1}'.format(common.AddonID, channel['image'])
+                               image = channel['image']
+                               tvg_logo = image if image.startswith('http://') or image.startswith('https://') else 'special://home/addons/{0}/resources/images/{1}'.format(common.AddonID, image)
```

The local branch is kept rather than dropped, because nothing says the data has to stay that way.
The `my_image` branch beside it is left exactly as it was, and deliberately: that value is written
by `ChangeChannelLogo()` from whatever `SaveLogo()` returns, which is always a bare filename inside
`addon_data/.../logos/channels/` — it is a local path by construction, even when the user picked
the logo from a url, because `SaveLogo()` downloads it first.

Kan names a good many of its images in Hebrew, and one of those urls is a 404 until the path is
escaped, at which point it is a 200:

```
https://mobapi.kan.org.il/media/qfkdwtzh/poster-image_small_239x360-מקום-שמח.jpg        404
https://mobapi.kan.org.il/media/qfkdwtzh/poster-image_small_239x360-%D7%9E...%D7%97.jpg 200
```

The add-on already knows this — `common.quoteNonASCII()` exists for it, and eleven of the fifteen
calls into `GetImageLink()` already use it — but the other four do not, and two lists built from
the mobile api bypass `GetImageLink()` altogether. So the quoting moves into the funnel:

```diff
 def GetImageLink(imageUrl, imageName):
+    imageUrl = common.quoteNonASCII(imageUrl)
     i = imageUrl.find('?')
```

`quoteNonASCII()` only touches characters above 127, so `%` survives it and nothing already
escaped is escaped twice; scheme, host and query are ascii and come through untouched. That makes
it safe to put in the shared path, where it is a no-op for the eleven callers that already quote.
The two mobile-api lists — radio series and podcasts — take the same one-word wrap at the point
they read `media_item[2]`, the logo image, straight out of the response.

Published under the **stock add-on id**. IPTV Simple is pointed at
`special://profile/addon_data/plugin.video.idanplus/idanplus.m3u`, and the add-on's settings,
per-channel name and logo overrides, favourites and cached EPG all live in that same directory —
a rename would take live TV down and orphan the lot.

The add-on's `.py` files are CRLF where every other upstream here is LF, so `patchlib` gates the
endings a file came in with rather than insisting on LF. Nothing compiled is published: a
`__pycache__` that outlives an upgrade, or a `.pyc` with no source beside it, is read before the
patched module is, and `drop_pycache()` plus a check over the finished zip keeps both out.

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

The shared module is a dependency rather than something installed by hand, so Kodi pulls it in on
its own. It arrives from whichever repository satisfied it first: if TMDb Helper was installed from
jurialmunkey's repository, that is where the module came from too, and switching TMDb Helper to
**Choose version** → **ntzb Repository** does not move it. Do the same for
Add-ons → My add-ons → Add-on libraries → jurialmunkey common. It is a python module, so nothing
reloads it until Kodi restarts.

The scraper has no such conflict: it is a separate add-on id, installed from
Add-ons → Install from repository → ntzb Repository → Information providers → Movie information.

עידן+ פלוס is published under the stock id too, so it takes the same **Choose version** step as
TMDb Helper, from Add-ons → My add-ons → Video add-ons. Two things then have to be nudged, because
neither happens on its own:

- the m3u is only rewritten when the add-on regenerates it, which the service does at Kodi start
  and every twelve hours. The add-on's settings → live TV → **יצירת קבצים לטלויזיה חיה** does it on
  demand.
- IPTV Simple only re-reads an m3u it has already loaded if its instance asks it to, and the
  instance here has `m3uRefreshMode = 0`. Disabling and re-enabling the PVR client picks the new
  file up; so does the add-on's **הגדרת IPTV Simple Client לשימוש בקבצי עידן פלוס**, which ends by
  doing exactly that.

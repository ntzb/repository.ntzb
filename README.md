# repository.ntzb

A personal Kodi add-on repository serving patched builds of **Arctic Fuse 3** and of Kodi's
**TMDb movie scraper**, rebuilt automatically from each upstream release.

## What is patched

### skin.arctic.fuse.3

| # | change | upstream |
|---|---|---|
| 001 | a skin setting to show titles as text instead of clearlogo art, in library lists and the video OSD | PR to be offered |
| 002 | Hebrew final forms restored to the Unicode fontset | [robotocjksc#3](https://github.com/jurialmunkey/resource.font.robotocjksc/issues/3), [rsms/inter#903](https://github.com/rsms/inter/issues/903) |
| 003 | the first genre in the info line, in place of the age rating, behind a skin setting | feature request to be offered |

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

The scraper has no such conflict: it is a separate add-on id, installed from
Add-ons → Install from repository → ntzb Repository → Information providers → Movie information.

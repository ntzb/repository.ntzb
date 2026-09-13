# repository.ntzb

A personal Kodi add-on repository serving a patched build of **Arctic Fuse 3**, rebuilt
automatically from each upstream release.

## What is patched

| # | change | upstream |
|---|---|---|
| 001 | a skin setting to show titles as text instead of clearlogo art, in library lists and the video OSD | PR to be offered |
| 002 | Hebrew final forms restored to the Unicode fontset | [robotocjksc#3](https://github.com/jurialmunkey/resource.font.robotocjksc/issues/3), [rsms/inter#903](https://github.com/rsms/inter/issues/903) |

Patch 002 exists because `resource.font.robotocjksc`'s `Inter-Unicode` fonts have no glyph for
U+05DA ך, U+05DD ם or U+05E5 ץ, so every Hebrew word ending in kaf, mem or tsadi loses its last
letter. The fonts are Inter 4.000 merged with DejaVu Sans 2.30 keyed on glyph name; Inter ships six
glyphs misnamed `uni05DA`, `uni05DD`, `uni05E5`, `uniFB47`, `uni25CE`, `uni200D` that are really
IPA letters, so the merge dropped the DejaVu originals and never mapped them. This repo ships
`resource.font.af3hebrew` with those six restored from the original donor, and repoints the skin's
fontset at it.

**Upstreaming is the plan of record.** When a patch is merged upstream it is deleted here, not
maintained.

## How it works

`tools/build.py` downloads upstream's released zip, gates every edit on an exact occurrence count
plus a hash of each match's surrounding lines, applies them byte-exact, and repacks. If any gate
rejects, nothing is published and the previous version keeps serving — so upstream drift shows up
as a failed build and an issue, never as a silently broken skin.

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

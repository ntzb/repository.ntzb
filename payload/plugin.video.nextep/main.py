# -*- coding: utf-8 -*-

import json
import sys
import traceback
from urllib.parse import parse_qsl

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")

# Everything the list needs, and nothing else. "art" is deliberately absent:
# Kodi repeats all thirteen tvshow.*/season.* keys on every episode row, so
# asking for it here costs more than fetching show art once per show below.
EPISODE_FIELDS = [
    "title",
    "showtitle",
    "season",
    "episode",
    "tvshowid",
    "playcount",
    "resume",
    "file",
    "runtime",
    "firstaired",
    "plot",
    "rating",
]

ANCHOR_FIELDS = ["tvshowid", "season", "episode", "lastplayed"]

SHOW_FIELDS = ["art", "title", "lastplayed", "episode", "watchedepisodes"]

# Show art is copied onto the episode under both the tvshow.* names the skin
# looks for first and the bare names the info dialogs fall back to.
ART_ALIASES = ("landscape", "clearlogo", "clearart", "banner", "fanart", "poster")


def log(message, level=xbmc.LOGDEBUG):
    xbmc.log("%s: %s" % (ADDON_ID, message), level)


def setting_bool(key, fallback):
    try:
        return ADDON.getSettingBool(key)
    except Exception:
        return fallback


def setting_int(key, fallback):
    try:
        value = ADDON.getSettingInt(key)
    except Exception:
        return fallback
    return value if value > 0 else fallback


def read_options(query):
    options = {
        "limit": setting_int("limit", 25),
        "specials": setting_bool("include_specials", False),
        "inprogress_only": setting_bool("inprogress_only", True),
    }
    params = dict(parse_qsl(query.lstrip("?")))
    if "limit" in params:
        try:
            options["limit"] = max(1, int(params["limit"]))
        except ValueError:
            pass
    for name in ("specials", "inprogress_only"):
        if name in params:
            options[name] = params[name].strip().lower() in ("1", "true", "yes")
    return options


def build_batch(options):
    unwatched_rules = [{"field": "playcount", "operator": "lessthan", "value": "1"}]
    if not options["specials"]:
        unwatched_rules.append({"field": "season", "operator": "greaterthan", "value": "0"})

    return [
        {
            "jsonrpc": "2.0",
            "id": "unwatched",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "properties": EPISODE_FIELDS,
                "filter": {"and": unwatched_rules},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": "anchors",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "properties": ANCHOR_FIELDS,
                "filter": {"field": "playcount", "operator": "greaterthan", "value": "0"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": "shows",
            "method": "VideoLibrary.GetTVShows",
            "params": {"properties": SHOW_FIELDS},
        },
    ]


def call_library(batch):
    """One round trip for the whole listing: MethodCall accepts a request array."""
    raw = xbmc.executeJSONRPC(json.dumps(batch))
    try:
        parsed = json.loads(raw)
    except ValueError:
        log("unparseable JSON-RPC response: %s" % raw[:500], xbmc.LOGERROR)
        return {}

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        log("unexpected JSON-RPC response shape", xbmc.LOGERROR)
        return {}

    # Responses may come back in any order, so index them by request id.
    results = {}
    for response in parsed:
        if not isinstance(response, dict):
            continue
        if "error" in response:
            log("sub-request %r failed: %s" % (response.get("id"), response["error"]), xbmc.LOGERROR)
            continue
        result = response.get("result")
        if isinstance(result, dict):
            results[response.get("id")] = result
    return results


def rows(results, key, container):
    result = results.get(key)
    if not isinstance(result, dict):
        return []
    return result.get(container) or []


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def order_key(episode):
    return (as_int(episode.get("season")), as_int(episode.get("episode")))


def resume_seconds(episode):
    resume = episode.get("resume")
    if not isinstance(resume, dict):
        return 0.0
    try:
        return float(resume.get("position") or 0)
    except (TypeError, ValueError):
        return 0.0


def group_unwatched(episodes):
    grouped = {}
    for episode in episodes:
        if episode.get("episodeid") is None or not episode.get("file"):
            continue
        grouped.setdefault(as_int(episode.get("tvshowid")), []).append(episode)
    return grouped


def collect_anchors(episodes):
    """Per show, the watched episode Kodi would call the last played one."""
    best = {}
    for episode in episodes:
        show_id = as_int(episode.get("tvshowid"))
        season, number = order_key(episode)
        played = episode.get("lastplayed") or ""
        candidate = (bool(played), played, season, number)
        # A dated episode always wins over an undated one, whatever the numbering.
        if candidate > best.get(show_id, ()):
            best[show_id] = candidate
    return dict((show_id, (value[2], value[3])) for show_id, value in best.items())


def index_shows(shows):
    indexed = {}
    for show in shows:
        indexed[as_int(show.get("tvshowid"))] = show
    return indexed


def is_inprogress(show, episodes):
    """Kodi's own tvshows "inprogress" rule, evaluated on data already in hand.

    Asking Kodi to apply the filter costs another 60ms of view work for an answer
    that agrees with this one on every show in the library. The resume branch goes
    a little further than Kodi does: a show whose first episode was started and
    abandoned counts as begun here, which is what a "play next" list should say.
    """
    watched = as_int(show.get("watchedepisodes"))
    total = as_int(show.get("episode"))
    if 0 < watched < total:
        return True
    if watched == 0:
        return any(resume_seconds(episode) > 0 for episode in episodes)
    return False


def pick_next(episodes, anchor):
    resumed = [episode for episode in episodes if resume_seconds(episode) > 0]
    if resumed:
        return min(resumed, key=order_key)
    if anchor is not None:
        later = [episode for episode in episodes if order_key(episode) > anchor]
        if later:
            return min(later, key=order_key)
    return min(episodes, key=order_key)


def select(results, options):
    unwatched = group_unwatched(rows(results, "unwatched", "episodes"))
    if not unwatched:
        return []

    anchors = collect_anchors(rows(results, "anchors", "episodes"))
    shows = index_shows(rows(results, "shows", "tvshows"))
    if not shows:
        # Without the show rows there is no art and no watched/total counts, so
        # filtering would silently empty the list. Show everything instead.
        log("no tvshow rows returned, listing every show with unwatched episodes")

    picks = []
    for show_id, episodes in unwatched.items():
        show = shows.get(show_id) or {}
        if shows and options["inprogress_only"] and not is_inprogress(show, episodes):
            continue
        picks.append((show, pick_next(episodes, anchors.get(show_id))))

    picks.sort(key=lambda pair: pair[0].get("title") or pair[1].get("showtitle") or "")
    # Most recently watched show first; shows never played sort to the bottom.
    picks.sort(key=lambda pair: pair[0].get("lastplayed") or "", reverse=True)
    return picks[:options["limit"]]


def show_art(show):
    art = show.get("art")
    if not isinstance(art, dict):
        return {}
    mapped = {}
    for key, url in art.items():
        if url:
            mapped["tvshow." + key] = url
    for key in ART_ALIASES:
        url = art.get(key)
        if url:
            mapped[key] = url
    return mapped


def make_listitem(show, episode):
    path = episode.get("file") or ""
    item = xbmcgui.ListItem(
        label=episode.get("title") or "",
        label2=episode.get("showtitle") or "",
        path=path,
        offscreen=True,
    )
    item.setProperty("IsPlayable", "true")

    # No "thumb": the directory provider runs the video thumb loader over every
    # item, which fills the episode still from the dbid set below.
    art = show_art(show)
    if art:
        item.setArt(art)

    tag = item.getVideoInfoTag()
    tag.setMediaType("episode")
    tag.setDbId(as_int(episode.get("episodeid")))
    tag.setTitle(episode.get("title") or "")
    tag.setTvShowTitle(episode.get("showtitle") or "")
    tag.setSeason(as_int(episode.get("season")))
    tag.setEpisode(as_int(episode.get("episode")))
    tag.setPlaycount(0)
    tag.setPlot(episode.get("plot") or "")

    runtime = as_int(episode.get("runtime"))
    if runtime > 0:
        tag.setDuration(runtime)
    if episode.get("firstaired"):
        tag.setFirstAired(episode["firstaired"])

    try:
        rating = float(episode.get("rating") or 0)
    except (TypeError, ValueError):
        rating = 0.0
    if rating > 0:
        tag.setRating(rating)

    position = resume_seconds(episode)
    if position > 0:
        resume = episode.get("resume") or {}
        try:
            total = float(resume.get("total") or 0)
        except (TypeError, ValueError):
            total = 0.0
        tag.setResumePoint(position, total)

    return (path, item, False)


def build_entries(query):
    options = read_options(query)
    results = call_library(build_batch(options))
    return [make_listitem(show, episode) for show, episode in select(results, options)]


def main():
    try:
        handle = int(sys.argv[1])
    except (IndexError, ValueError):
        log("no plugin handle, refusing to run", xbmc.LOGERROR)
        return

    succeeded = True
    entries = []
    try:
        entries = build_entries(sys.argv[2] if len(sys.argv) > 2 else "")
    except Exception:
        log(traceback.format_exc(), xbmc.LOGERROR)
        succeeded = False

    try:
        xbmcplugin.setContent(handle, "episodes")
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        if entries:
            xbmcplugin.addDirectoryItems(handle, entries, len(entries))
    except Exception:
        log(traceback.format_exc(), xbmc.LOGERROR)
        succeeded = False

    # Widgets re-run the plugin on every library change, so a disc copy could
    # only ever be stale.
    xbmcplugin.endOfDirectory(handle, succeeded, False, False)


if __name__ == "__main__":
    main()

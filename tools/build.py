"""Rebuild the patched add-ons from their upstream released zips and stage a repository index.

Fails closed: if any gate rejects, nothing is written to dist/ and the previously
published version keeps serving.
"""
import gzip
import hashlib
import os
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patchlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = "https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips"
KODI = "https://mirrors.kodi.tv/addons/omega"
SKIN = "skin.arctic.fuse.3"
HELPER = "plugin.video.themoviedb.helper"
FONT = "resource.font.af3hebrew"
REPO = "repository.ntzb"
STOCK = "metadata.themoviedb.org.python"
STOCK_NAME = "The Movie Database Python"
SCRAPER = STOCK + ".ntzb"
SCRAPER_NAME = "The Movie Database Python (ntzb)"
BUILD_N = 7
SCRAPER_BUILD_N = 2
HELPER_BUILD_N = 1
FONT_VERSION = "1.1.0"
REPO_VERSION = "1.0.0"

def log(msg):
    print(msg, flush=True)

def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def index_version(blob, addon_id, where):
    for a in ET.fromstring(blob.decode("utf-8")).findall("addon"):
        if a.get("id") == addon_id:
            return a.get("version")
    raise SystemExit("%s not found in %s" % (addon_id, where))


def upstream_version(addon_id):
    return index_version(fetch(UPSTREAM + "/addons.xml"), addon_id, "jurialmunkey addons.xml")


def kodi_version(addon_id):
    """The version Kodi's own repository advertises -- the released artifact, not git."""
    return index_version(gzip.decompress(fetch(KODI + "/addons.xml.gz")), addon_id,
                         "kodi addons.xml.gz")


def rename_addon(tree):
    """Re-id the forked scraper so it coexists with the stock one instead of
    colliding with it. Counted like a patch: a silent miss here would publish an
    add-on that claims to be the official scraper."""
    for rel, find, with_ in (
            ("addon.xml", 'id="%s"' % STOCK, 'id="%s"' % SCRAPER),
            ("addon.xml", 'name="%s"' % STOCK_NAME, 'name="%s"' % SCRAPER_NAME),
            ("resources/settings.xml",
             '<section id="%s">' % STOCK, '<section id="%s">' % SCRAPER)):
        path = os.path.join(tree, rel)
        with open(path, "rb") as fh:
            buf = fh.read()
        f = find.encode("utf-8")
        if buf.count(f) != 1:
            raise SystemExit("%s: %r expected 1, found %d" % (rel, find, buf.count(f)))
        with open(path, "wb") as fh:
            fh.write(buf.replace(f, with_.encode("utf-8")))


def patch(tree, addon_id):
    d = os.path.join(ROOT, "patches", addon_id)
    for name in sorted(os.listdir(d)):
        desc = patchlib.load(os.path.join(d, name))
        touched = patchlib.apply(tree, desc)
        log("applied %-22s -> %s" % (desc["id"], ", ".join(touched)))


def unpack(url, work, name):
    log("fetching %s" % url)
    zpath = os.path.join(work, name + ".zip")
    with open(zpath, "wb") as fh:
        fh.write(fetch(url))
    with zipfile.ZipFile(zpath) as z:
        z.extractall(work)
    return os.path.join(work, name)

def set_addon_version(tree, version):
    p = os.path.join(tree, "addon.xml")
    with open(p, "rb") as fh:
        buf = fh.read()
    lo = buf.index(b"<addon ")
    hi = buf.index(b">", lo)
    head = buf[lo:hi]
    i = head.index(b'version="')
    j = head.index(b'"', i + 9)
    with open(p, "wb") as fh:
        fh.write(buf[:lo] + head[:i + 9] + version.encode() + head[j:] + buf[hi:])

def zip_tree(src, root_name, dest):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src):
            for f in sorted(files):
                full = os.path.join(base, f)
                rel = os.path.relpath(full, src).replace(os.sep, "/")
                z.write(full, "%s/%s" % (root_name, rel))
    with zipfile.ZipFile(dest) as z:
        tops = {n.split("/", 1)[0] for n in z.namelist()}
    if tops != {root_name}:
        raise SystemExit("%s: expected a single root %r, got %r" % (dest, root_name, tops))

def stage(dist, addon_id, version, tree, src_assets):
    out = os.path.join(dist, addon_id)
    os.makedirs(out, exist_ok=True)
    zip_tree(tree, addon_id, os.path.join(out, "%s-%s.zip" % (addon_id, version)))
    for name in ("icon.png", "fanart.jpg"):
        s = os.path.join(src_assets, name)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(out, name))
    return out

def already_published(addon_id, version):
    url = ("https://github.com/ntzb/repository.ntzb/releases/download/%s/%s-%s.zip"
           % (addon_id, addon_id, version))
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60):
            return True
    except Exception:
        return False


def emit(**kw):
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as fh:
        for k, v in kw.items():
            fh.write("{}={}\n".format(k, v))


def main():
    work = os.path.join(ROOT, "build")
    dist = os.path.join(ROOT, "dist")
    for d in (work, dist):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)

    up = upstream_version(SKIN)
    ours = "%s+ntzb%d" % (up, BUILD_N)
    sup = kodi_version(STOCK)
    sours = "%s+ntzb%d" % (sup, SCRAPER_BUILD_N)
    hup = upstream_version(HELPER)
    hours = "%s+ntzb%d" % (hup, HELPER_BUILD_N)
    emit(upstream=up, version=ours, scraper_upstream=sup, scraper_version=sours,
         helper_upstream=hup, helper_version=hours)
    for a, b in ((up, ours), (sup, sours), (hup, hours)):
        log("upstream %s -> publishing %s" % (a, b))

    font_src = os.path.join(ROOT, "payload", FONT)
    repo_src = os.path.join(ROOT, "repo", REPO)
    wanted = ((SKIN, ours), (FONT, FONT_VERSION), (REPO, REPO_VERSION), (SCRAPER, sours),
              (HELPER, hours))

    # All or nothing, as before: payload edited without a version bump only reaches
    # users on the next publish, so one missing artifact republishes them all.
    if os.environ.get("FORCE") != "true" and all(already_published(a, v) for a, v in wanted):
        log("%s, %s and %s already published, nothing to do" % (ours, sours, hours))
        emit(published="skip")
        return

    tree = unpack("%s/%s/%s-%s.zip" % (UPSTREAM, SKIN, SKIN, up), work, SKIN)
    patch(tree, SKIN)
    set_addon_version(tree, ours)

    stree = unpack("%s/%s/%s-%s.zip" % (KODI, STOCK, STOCK, sup), work, STOCK)
    patch(stree, SCRAPER)
    rename_addon(stree)
    set_addon_version(stree, sours)

    # Published under the stock id: Arctic Fuse 3 imports plugin.video.themoviedb.helper
    # by name and the add-on's Trakt token lives in its settings, so a rename would cost
    # the skin its dependency and the user their login.
    htree = unpack("%s/%s/%s-%s.zip" % (UPSTREAM, HELPER, HELPER, hup), work, HELPER)
    patch(htree, HELPER)
    set_addon_version(htree, hours)

    stage(dist, SKIN, ours, tree, tree)
    stage(dist, FONT, FONT_VERSION, font_src, font_src)
    stage(dist, REPO, REPO_VERSION, repo_src, repo_src)
    stage(dist, SCRAPER, sours, stree, os.path.join(stree, "resources"))
    stage(dist, HELPER, hours, htree, htree)

    index = [b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', b"<addons>"]
    for src in (tree, font_src, repo_src, stree, htree):
        with open(os.path.join(src, "addon.xml"), "rb") as fh:
            body = fh.read()
        index.append(body[body.index(b"<addon "):].rstrip())
    index.append(b"</addons>\n")
    blob = b"\n".join(index)
    with open(os.path.join(dist, "addons.xml"), "wb") as fh:
        fh.write(blob)
    with open(os.path.join(dist, "addons.xml.sha256"), "wb") as fh:
        fh.write(hashlib.sha256(blob).hexdigest().encode())

    emit(published="yes")
    log("staged dist/ for %s, %s and %s" % (ours, sours, hours))

if __name__ == "__main__":
    main()

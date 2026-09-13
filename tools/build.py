"""Rebuild the patched skin from upstream's released zip and stage a repository index.

Fails closed: if any gate rejects, nothing is written to dist/ and the previously
published version keeps serving.
"""
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
SKIN = "skin.arctic.fuse.3"
BUILD_N = 1

def log(msg):
    print(msg, flush=True)

def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def upstream_version():
    root = ET.fromstring(fetch(UPSTREAM + "/addons.xml").decode("utf-8"))
    for a in root.findall("addon"):
        if a.get("id") == SKIN:
            return a.get("version")
    raise SystemExit("%s not found in upstream addons.xml" % SKIN)

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

def already_published(version):
    url = ("https://github.com/ntzb/repository.ntzb/releases/download/%s/%s-%s.zip"
           % (SKIN, SKIN, version))
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

    up = upstream_version()
    ours = "%s+ntzb%d" % (up, BUILD_N)
    emit(upstream=up, version=ours)
    log("upstream %s -> publishing %s" % (up, ours))

    if already_published(ours) and os.environ.get("FORCE") != "true":
        log("%s already published, nothing to do" % ours)
        emit(published="skip")
        return

    zpath = os.path.join(work, "upstream.zip")
    url = "%s/%s/%s-%s.zip" % (UPSTREAM, SKIN, SKIN, up)
    log("fetching %s" % url)
    with open(zpath, "wb") as fh:
        fh.write(fetch(url))
    with zipfile.ZipFile(zpath) as z:
        z.extractall(work)
    tree = os.path.join(work, SKIN)

    for name in sorted(os.listdir(os.path.join(ROOT, "patches"))):
        desc = patchlib.load(os.path.join(ROOT, "patches", name))
        touched = patchlib.apply(tree, desc)
        log("applied %-22s -> %s" % (desc["id"], ", ".join(touched)))

    set_addon_version(tree, ours)
    stage(dist, SKIN, ours, tree, tree)
    stage(dist, "resource.font.af3hebrew", "1.0.0",
          os.path.join(ROOT, "payload", "resource.font.af3hebrew"),
          os.path.join(ROOT, "payload", "resource.font.af3hebrew"))
    stage(dist, "repository.ntzb", "1.0.0",
          os.path.join(ROOT, "repo", "repository.ntzb"),
          os.path.join(ROOT, "repo", "repository.ntzb"))

    index = [b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', b"<addons>"]
    for aid, src in ((SKIN, tree),
                     ("resource.font.af3hebrew", os.path.join(ROOT, "payload", "resource.font.af3hebrew")),
                     ("repository.ntzb", os.path.join(ROOT, "repo", "repository.ntzb"))):
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
    log("staged dist/ for %s" % ours)

if __name__ == "__main__":
    main()

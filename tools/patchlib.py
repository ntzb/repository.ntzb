"""Declarative byte-level patching of third-party add-on trees.

Everything is bytes: a text-mode round trip on Windows silently rewrites both the
encoding and the line endings, and the upstreams disagree about the latter --
jurialmunkey ships LF, Fishenzon ships CRLF, and each has to come back out the
way it went in.
"""
import hashlib
import json
import os

CTX_LINES = 3


def _expand(buf, start, end):
    lo = start
    for _ in range(CTX_LINES + 1):
        nl = buf.rfind(b"\n", 0, lo)
        if nl < 0:
            lo = 0
            break
        lo = nl
    hi = end
    for _ in range(CTX_LINES + 1):
        nl = buf.find(b"\n", hi)
        if nl < 0:
            hi = len(buf)
            break
        hi = nl + 1
    return buf[lo:hi]


def context_hashes(buf, needle):
    """sha256 of each occurrence widened to whole lines +/- CTX_LINES.

    Counts alone cannot see 'right number, wrong place' -- upstream adding one
    matching control in our region and dropping one elsewhere keeps the count.
    """
    out, at = [], 0
    while True:
        i = buf.find(needle, at)
        if i < 0:
            return out
        out.append(hashlib.sha256(_expand(buf, i, i + len(needle))).hexdigest())
        at = i + len(needle)


class PatchError(Exception):
    pass


def _b(s):
    return s.encode("utf-8")


def load(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def apply(tree, desc, strict_context=True):
    """Apply one descriptor to an extracted add-on tree. Raises PatchError and
    writes nothing unless every gate passes."""
    bufs, touched = {}, []

    def read(rel):
        if rel not in bufs:
            with open(os.path.join(tree, rel), "rb") as fh:
                bufs[rel] = fh.read()
        return bufs[rel]

    for rel, needle in desc.get("absent", []):
        if _b(needle) in read(rel):
            raise PatchError("%s: %r already present upstream" % (rel, needle))

    # Gate every edit against the pristine bytes before mutating anything: an
    # earlier edit moves the lines a later edit's context hash was measured over.
    for e in desc["edits"]:
        rel, find, count = e["file"], _b(e["find"]), e["count"]
        buf = read(rel)
        got = buf.count(find)
        if got != count:
            raise PatchError("%s: %r expected %d, found %d" % (rel, e["find"][:60], count, got))
        if strict_context and "contexts" in e:
            if context_hashes(buf, find) != e["contexts"]:
                raise PatchError("%s: context changed around %r" % (rel, e["find"][:60]))

    pristine = dict(bufs)

    for e in desc["edits"]:
        rel, find = e["file"], _b(e["find"])
        bufs[rel] = bufs[rel].replace(find, _b(e["with"]))
        touched.append(rel)

    for e in desc["edits"]:
        rel, find, with_, count = e["file"], _b(e["find"]), _b(e["with"]), e["count"]
        buf = bufs[rel]
        if e["kind"] == "replace":
            if buf.count(find) != 0:
                raise PatchError("%s: replace left the anchor behind" % rel)
        elif buf.count(find) != count:
            raise PatchError("%s: insert changed the anchor count" % rel)
        if buf.count(with_) != count:
            raise PatchError("%s: post-condition count wrong" % rel)

    # The gate is "the endings upstream shipped, unchanged" rather than "LF
    # everywhere": a bare LF written into a CRLF file is the same accident in
    # reverse, and it is the one a patch drafted against an LF upstream makes.
    for rel in sorted(set(touched)):
        buf = bufs[rel]
        if b"\r\n" in pristine[rel]:
            if buf.count(b"\n") != buf.count(b"\r\n"):
                raise PatchError("%s: bare LF written into a CRLF file" % rel)
        elif b"\r\n" in buf:
            raise PatchError("%s: CRLF introduced" % rel)
        with open(os.path.join(tree, rel), "wb") as fh:
            fh.write(bufs[rel])
    return sorted(set(touched))

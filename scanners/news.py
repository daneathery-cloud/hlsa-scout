"""News scanner: Google News search (which indexes small-town papers, local TV,
blogs and press releases) + free direct RSS feeds.

Every story is kept only if it is (1) in the territory (geo.locate), (2) on a
healthcare-business topic (a category's "match" words) and (3) recent. It is
then scored as an opportunity and tagged with the partners it could matter to.

For subscription outlets only the publisher's public headline/teaser is read;
no paywalled page is ever fetched."""
import calendar
import hashlib
import html as html_lib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import feedparser
import requests

import config
import geo

log = logging.getLogger("hlsascout.news")

_TAG_RE = re.compile(r"<[^<]+?>")
_PAYWALL_RE = re.compile("|".join(re.escape(m) for m in config.PAYWALLED_OUTLETS), re.I)
_BLOCKED_RE = re.compile("|".join(config.BLOCKED_SOURCES), re.I)
_NOISE_RE = re.compile("|".join(config.NOISE), re.I)
_BIG_RE = re.compile("|".join(config.BIG_SYSTEMS))
_PARTNER_RES = {k: re.compile("|".join(v), re.I) for k, v in config.PARTNER_RULES.items()}
_CAT_MATCH = {c["key"]: re.compile("|".join(c["match"]), re.I) for c in config.CATEGORIES}
_CAT_SIGNAL = {c["key"]: re.compile("|".join(c["signal"]), re.I) for c in config.CATEGORIES}
_CAT_BY_KEY = {c["key"]: c for c in config.CATEGORIES}


def _clean(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def story_id(title: str, link: str) -> str:
    # Google News links differ per query for the same story, so key on the headline.
    key = re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:120] or link
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:16]


def _entry_time(e):
    parsed = e.get("published_parsed") or e.get("updated_parsed")
    return calendar.timegm(parsed) if parsed else None


def _get(url: str) -> bytes:
    r = requests.get(url, headers=config.REQUEST_HEADERS, timeout=config.REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.content


def _entries_to_items(entries, default_source: str, limit: int) -> list:
    cutoff = time.time() - config.MAX_NEWS_AGE_DAYS * 86400
    items = []
    for e in entries[:limit]:
        title = _clean(e.get("title", ""))
        if not title:
            continue
        ts = _entry_time(e)
        if ts is None or ts < cutoff:
            continue
        source = default_source
        src = e.get("source")
        if isinstance(src, dict) and src.get("title"):
            source = src["title"]
            title = re.sub(rf"\s+-\s+{re.escape(source)}\s*$", "", title)
        elif default_source == "Google News":
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                title, source = parts
        summary = _clean(e.get("summary", ""))
        if summary.startswith(title[:40]):   # Google News "summary" is usually just the headline again
            summary = ""
        items.append({"title": title, "summary": summary[:400], "link": e.get("link", ""),
                      "source": source, "ts": ts})
    return items


def fetch_feed(name: str, url: str) -> list:
    try:
        d = feedparser.parse(_get(url))
        items = _entries_to_items(d.entries, name, config.ITEMS_PER_FEED)
        if d.entries and not items:
            log.info("Feed %s returned only old items - may be discontinued", name)
        return items
    except Exception as e:
        log.warning("Feed %s failed: %s", name, e)
        return []


def google_news(query: str, window: str = None) -> list:
    url = config.GOOGLE_NEWS_SEARCH.format(query=quote(f"{query} when:{window or config.NEWS_WINDOW}"))
    for attempt in range(2):
        try:
            d = feedparser.parse(_get(url))
            return _entries_to_items(d.entries, "Google News", config.ITEMS_PER_QUERY)
        except Exception as e:
            if attempt:
                log.warning("Google News query failed (%s): %s", e, query[:80])
            time.sleep(1.5)
    return []


def partners_for(text: str) -> list:
    return [k for k, rx in _PARTNER_RES.items() if rx.search(text)]


def _classify(item: dict, forced_cat: str = None) -> list:
    """Category keys a story belongs to (best first)."""
    text = item["title"] + " " + item["summary"]
    cats = []
    for c in config.CATEGORIES:
        k = c["key"]
        if _CAT_MATCH[k].search(text) and _CAT_SIGNAL[k].search(text):
            cats.append(k)
    if forced_cat and forced_cat in cats:
        cats.remove(forced_cat)
        cats.insert(0, forced_cat)
    return cats


def _score(item: dict, cat: str) -> float:
    """Opportunity score: how recent, how clearly an opportunity, how boutique."""
    text = item["title"] + " " + item["summary"]
    age_days = max(0.0, (time.time() - item["ts"]) / 86400)
    score = 3.0 * max(0.0, 1 - age_days / config.MAX_NEWS_AGE_DAYS)          # 0..3 freshness
    score += min(2.0, 0.7 * len(_CAT_SIGNAL[cat].findall(text)))             # 0..2 signal strength
    score += geo.small_town_bonus(item.get("loc"))                           # 0..1 boutique/rural
    score += min(1.5, 0.3 * len(item.get("partners", [])))                   # who could use it
    if item.get("big_system"):
        score -= 0.8
    if item.get("place"):                                                    # town named in the story itself
        score += 0.4
    return round(score, 2)


def _prepare(raw: list, forced_cat: str = None, require_local_name: bool = False) -> list:
    out = []
    for it in raw:
        text = it["title"] + " " + it["summary"]
        if _BLOCKED_RE.search(it["source"]) or _NOISE_RE.search(it["title"]):
            continue
        loc = geo.locate(text, it["source"])
        if not loc or (require_local_name and not loc["place"]):
            continue
        cats = _classify(it, forced_cat)
        if not cats:
            continue
        it = dict(it)
        it["loc"] = loc
        it["place"] = loc["place"]
        it["region"] = loc["region"]
        it["categories"] = cats
        it["category"] = cats[0]
        it["partners"] = partners_for(text)
        it["big_system"] = bool(_BIG_RE.search(text))
        it["paywalled"] = bool(_PAYWALL_RE.search(it["source"]))
        it["id"] = story_id(it["title"], it["link"])
        it["score"] = _score(it, it["category"])
        out.append(it)
    return out


def _words(title: str) -> set:
    return {w for w in re.findall(r"[a-z0-9$]+", title.lower()) if w not in _STOP and len(w) > 2}


def _merge_near_duplicates(stories: list) -> list:
    """The same story from several outlets (press release + paper + Yahoo...):
    keep the best-scored one and list the others as 'also covered by'."""
    kept = []
    for s in stories:
        w = _words(s["title"])
        for k in kept:
            kw = k["_w"]
            if w and kw and len(w & kw) / len(w | kw) >= 0.5:
                k.setdefault("also", []).append({"source": s["source"], "link": s["link"], "paywalled": s["paywalled"]})
                for c in s["categories"]:
                    if c not in k["categories"]:
                        k["categories"].append(c)
                break
        else:
            s["_w"] = w
            kept.append(s)
    for k in kept:
        k.pop("_w", None)
    return kept


def scan(progress_cb=None) -> dict:
    """Runs every category x place-group search plus the direct feeds.
    Returns {'stories': [...deduped, best first], 'stats': {...}}."""
    def say(msg):
        if progress_cb:
            progress_cb(msg)
        log.info(msg)

    jobs = [(cat, q) for cat, _region, q in geo.search_plan(config.CATEGORIES, config.HEALTH_TERMS)]
    say(f"Searching Google News: {len(jobs)} local searches across {len(geo.PLACES)} towns and counties...")

    collected, failures = [], 0
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda j: (j[0], google_news(j[1])), jobs))
    for cat_key, items in results:
        if not items:
            failures += 1
        collected += _prepare(items, forced_cat=cat_key)
    say(f"  Google News: {len(collected)} local, on-topic stories (before de-duplication)")

    say(f"Reading {len(config.NEWS_FEEDS)} direct feeds (local papers/TV + home health & hospital trade press)...")
    with ThreadPoolExecutor(6) as ex:
        feed_results = list(ex.map(lambda f: (f, fetch_feed(f[0], f[1])), config.NEWS_FEEDS))
    feed_count = 0
    for (name, url, is_local), items in feed_results:
        # Trade-press stories must name a place in the territory; local outlets are local by definition.
        kept = _prepare(items, require_local_name=not is_local)
        feed_count += len(kept)
        collected += kept
    say(f"  Direct feeds: {feed_count} matching stories")

    best = {}
    for it in collected:
        prev = best.get(it["id"])
        if prev is None:
            best[it["id"]] = it
        else:   # same story found by several searches: keep the richer record, merge categories
            for c in it["categories"]:
                if c not in prev["categories"]:
                    prev["categories"].append(c)
            prev["score"] = max(prev["score"], it["score"])
    stories = _merge_near_duplicates(sorted(best.values(), key=lambda s: (-s["score"], -s["ts"])))
    say(f"  {len(stories)} unique opportunity stories after de-duplication")
    return {"stories": stories,
            "stats": {"searches": len(jobs), "empty_searches": failures, "feeds": len(config.NEWS_FEEDS),
                      "unique": len(stories)}}


# --- "Find free versions" for paywalled stories -------------------------
_STOP = set("""a an the and or of to in on for at by with from as is are was were be been it its this that these those
new news says said will can could may might has have had not no but more most over after before into about up out than
how why what when where who which amid via per vs report""".split())
_free_cache: dict = {}


def keywords(title: str, limit: int = 6) -> list:
    title = re.sub(r"\s+-\s+[^-]{2,40}$", "", title or "").replace("’", "'")
    words, seen = [], set()
    caps, rest = [], []
    for n, tok in enumerate(re.findall(r"[A-Za-z0-9][A-Za-z0-9&'.\-]*", title)):
        clean = re.sub(r"'s$", "", tok).strip(".'-")
        low = clean.lower()
        if len(low) < 3 and not clean.isupper() or low in _STOP or low in seen:
            continue
        seen.add(low)
        # Names first; a headline's first word is capitalized anyway, so it doesn't count as a name.
        (caps if clean[:1].isupper() and n > 0 else rest).append(clean)
    words = caps + rest
    return words[:limit]


def _overlap(a: str, b: str) -> float:
    ta = {w.lower() for w in keywords(a, 8)}
    tb = set(re.findall(r"[a-z0-9&']+", b.lower()))
    return len([w for w in ta if w in tb]) / max(1, len(ta))


def free_search_url(words: list) -> str:
    excl = " ".join(f"-site:{d}" for d in config.FREE_SEARCH_EXCLUDED_DOMAINS)
    return ("https://news.google.com/search?q=" + quote(f"{' '.join(words)} {excl} when:60d")
            + "&hl=en-US&gl=US&ceid=US:en")


def find_free_versions(title: str, max_results: int = 5) -> dict:
    """Same story at outlets without a hard paywall (best effort). Always returns
    a Google News link the user can open; 'matches' may be empty."""
    words = keywords(title)
    result = {"keywords": " ".join(words), "search_url": free_search_url(words[:4]), "matches": [], "error": None}
    if not words:
        return result
    cached = _free_cache.get(title)
    if cached and time.time() - cached[0] < 1800:
        return cached[1]
    seen_src, matches = set(), []
    try:
        for q in (" ".join(words[:5]), " ".join(words[:3])):
            url = config.GOOGLE_NEWS_SEARCH.format(query=quote(q + " when:60d"))
            for e in feedparser.parse(_get(url)).entries[:30]:
                src = (e.get("source") or {}).get("title", "")
                href = (e.get("source") or {}).get("href", "")
                if _PAYWALL_RE.search(src) or any(d in href for d in config.FREE_SEARCH_EXCLUDED_DOMAINS):
                    continue
                if not src or src in seen_src:
                    continue
                t = re.sub(rf"\s+-\s+{re.escape(src)}\s*$", "", e.get("title", ""))
                score = _overlap(title, t)
                if score < 0.5:
                    continue
                seen_src.add(src)
                matches.append({"source": src, "title": t, "link": e.get("link", ""),
                                "published": e.get("published", "")[:16], "score": round(score, 2)})
            if len(matches) >= 2:
                break
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        return result
    matches.sort(key=lambda m: -m["score"])
    result["matches"] = matches[:max_results]
    _free_cache[title] = (time.time(), result)
    return result

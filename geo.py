"""The territory HLSA Scout watches, and how a story is judged to be local.

Four regions: Bexar County, the counties touching Bexar, the I-35 corridor up
to Austin/Round Rock, and an outer ring of Hill Country / rural towns.

Many town names exist elsewhere too (Pleasanton CA, Seguin Ontario, Kyle and
Austin are people's names, "Comfort" and "Manor" are words). Those are marked
ambiguous: they only count when the story also says Texas/TX/its county, or
comes from a known local outlet."""
import re

# region key -> (label, short label)
REGIONS = {
    "bexar":  ("Bexar County / San Antonio", "Bexar"),
    "ring":   ("Counties touching Bexar", "Bexar-adjacent"),
    "i35":    ("I-35 Corridor to Austin", "I-35 Corridor"),
    "rural":  ("Hill Country & rural ring", "Rural ring"),
}

# (place, county, region, ambiguous?)
PLACES = [
    # Bexar
    ("San Antonio", "Bexar", "bexar", False), ("Bexar County", "Bexar", "bexar", False),
    ("Alamo Heights", "Bexar", "bexar", False), ("Converse", "Bexar", "bexar", True),
    ("Live Oak", "Bexar", "bexar", True), ("Universal City", "Bexar", "bexar", True),
    ("Helotes", "Bexar", "bexar", False), ("Leon Valley", "Bexar", "bexar", False),
    ("Kirby", "Bexar", "bexar", True), ("Windcrest", "Bexar", "bexar", False),
    ("Selma", "Bexar", "bexar", True), ("Shavano Park", "Bexar", "bexar", False),
    ("Stone Oak", "Bexar", "bexar", False), ("Fair Oaks Ranch", "Bexar", "bexar", False),
    ("Somerset", "Bexar", "bexar", True), ("Von Ormy", "Bexar", "bexar", False),
    ("Hollywood Park", "Bexar", "bexar", True), ("Balcones Heights", "Bexar", "bexar", False),
    ("Castle Hills", "Bexar", "bexar", True), ("Olmos Park", "Bexar", "bexar", False),
    ("Terrell Hills", "Bexar", "bexar", False), ("Lackland", "Bexar", "bexar", False),
    ("Fort Sam Houston", "Bexar", "bexar", False), ("Randolph AFB", "Bexar", "bexar", False),
    ("JBSA", "Bexar", "bexar", False), ("Alamo City", "Bexar", "bexar", False), ("SA", "Bexar", "bexar", True),
    ("UTSA", "Bexar", "bexar", False), ("TAMUSA", "Bexar", "bexar", False), ("A&M-San Antonio", "Bexar", "bexar", False),
    # Counties touching Bexar
    ("New Braunfels", "Comal", "ring", False), ("Comal County", "Comal", "ring", False),
    ("Canyon Lake", "Comal", "ring", True), ("Bulverde", "Comal", "ring", False),
    ("Garden Ridge", "Comal", "ring", True), ("Spring Branch", "Comal", "ring", True),
    ("Seguin", "Guadalupe", "ring", True), ("Guadalupe County", "Guadalupe", "ring", False),
    ("Schertz", "Guadalupe", "ring", False), ("Cibolo", "Guadalupe", "ring", False),
    ("Marion", "Guadalupe", "ring", True), ("Floresville", "Wilson", "ring", False),
    ("Wilson County", "Wilson", "ring", True), ("La Vernia", "Wilson", "ring", False),
    ("Stockdale", "Wilson", "ring", True), ("Poth", "Wilson", "ring", False),
    ("Pleasanton", "Atascosa", "ring", True), ("Atascosa County", "Atascosa", "ring", False),
    ("Jourdanton", "Atascosa", "ring", False), ("Poteet", "Atascosa", "ring", False),
    ("Lytle", "Atascosa", "ring", False), ("Charlotte", "Atascosa", "ring", True),
    ("Hondo", "Medina", "ring", True), ("Medina County", "Medina", "ring", True),
    ("Castroville", "Medina", "ring", True), ("Devine", "Medina", "ring", True),
    ("Natalia", "Medina", "ring", True), ("Medina Valley", "Medina", "ring", False),
    ("Bandera", "Bandera", "ring", True), ("Lakehills", "Bandera", "ring", False),
    ("Boerne", "Kendall", "ring", False), ("Kendall County", "Kendall", "ring", False),
    ("Comfort", "Kendall", "ring", True),
    # I-35 corridor north to Austin
    ("San Marcos", "Hays", "i35", True), ("Hays County", "Hays", "i35", False),
    ("Kyle", "Hays", "i35", True), ("Buda", "Hays", "i35", True), ("Wimberley", "Hays", "i35", False),
    ("Dripping Springs", "Hays", "i35", False), ("Austin", "Travis", "i35", True),
    ("Travis County", "Travis", "i35", False), ("Pflugerville", "Travis", "i35", False),
    ("Manor", "Travis", "i35", True), ("Lakeway", "Travis", "i35", True),
    ("Round Rock", "Williamson", "i35", True), ("Williamson County", "Williamson", "i35", True),
    ("Georgetown", "Williamson", "i35", True), ("Cedar Park", "Williamson", "i35", False),
    ("Leander", "Williamson", "i35", False), ("Hutto", "Williamson", "i35", False),
    ("Taylor", "Williamson", "i35", True), ("Lockhart", "Caldwell", "i35", True),
    ("Luling", "Caldwell", "i35", True), ("Caldwell County", "Caldwell", "i35", True),
    ("Bastrop", "Bastrop", "i35", False), ("New Braunfels", "Comal", "i35", False),
    # Hill Country & rural ring
    ("Kerrville", "Kerr", "rural", False), ("Kerr County", "Kerr", "rural", False),
    ("Ingram", "Kerr", "rural", True), ("Fredericksburg", "Gillespie", "rural", True),
    ("Gillespie County", "Gillespie", "rural", False), ("Gonzales", "Gonzales", "rural", True),
    ("Nixon", "Gonzales", "rural", True), ("Karnes City", "Karnes", "rural", False),
    ("Kenedy", "Karnes", "rural", True), ("Karnes County", "Karnes", "rural", False),
    ("Pearsall", "Frio", "rural", True), ("Frio County", "Frio", "rural", False),
    ("Uvalde", "Uvalde", "rural", False), ("Blanco", "Blanco", "rural", True),
    ("Johnson City", "Blanco", "rural", True), ("Cuero", "DeWitt", "rural", False),
    ("Dilley", "Frio", "rural", False), ("Sabinal", "Uvalde", "rural", False),
]
# Duplicate place rows (New Braunfels is both Bexar-adjacent and on I-35) - first wins.
_seen = set()
PLACES = [p for p in PLACES if not (p[0] in _seen or _seen.add(p[0]))]

TEXAS_RE = re.compile(r"\bTexas\b|\bTX\b|\bTex\.", re.I)
# County names that also exist in other states don't, by themselves, prove Texas.
_AMBIGUOUS_COUNTIES = {"Wilson", "Medina", "Williamson", "Caldwell", "Marion", "Taylor", "Gonzales"}
COUNTY_NAMES = sorted({p[1] for p in PLACES} - _AMBIGUOUS_COUNTIES)
_COUNTY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in COUNTY_NAMES) + r") County\b", re.I)

# Small local outlets: a story from them is local even if no town is named.
# (Metro TV/radio/papers and Community Impact also cover statewide or other-metro
# news, so their stories must name a place in the territory - see locate().)
LOCAL_SOURCES = [
    ("San Antonio Report", "bexar"), ("San Antonio Business Journal", "bexar"), ("MySA", "bexar"),
    ("Herald-Zeitung", "ring"), ("Seguin Gazette", "ring"), ("Seguin Today", "ring"), ("Boerne Star", "ring"),
    ("Hill Country Weekly", "ring"), ("Wilson County News", "ring"), ("Pleasanton Express", "ring"),
    ("Hondo Anvil", "ring"), ("Bandera Bulletin", "ring"), ("Bandera Prophet", "ring"), ("Canyon Lake Week", "ring"),
    ("Devine News", "ring"), ("Castroville News", "ring"), ("Kendall County Now", "ring"), ("KWED", "ring"),
    ("San Marcos Daily Record", "i35"), ("San Marcos Record", "i35"), ("Hays Free Press", "i35"),
    ("Williamson County Sun", "i35"), ("Lockhart Post", "i35"), ("Pflugerville Pflag", "i35"),
    ("Hutto News", "i35"), ("Taylor Press", "i35"), ("Wimberley View", "i35"),
    ("Kerrville Daily Times", "rural"), ("DailyTimes.com", "rural"), ("Kerr County Lead", "rural"),
    ("Fredericksburg Standard", "rural"), ("Gonzales Inquirer", "rural"), ("Uvalde Leader", "rural"),
    ("Karnes Countywide", "rural"), ("Frio-Nueces Current", "rural"), ("Cuero Record", "rural"),
    ("dewittcountytoday", "rural"), ("hccommunityjournal", "rural"), ("Hill Country Community Journal", "rural"),
    ("Blanco County News", "rural"),
]
# Metro outlets: they make an ambiguous town name trustworthy (Texas context),
# but don't make a story local on their own.
METRO_SOURCES = ["San Antonio Report", "Express-News", "MySA", "KSAT", "KENS", "KABB", "WOAI", "Texas Public Radio",
                 "San Antonio Business Journal", "San Antonio Current", "CultureMap", "Community Impact", "KXAN",
                 "KVUE", "KUT", "Austin American-Statesman", "Statesman", "Austin Business Journal", "Austin Monitor",
                 "Texas Tribune", "Texas Standard", "Hoodline", "The Business Journals"]


_PLACE_RX = [(re.compile(r"(?<![A-Za-z])" + re.escape(p) + r"(?![A-Za-z])"), p, c, r, amb) for p, c, r, amb in PLACES]


def source_region(source: str) -> str | None:
    s = (source or "").lower()
    for name, region in LOCAL_SOURCES:
        if name.lower() in s:
            return region
    return None


def locate(text: str, source: str = "") -> dict | None:
    """Where a story is, or None if it isn't clearly in the territory.
    Returns {'place', 'county', 'region'}."""
    text = text or ""
    src_region = source_region(source)
    metro = any(m.lower() in (source or "").lower() for m in METRO_SOURCES)
    texas_context = (bool(TEXAS_RE.search(text)) or bool(_COUNTY_RE.search(text))
                     or src_region is not None or metro)
    best = None
    for rx, place, county, region, ambiguous in _PLACE_RX:
        if not rx.search(text):
            continue
        if ambiguous and not texas_context:
            continue
        # Prefer the smaller-town match (more specific than "San Antonio")
        rank = {"rural": 0, "ring": 1, "i35": 2, "bexar": 3}[region]
        if place in ("San Antonio", "Austin", "Bexar County", "Alamo City"):
            rank += 1
        if best is None or rank < best[0]:
            best = (rank, place, county, region)
    if best:
        return {"place": best[1], "county": best[2], "region": best[3]}
    if src_region:
        return {"place": "", "county": "", "region": src_region}
    return None


def small_town_bonus(loc: dict | None) -> float:
    """Boutique / rural opportunities rank a little higher, per the brief."""
    if not loc:
        return 0.0
    if loc["region"] == "rural":
        return 1.0
    if loc["region"] == "ring":
        return 0.8
    if loc["region"] == "i35" and loc["place"] not in ("Austin", "Travis County", ""):
        return 0.5
    return 0.0


# Big places get one search per category topic (a single broad health search
# there would hit Google News' 100-result cap); every other town gets one broad
# health search, which catches nearly all of its health news.
BIG_PLACES = ["San Antonio", "Austin", "New Braunfels", "San Marcos", "Round Rock", "Georgetown",
              "Bexar County", "Travis County", "Williamson County", "Hays County", "Cedar Park", "Pflugerville",
              "Kyle", "Seguin", "Boerne", "Schertz", "Leander", "Kerrville"]
_SKIP_SEARCH = {"SA", "UTSA", "TAMUSA", "A&M-San Antonio", "JBSA", "Alamo City", "Lackland", "Fort Sam Houston", "Randolph AFB", "Stone Oak"}


def _search_name(place: str, ambiguous: bool) -> str:
    return f'"{place}" Texas' if ambiguous else f'"{place}"'


def search_plan(categories: list, health_terms: str) -> list:
    """[(category key or None, region, query)] covering the whole territory."""
    plan = []
    for place, county, region, ambiguous in PLACES:
        if place in _SKIP_SEARCH:
            continue
        name = _search_name(place, ambiguous)
        if place in BIG_PLACES:
            for cat in categories:
                for topic in cat["topics"]:
                    plan.append((cat["key"], region, f"{name} {topic}"))
        else:
            plan.append((None, region, f"{name} {health_terms}"))
    return plan


# --- NPI Registry territory: 3-digit ZIP prefixes + the cities we accept ---
NPI_ZIP_PREFIXES = ["780", "781", "782", "786", "787", "788"]
NPI_CITIES = {}
for _p, _c, _r, _a in PLACES:
    if not _p.endswith("County") and _p not in ("Stone Oak", "JBSA", "Alamo City", "Medina Valley", "SA", "UTSA",
                                                 "TAMUSA", "A&M-San Antonio"):
        NPI_CITIES[_p.upper()] = (_p, _c, _r)
for _extra, _c, _r in [("SPRING BRANCH", "Comal", "ring"), ("CANYON LAKE", "Comal", "ring"),
                       ("FORT SAM HOUSTON", "Bexar", "bexar"), ("JBSA FT SAM HOUSTON", "Bexar", "bexar"),
                       ("JBSA LACKLAND", "Bexar", "bexar"), ("SCHERTZ", "Guadalupe", "ring"),
                       ("SAINT HEDWIG", "Bexar", "bexar"), ("ST HEDWIG", "Bexar", "bexar"),
                       ("ELMENDORF", "Bexar", "bexar"), ("ADKINS", "Bexar", "bexar"), ("ATASCOSA", "Bexar", "bexar"),
                       ("MC QUEENEY", "Guadalupe", "ring"), ("MCQUEENEY", "Guadalupe", "ring"),
                       ("ROUND ROCK", "Williamson", "i35"), ("CEDAR PARK", "Williamson", "i35"),
                       ("DEL VALLE", "Travis", "i35"), ("WEST LAKE HILLS", "Travis", "i35"),
                       ("BEE CAVE", "Travis", "i35"), ("LIBERTY HILL", "Williamson", "i35"),
                       ("CEDAR CREEK", "Bastrop", "i35"), ("ELGIN", "Bastrop", "i35"),
                       ("HELOTES", "Bexar", "bexar"), ("BOERNE", "Kendall", "ring"),
                       ("CASTROVILLE", "Medina", "ring"), ("HONDO", "Medina", "ring")]:
    NPI_CITIES.setdefault(_extra, (_extra.title(), _c, _r))

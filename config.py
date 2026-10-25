"""Shared configuration for HLSA Scout - local healthcare business-opportunity
intelligence for Healthcare Leaders of San Antonio's referral partners and
NT Partnership.

Edit this file to tune what HLSA Scout looks for: the opportunity categories
(and their search phrases), the partner-fit rules, the direct feeds and the
paywalled outlets. Places/regions live in geo.py."""
import os
import sys


def resource_path(relative_path: str) -> str:
    """Bundled resource path, both from source and from the PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


LOGO_PATH = resource_path(os.path.join("assets", "hlsa_logo.png"))
README_PATH = resource_path("README.html")

APP_NAME = "HLSA Scout"
APP_SUBTITLE = "Local Healthcare Opportunity Intelligence"
APP_VERSION = "1.1.0"
APP_VERSION_DATE = "2026-10-25"

# The phone edition (built by site_builder.py on GitHub, see .github/workflows/scan.yml)
PHONE_URL = "https://daneathery-cloud.github.io/hlsa-scout/"
REPO_URL = "https://github.com/daneathery-cloud/hlsa-scout"

# Brand colors sampled from healthcareleaderssa.com / the HLSA app
NAVY = "#1E3864"
NAVY_DARK = "#1C2230"
RED = "#CD2027"
CREAM = "#F6F5F2"

# --- How much to collect / show ----------------------------------------
NEWS_WINDOW = "30d"          # Google News look-back (small-town papers publish slowly)
MAX_NEWS_AGE_DAYS = 45       # anything older is dropped even if a feed still lists it
ITEMS_PER_QUERY = 25         # Google News results read per search
ITEMS_PER_FEED = 40          # direct RSS items read per feed
SECTION_COUNT = 8            # stories shown per category on the Scan Report
TOP_COUNT = 12               # stories in "Top Opportunities"
NPI_WINDOW_DAYS = 90         # "newly registered" = NPI issued within this many days
NPI_CACHE_HOURS = 20         # registry results are reused for this long between scans

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (HLSA Scout local research tool)"}
REQUEST_TIMEOUT = 20

GOOGLE_NEWS_SEARCH = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# --- Who could act on a story -------------------------------------------
# key -> (short label, what they do). NT Partnership first: it's the focus.
PARTNERS = {
    "nt_staff":   ("NT Staffing", "NT Partnership - boutique placements, primarily home health"),
    "nt_cred":    ("NT Credentialing", "NT Partnership - physician credentialing / payer enrollment"),
    "nurses_etc": ("Nurses Etc Staffing", "Healthcare staffing - local, travel, government"),
    "wave":       ("Wave Online", "Revenue cycle management, coding, billing"),
    "mr3":        ("MR3 Health", "Remote patient monitoring"),
    "orchestra":  ("Orchestra Health", "Surgical / patient readiness platform"),
    "guiding":    ("Guiding Light Hospice", "Hospice & home care"),
    "puckett":    ("Puckett PT", "Sports physical therapy"),
    "ascent":     ("Ascent Strategic Finance", "Fractional CFO services"),
    "vested":     ("Vested Business Brokers", "Buying / selling a practice or business"),
    "arista":     ("Arista Advisors", "Executive coaching & leadership development"),
    "macro":      ("Macro Integrated Marketing", "Marketing, branding, web, creative"),
}

# Keyword rules (regex, case-insensitive) that tag a story with the partners
# it could matter to. A story can fit several partners.
PARTNER_RULES = {
    "nt_staff": [r"home health", r"home care", r"hospice", r"assisted living", r"memory care",
                 r"senior (living|care)", r"nursing (home|facility)", r"skilled nursing", r"\bhiring\b",
                 r"job fair", r"hiring event", r"shortage", r"\bnurses?\b", r"\bstaff(ing)?\b",
                 r"caregiver", r"personal care", r"new (clinic|practice|hospital|location)",
                 r"\bopen(s|ing|ed)?\b.*\b(clinic|practice|hospital|center|care)\b", r"layoffs?"],
    "nt_cred":  [r"\bjoins?\b", r"welcomes?", r"new (physician|doctor|provider|practice|clinic)",
                 r"\b(physician|doctor|surgeon|nurse practitioner|\bNP\b|\bPA\b|DPT|psychiatrist)s?\b",
                 r"family (medicine|practice)", r"primary care", r"urgent care", r"medical group",
                 r"accepting new patients", r"credential", r"payer enrollment", r"\bopen(s|ing|ed)\b.*(clinic|practice)",
                 r"specialist", r"pediatric", r"behavioral health", r"counseling"],
    "nurses_etc": [r"hospital", r"emergency room", r"\bER\b", r"\bnurses?\b", r"nursing", r"staffing",
                   r"\bVA\b", r"veterans", r"military", r"travel nurs", r"\bhiring\b", r"shortage", r"beds"],
    "wave":     [r"new (clinic|practice)", r"billing", r"revenue", r"reimburse", r"medicaid", r"medicare",
                 r"\bclaims?\b", r"coding", r"rural hospital", r"financial", r"acquir", r"merger",
                 r"urgent care", r"\bopen(s|ing|ed)\b.*(clinic|practice)", r"budget", r"deficit"],
    "mr3":      [r"primary care", r"family (medicine|practice)", r"internal medicine", r"chronic",
                 r"diabet", r"hypertension", r"cardio", r"heart", r"rural health", r"\bFQHC\b",
                 r"federally qualified", r"podiatr", r"wound", r"remote (patient )?monitoring", r"telehealth",
                 r"seniors?", r"medicare"],
    "orchestra": [r"surg(ery|ical|eon)", r"\bASC\b", r"ambulatory", r"orthop", r"operating room",
                  r"hospital (expansion|tower|wing)", r"joint replacement", r"spine"],
    "guiding":  [r"assisted living", r"memory care", r"senior (living|community|center)", r"nursing (home|facility)",
                 r"skilled nursing", r"hospice", r"palliative", r"dementia", r"alzheimer", r"aging", r"retirement community"],
    "puckett":  [r"sports? medicine", r"athlet", r"orthop", r"physical therap", r"rehab", r"injur",
                 r"sports (complex|facility|park)", r"youth sports"],
    "ascent":   [r"\bgrants?\b", r"funding", r"\bbonds?\b", r"budget", r"financ", r"expan", r"invest",
                 r"acquir", r"startup", r"capital", r"loan", r"deficit", r"hospital district", r"tax"],
    "vested":   [r"acquir", r"acquisition", r"\bsold\b", r"\bsells?\b", r"for sale", r"merger", r"merges?",
                 r"new owner", r"ownership", r"retir(e|es|ing|ement)", r"clos(e|es|ing|ure)", r"bankrupt",
                 r"succession", r"buys?\b"],
    "arista":   [r"\bCEO\b", r"president", r"named", r"appoint", r"leadership", r"executive",
                 r"administrator", r"\bdirector\b", r"\bboard\b", r"chief", r"promot", r"succession"],
    "macro":    [r"grand opening", r"ribbon cutting", r"now open", r"\bopen(s|ing|ed)\b", r"rebrand",
                 r"new (location|name|brand)", r"launch", r"coming soon", r"relocat"],
}

# --- Opportunity categories --------------------------------------------
# How searching works (Google News indexes local papers, TV, blogs and press
# releases): every smaller town gets ONE broad healthcare search (HEALTH_TERMS),
# which catches nearly all of its health news; the big cities (geo.BIG_PLACES)
# get each category's short "topics" instead, because a broad search there would
# overflow. Keep each topic short - Google News silently ignores the rest of a
# long query (including the town name!). Every story is then sorted into
# categories locally using "match" + "signal".
# "match" = words a story must contain (title/summary) to be kept in the category.
CATEGORIES = [
    {
        "key": "openings", "label": "New Practices & Clinic Openings", "icon": "\U0001F3E5", "color": "#1E3864",
        "sub": "New physician practices, clinics, urgent cares and offices opening or coming soon. A new practice "
               "needs everything at once: providers credentialed, staff hired, billing set up, patients told.",
        "topics": [
            '(clinic OR "urgent care" OR "medical practice" OR "family medicine" OR pediatrics) (opens OR opening OR "grand opening" OR "ribbon cutting" OR "coming soon")',
            '("physical therapy" OR "behavioral health" OR counseling OR dermatology OR "primary care") (opens OR opening OR "new location")',
        ],
        "match": [r"clinic", r"practice", r"urgent care", r"medical", r"health", r"physician", r"doctor",
                  r"therap", r"dental|dentist", r"pediatric", r"wellness", r"pharmacy", r"care center"],
        "signal": [r"\bopen", r"coming soon", r"ribbon", r"new location", r"now open", r"expands? to", r"relocat"],
    },
    {
        "key": "facilities", "label": "Hospitals, ERs & Facility Projects", "icon": "\U0001F3D7️", "color": "#3A5BA0",
        "sub": "Hospitals, freestanding ERs, surgery centers and medical office buildings that are planned, "
               "breaking ground or expanding - staff and vendors are needed months before the doors open.",
        "topics": [
            '(hospital OR "emergency room" OR "surgery center" OR "medical office building") (groundbreaking OR expansion OR construction OR "breaks ground")',
        ],
        "match": [r"hospital", r"emergency", r"\bER\b", r"surg", r"medical (office|building|center|plaza|campus)",
                  r"health(care)? (campus|center|facility)", r"clinic", r"beds", r"trauma center",
                  r"health sciences?", r"\bEMS\b"],
        "signal": [r"ground", r"expan", r"construct", r"plan", r"approv", r"open", r"build", r"rezon", r"permit", r"tower",
                   r"propos", r"develop", r"launch", r"site\b"],
    },
    {
        "key": "senior", "label": "Home Health, Hospice & Senior Care", "icon": "\U0001F3E1", "color": "#C2185B",
        "sub": "Home health and hospice agencies, home-care franchises, assisted living and memory care - "
               "NT Partnership's core staffing market and a natural referral circle for hospice and RPM.",
        "topics": [
            '("home health" OR hospice OR "home care" OR caregivers)',
            '("assisted living" OR "memory care" OR "senior living" OR "nursing home")',
        ],
        "match": [r"home health", r"hospice", r"home care", r"assisted living", r"memory care", r"senior",
                  r"nursing (home|facility|center)", r"skilled nursing", r"adult day", r"caregiv", r"palliative",
                  r"retirement community", r"long-term care"],
        "signal": [r"open", r"new", r"coming", r"expan", r"acquir", r"hiring", r"build", r"plan", r"award", r"launch"],
    },
    {
        "key": "workforce", "label": "Staffing & Workforce Signals", "icon": "\U0001F465", "color": "#C9822A",
        "sub": "Hiring pushes, job fairs, shortages, new nursing/allied-health programs (the candidate pipeline) "
               "and layoffs or closures (experienced people suddenly available).",
        "topics": [
            '(nurses OR nursing OR "health care workers" OR caregivers) (hiring OR "job fair" OR shortage OR layoffs OR "nursing program")',
        ],
        "match": [r"nurs", r"health", r"medical", r"hospital", r"clinic", r"caregiv", r"physician", r"therap", r"\bEMS\b|paramedic"],
        "signal": [r"hir", r"job", r"shortage", r"layoff", r"program", r"graduat", r"recruit", r"workforce", r"staff", r"vacanc"],
    },
    {
        "key": "providers", "label": "Physicians & Leaders on the Move", "icon": "\U0001FA7A", "color": "#0089C4",
        "sub": "Doctors, nurse practitioners and therapists joining or starting practices (credentialing!), "
               "plus new administrators, CEOs and medical directors (new leaders bring new vendors).",
        "topics": [
            '(physician OR doctor OR "nurse practitioner" OR surgeon) (joins OR welcomes OR "accepting new patients")',
            '(hospital OR clinic OR "health system") (CEO OR administrator OR "medical director") (named OR appointed)',
        ],
        "match": [r"physician", r"doctor", r"\bdr\.", r"\bM\.?D\.?\b", r"\bD\.?O\.?\b", r"nurse practitioner", r"surgeon",
                  r"dentist", r"therapist", r"medical director", r"\bCEO\b", r"administrator", r"hospital", r"clinic", r"health"],
        "signal": [r"join", r"welcom", r"new", r"named", r"appoint", r"hire", r"accepting", r"seeing patients", r"promot"],
    },
    {
        "key": "deals", "label": "Ownership Changes, Sales & Closures", "icon": "\U0001F91D", "color": "#7B4FB5",
        "sub": "Practices and agencies changing hands, merging, retiring or closing - transition work for brokers, "
               "CFOs and billing, and displaced staff and patients that need a new home.",
        "topics": [
            '(clinic OR practice OR "home health" OR hospice OR hospital OR pharmacy) (acquires OR acquisition OR sold OR merger OR closing OR closure)',
        ],
        "match": [r"clinic", r"(medical|dental|physician|group|family) practice", r"home health", r"health system",
                  r"hospice", r"hospital", r"pharmacy", r"nursing (home|facility)", r"medical", r"urgent care",
                  r"assisted living", r"senior living", r"home care"],
        "signal": [r"acqui", r"\bsold\b", r"merg", r"owner", r"retir", r"clos", r"bankrupt", r"\bbuys?\b", r"sale",
                   r"purchas", r"operator"],
    },
    {
        "key": "funding", "label": "Grants, Funding & Rural Health", "icon": "\U0001F4B5", "color": "#1F9D55",
        "sub": "Grants, hospital-district budgets and bonds, rural-health and community-clinic funding - "
               "money arriving means programs to staff, bill, monitor and manage.",
        "topics": [
            '(grant OR funding OR bond OR "hospital district" OR "rural health" OR FQHC) (health OR clinic OR hospital)',
        ],
        "match": [r"health", r"clinic", r"hospital", r"medical", r"\bEMS\b", r"nurs", r"mental"],
        "signal": [r"grant", r"fund", r"bond", r"budget", r"award", r"million", r"invest", r"rural", r"\bFQHC\b",
                   r"federally qualified", r"community health", r"district"],
    },
]

HEALTH_TERMS = ('(clinic OR hospital OR "home health" OR hospice OR physician OR nurses OR "assisted living" '
                'OR "urgent care" OR healthcare OR medical)')

# --- Direct feeds (free, public RSS) -------------------------------------
# (source name, url, local?) Local general-news feeds are only kept when a story
# also matches a category; industry feeds additionally need a Texas/local mention.
NEWS_FEEDS = [
    ("San Antonio Report", "https://sanantonioreport.org/feed/", True),
    ("KSAT", "https://www.ksat.com/arc/outboundfeeds/rss/?outputType=xml", True),
    ("Texas Public Radio", "https://www.tpr.org/news.rss", True),
    ("Seguin Gazette", "https://seguingazette.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc", True),
    ("Seguin Today", "https://seguintoday.com/feed/", True),
    ("Kerrville Daily Times", "https://www.dailytimes.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc", True),
    ("Wilson County News", "https://www.wilsoncountynews.com/rss", True),
    ("KXAN Austin", "https://www.kxan.com/feed/", True),
    ("Becker's Hospital Review", "https://www.beckershospitalreview.com/feed/", False),
    ("Home Health Care News", "https://homehealthcarenews.com/feed/", False),
    ("Hospice News", "https://hospicenews.com/feed/", False),
    ("Senior Housing News", "https://seniorhousingnews.com/feed/", False),
    ("Texas Hospital Association", "https://www.tha.org/feed/", False),
]

# Outlets that put most stories behind a subscription. We only ever read the
# publisher's own public headline/teaser; the 🔓 button looks for the same
# story at free outlets (no paywall is bypassed).
PAYWALLED_OUTLETS = [
    "San Antonio Express-News", "Express-News", "The Business Journals", "San Antonio Business Journal",
    "Austin Business Journal", "Austin American-Statesman", "Statesman", "Houston Chronicle",
    "Dallas Morning News", "Modern Healthcare", "Wall Street Journal", "WSJ", "Bloomberg",
    "Herald-Zeitung", "New Braunfels Herald-Zeitung", "Boerne Star", "Medical Economics", "STAT+",
]
FREE_SEARCH_EXCLUDED_DOMAINS = [
    "expressnews.com", "bizjournals.com", "statesman.com", "houstonchronicle.com", "dallasnews.com",
    "modernhealthcare.com", "wsj.com", "bloomberg.com", "herald-zeitung.com", "medicaleconomics.com",
]

# Sources that are never local healthcare news for this region (same town names elsewhere).
BLOCKED_SOURCES = [r"Sutter Health", r"Pleasanton Weekly", r"ParrySound", r"East Bay Times", r"Patch.*Pleasanton",
                   r"Legacy\.com", r"Dignity Memorial", r"Funeral", r"Mortuary", r"Obituar", r"Tributes"]
# Stories about these are noise no matter where they are.
NOISE = [r"obituar", r"funeral", r"in loving memory", r"\bfootball\b", r"\bvolleyball\b", r"\bbasketball\b",
         r"\bbaseball\b", r"\bsoftball\b", r"playoff", r"touchdown", r"homecoming", r"\bhoroscope", r"recipe",
         r"\bbagel", r"restaurant", r"\bbrewery\b", r"\bbar\b and grill", r"high school .* (wins|beats|falls)",
         r"weather forecast", r"veterinar", r"\bpets?\b", r"emancipet", r"humane society", r"spay", r"animal", r"\bdogs?\b", r"\bcats?\b", r"\bcrash\b", r"\bshooting\b", r"\barrest", r"\bmurder", r"\bpolice\b", r"sheriff"]

# Big systems: shown (they matter!) but badged, and can be hidden on the Wire,
# so Mom-and-Pop opportunities aren't drowned out.
BIG_SYSTEMS = [r"Methodist", r"Baptist Health", r"Baptist Medical", r"University Health", r"CHRISTUS", r"HCA\b",
               r"Ascension", r"St\.? David'?s", r"Baylor Scott", r"UT Health", r"UTHealth", r"Texas Health Resources",
               r"Seton", r"Kaiser", r"Tenet", r"Brooke Army", r"\bBAMC\b", r"Audie Murphy", r"\bVA\b", r"Veterans Affairs",
               r"Optum", r"CVS", r"Walgreens", r"Walmart", r"Amazon", r"One Medical", r"Kelsey"]

DISCLAIMER = (
    "HLSA Scout is a research aggregator for Healthcare Leaders of San Antonio's referral partners and NT Partnership. "
    "It gathers publicly available news, press releases and public registry data and suggests which partners a story "
    "might matter to - the suggestions are keyword-based starting points, not verified leads. For subscription outlets "
    "only the publisher's own public headline and teaser are shown; no paywall is bypassed. Always confirm details "
    "directly before reaching out."
)

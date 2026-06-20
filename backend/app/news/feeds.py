"""RSS sources. Pure URL → category map; ingester pulls each on its cadence."""
FEEDS: list[dict[str, str]] = [
    {"source": "Reuters Business",   "url": "https://feeds.reuters.com/reuters/businessNews",            "category": "markets"},
    {"source": "MarketWatch Top",    "url": "https://www.marketwatch.com/feeds/topstories",              "category": "markets"},
    {"source": "WSJ Markets",        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",             "category": "markets"},
    {"source": "CNBC Top News",      "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",     "category": "markets"},
    {"source": "Seeking Alpha",      "url": "https://seekingalpha.com/feed.xml",                          "category": "analysis"},
    {"source": "Federal Reserve",    "url": "https://www.federalreserve.gov/feeds/press_all.xml",        "category": "macro"},
    {"source": "Treasury Press",     "url": "https://home.treasury.gov/news/press-releases/feed",        "category": "macro"},
    {"source": "Yahoo Finance",      "url": "https://finance.yahoo.com/news/rssindex",                   "category": "markets"},
    {"source": "BBC Business",       "url": "http://feeds.bbci.co.uk/news/business/rss.xml",             "category": "markets"},
    {"source": "FT Companies",       "url": "https://www.ft.com/companies?format=rss",                   "category": "companies"},
    {"source": "USGS Earthquakes",   "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", "category": "disaster"},
    {"source": "NOAA Hurricanes",    "url": "https://www.nhc.noaa.gov/index-at.xml",                     "category": "disaster"},
]

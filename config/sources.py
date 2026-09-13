# List of RSS feeds, curated from Ali's source map (official labs > research > tool discovery > aggregators)
# tag: used only for lightweight logging/debugging, not shown to the reader

FEEDS = [
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "tag": "official"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "tag": "official"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "tag": "official"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "tag": "official"},
    {"name": "arXiv cs.AI", "url": "https://rss.arxiv.org/rss/cs.AI", "tag": "research"},
    {"name": "arXiv cs.LG", "url": "http://arxiv.org/rss/cs.LG", "tag": "research"},
    {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/", "tag": "aggregator"},
    {"name": "The Gradient", "url": "https://thegradient.pub/rss/", "tag": "aggregator"},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "tag": "aggregator"},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "tag": "aggregator"},
    {"name": "AWS ML Blog", "url": "https://aws.amazon.com/blogs/machine-learning/feed/", "tag": "official"},
]

# How far back (in hours) to look for fresh items on each run.
LOOKBACK_HOURS = 30

# Max items pulled per feed (keeps things light and fast on GitHub's free runners)
MAX_ITEMS_PER_FEED = 8

# Reddit V2 data source: old.reddit.com HTML scraper.
#
# Additive alternative to the legacy app.reddit JSON client (Reddit killed the
# public .json endpoints). Exposes the singleton client and class so callers
# can ``from app.reddit_v2 import redditapiv2_client``.
from app.reddit_v2.redditapiv2_client import RedditAPIv2Client, redditapiv2_client

__all__ = ["RedditAPIv2Client", "redditapiv2_client"]

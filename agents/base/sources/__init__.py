"""agents/base/sources — Source Plugins"""
from agents.base.sources.gmail_source import GmailSource
from agents.base.sources.feed_crawler_source import FeedCrawlerSource
from agents.base.sources.newseria_source import NewseriaSource
from agents.base.sources.rss_source import RSSSource
from agents.base.sources.youtube_channel_source import YouTubeChannelSource

__all__ = [
    'GmailSource',
    'FeedCrawlerSource',
    'NewseriaSource',
    'RSSSource',
    'YouTubeChannelSource',
]

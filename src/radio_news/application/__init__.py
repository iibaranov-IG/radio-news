"""Read-only application services for product slice P1."""

from .feed import EditorialFeedItem, EditorialFeedService, FeedSnapshot

__all__ = ["EditorialFeedItem", "EditorialFeedService", "FeedSnapshot"]

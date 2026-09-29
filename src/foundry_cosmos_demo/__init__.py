"""Core package for the Foundry + Cosmos DB synthetic care-guidance demo."""

from .config import SeederSettings
from .seeder import seed_documents

__all__ = ["SeederSettings", "seed_documents"]

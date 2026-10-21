"""GROBID API endpoint handlers."""

from pte_plugin_grobid.handlers.base import GrobidHandler
from pte_plugin_grobid.handlers.training import TrainingHandler
from pte_plugin_grobid.handlers.fulltext import FulltextHandler
from pte_plugin_grobid.handlers.references import ReferencesHandler

__all__ = [
    "GrobidHandler",
    "TrainingHandler",
    "FulltextHandler",
    "ReferencesHandler",
]

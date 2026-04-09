"""Theme preprocessing: normalization and deduplication."""

import logging
import re
from difflib import SequenceMatcher

from app.config import config

logger = logging.getLogger(__name__)


class ThemePreprocessor:
    """Normalize and deduplicate complaint themes before clustering."""

    def __init__(
        self,
        case_normalize: bool | None = None,
        dedup_threshold: float | None = None,
    ):
        self.case_normalize = (
            case_normalize
            if case_normalize is not None
            else config.clustering_preprocess_case_normalize
        )
        self.dedup_threshold = (
            dedup_threshold
            if dedup_threshold is not None
            else config.clustering_preprocess_dedup_threshold
        )

    def normalize(self, theme: str) -> str:
        """Normalize a theme string: lowercase, strip whitespace, collapse spaces."""
        result = theme.strip()
        if self.case_normalize:
            result = result.lower()
        result = re.sub(r"\s+", " ", result)
        return result

    def deduplicate_themes(
        self,
        theme_to_count: dict[str, int],
    ) -> dict[str, str]:
        """Find near-duplicate themes and map them to the most frequent variant.

        Args:
            theme_to_count: Mapping of normalized theme -> post count.

        Returns:
            Mapping of every theme -> canonical theme (most frequent variant).
        """
        themes = sorted(
            theme_to_count.keys(),
            key=lambda t: theme_to_count[t],
            reverse=True,
        )

        # Each theme maps to itself by default
        mapping: dict[str, str] = {t: t for t in themes}
        # Track which canonical themes we've already assigned
        canonical: list[str] = []

        for theme in themes:
            # Check if this theme is already mapped to a canonical
            if mapping[theme] != theme:
                continue

            canonical.append(theme)

            # Find near-duplicates among remaining themes
            for other in themes:
                if other == theme or mapping[other] != other:
                    continue

                similarity = SequenceMatcher(None, theme, other).ratio()
                if similarity >= self.dedup_threshold:
                    mapping[other] = theme

        merged_count = sum(1 for k, v in mapping.items() if k != v)
        logger.info(
            f"Deduplication: {len(themes)} themes -> {len(canonical)} canonical "
            f"({merged_count} merged)"
        )
        return mapping

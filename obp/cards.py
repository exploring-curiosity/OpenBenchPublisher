"""Data Card and Repro Card generation."""

from typing import Dict, Any, List
from datetime import datetime
import json
import logging

from obp.db import get_cards_collection

logger = logging.getLogger(__name__)


class CardPublisher:
    """Publisher for Data Cards and Repro Cards."""
    
    def __init__(self):
        self.cards_col = get_cards_collection()
    
    def publish_data_card(
        self,
        dataset_id: str,
        manifest: Dict[str, Any],
        classes: List[str],
    ) -> Dict[str, Any]:
        """Publish a Data Card for a dataset slice."""
        logger.info(f"Publishing Data Card for dataset: {dataset_id}")
        
        stats = manifest["stats"]
        
        card = {
            "type": "data_card",
            "dataset_id": dataset_id,
            "title": f"Dataset: {' vs '.join(classes)}",
            "summary": {
                "total_samples": manifest["total"],
                "classes": classes,
                "splits": {
                    "train": stats["train_count"],
                    "val": stats["val_count"],
                    "test": stats["test_count"],
                },
                "class_distribution": stats["class_distribution"],
            },
            "license": {
                "type": "CC-BY",
                "attribution": "Images sourced from Wikimedia Commons, Unsplash, Pexels",
            },
            "provenance": {
                "source": "Tavily image search",
                "search_domains": ["commons.wikimedia.org", "unsplash.com", "pexels.com"],
                "deduplication": "pHash + vector similarity (threshold=0.95)",
            },
            "quality_metrics": {
                "min_resolution": "512px",
                "dedupe_applied": True,
                "balance_strategy": "equal_per_class",
            },
            "created_at": datetime.utcnow(),
            "version": "1.0",
        }
        
        result = self.cards_col.insert_one(card)
        card["card_id"] = str(result.inserted_id)
        
        logger.info(f"Data Card published: {card['card_id']}")
        return card
    
    def format_card_markdown(self, card: Dict[str, Any]) -> str:
        """Format card as Markdown for display."""
        if card["type"] == "data_card":
            return self._format_data_card_md(card)
        return json.dumps(card, indent=2, default=str)
    
    def _format_data_card_md(self, card: Dict[str, Any]) -> str:
        """Format Data Card as Markdown."""
        summary = card["summary"]
        
        md = f"""# {card['title']}

**Type:** Data Card  
**Dataset ID:** `{card['dataset_id']}`  
**Created:** {card['created_at'].strftime('%Y-%m-%d %H:%M UTC')}

## Summary
- **Total Samples:** {summary['total_samples']}
- **Classes:** {', '.join(summary['classes'])}

## Splits
- **Train:** {summary['splits']['train']} samples
- **Val:** {summary['splits']['val']} samples
- **Test:** {summary['splits']['test']} samples

## Class Distribution
"""
        for cls, count in summary['class_distribution'].items():
            md += f"- **{cls}:** {count} samples\n"
        
        md += f"""
## License
- **Type:** {card['license']['type']}
- **Attribution:** {card['license']['attribution']}

## Provenance
- **Source:** {card['provenance']['source']}
- **Domains:** {', '.join(card['provenance']['search_domains'])}
- **Deduplication:** {card['provenance']['deduplication']}
"""
        return md


# Global publisher instance (lazy-loaded)
_card_publisher = None

def get_card_publisher():
    """Get or create the global CardPublisher instance."""
    global _card_publisher
    if _card_publisher is None:
        _card_publisher = CardPublisher()
    return _card_publisher

# Lazy accessor
class _CardPublisherAccessor:
    def __getattr__(self, name):
        return getattr(get_card_publisher(), name)

card_publisher = _CardPublisherAccessor()

import re
from typing import Dict, Any, List, Optional
from models.query import QueryFilters

class QueryAnalyser:
    """
    Identifies intent-based filters from the user's natural language question.
    Example: "What does page 5 say about X?" -> page_range: [5, 5]
    """

    def __init__(self):
        # Regex patterns for page detection
        self.page_pattern = re.compile(r'page\s+(\d+)', re.IGNORECASE)
        self.page_range_pattern = re.compile(r'pages?\s+(\d+)\s*(?:to|-)\s*(\d+)', re.IGNORECASE)

    def analyse(self, 
                question: str, 
                existing_filters: Optional[QueryFilters] = None,
                section_titles: Optional[List[str]] = None) -> QueryFilters:
        """
        Extracts filters from question and merges with existing filters.
        """
        filters = existing_filters.model_dump() if existing_filters else {
            "page_range": None,
            "section_title": None,
            "block_type": None
        }

        # 1. Page Range Extraction
        range_match = self.page_range_pattern.search(question)
        if range_match:
            start, end = map(int, range_match.groups())
            filters["page_range"] = [start, end]
        else:
            single_match = self.page_pattern.search(question)
            if single_match:
                page = int(single_match.group(1))
                filters["page_range"] = [page, page]

        # 2. Section Title Detection (Keyword matching against known sections)
        if section_titles:
            q_lower = question.lower()
            for title in section_titles:
                if title.lower() in q_lower:
                    filters["section_title"] = title
                    break

        # 3. Block Type Detection (Simple Heuristic)
        if any(kw in question.lower() for kw in ["table", "tabular", "chart"]):
            filters["block_type"] = "table"

        return QueryFilters(**filters)

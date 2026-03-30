from dataclasses import dataclass

@dataclass
class EmailAnalysis:
    category: str
    priority: str
    summary: str
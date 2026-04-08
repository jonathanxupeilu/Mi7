"""采集器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'Unknown')
        self.enabled = config.get('enabled', False)
        self.priority = config.get('priority', 'medium')
        
    @abstractmethod
    def collect(self, hours: int = 24) -> List[Dict[str, Any]]:
        """采集数据"""
        pass
        
    def is_enabled(self) -> bool:
        return self.enabled
        
    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'title': item.get('title', ''),
            'content': item.get('content', ''),
            'url': item.get('url', ''),
            'source': item.get('source', self.name),
            'source_type': self.__class__.__name__,
            'published_at': item.get('published_at', datetime.now()),
            'collected_at': datetime.now(),
            'metadata': item.get('metadata', {}),
            'priority': self.priority
        }

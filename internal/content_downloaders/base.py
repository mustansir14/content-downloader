from abc import ABC, abstractmethod
from typing import Generator

from internal.content_downloaders.types import Content

class ContentDownloader(ABC):
    """
    Abstract base class for content downloaders.
    """

    @abstractmethod
    def get_content(self) -> Generator[Content, None, None]:
        """
        Abstract method to retrieve content.
        Must be implemented by subclasses.
        """
        pass
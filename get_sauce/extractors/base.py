from abc import ABC, abstractmethod

class Extractor(ABC):
    @abstractmethod
    def can_handle(self, url, content_type=""):
        ...

    @abstractmethod
    def extract(self, url):
        ...

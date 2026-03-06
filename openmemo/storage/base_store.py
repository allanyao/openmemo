"""
Base storage interface.

All storage backends must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseStore(ABC):

    @abstractmethod
    def put_note(self, note: dict) -> str:
        pass

    @abstractmethod
    def get_note(self, note_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_notes(self, limit: int = 100, offset: int = 0) -> List[dict]:
        pass

    @abstractmethod
    def delete_note(self, note_id: str) -> bool:
        pass

    @abstractmethod
    def put_cell(self, cell: dict) -> str:
        pass

    @abstractmethod
    def get_cell(self, cell_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_cells(self, limit: int = 100, offset: int = 0) -> List[dict]:
        pass

    @abstractmethod
    def put_scene(self, scene: dict) -> str:
        pass

    @abstractmethod
    def get_scene(self, scene_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_scenes(self, limit: int = 100, offset: int = 0) -> List[dict]:
        pass

    @abstractmethod
    def put_skill(self, skill: dict) -> str:
        pass

    @abstractmethod
    def list_skills(self) -> List[dict]:
        pass

    @abstractmethod
    def close(self):
        pass

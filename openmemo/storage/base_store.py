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
    def list_notes(self, limit: int = 100, offset: int = 0, agent_id: str = None) -> List[dict]:
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
    def list_cells(self, limit: int = 100, offset: int = 0,
                   agent_id: str = None, scene: str = None) -> List[dict]:
        pass

    def list_cells_scoped(self, agent_id: str = None, conversation_id: str = None,
                          scene: str = None, limit: int = 100) -> List[dict]:
        return self.list_cells(limit=limit, agent_id=agent_id, scene=scene)

    @abstractmethod
    def delete_cell(self, cell_id: str) -> bool:
        pass

    @abstractmethod
    def put_scene(self, scene: dict) -> str:
        pass

    @abstractmethod
    def get_scene(self, scene_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_scenes(self, limit: int = 100, offset: int = 0, agent_id: str = None) -> List[dict]:
        pass

    @abstractmethod
    def put_skill(self, skill: dict) -> str:
        pass

    @abstractmethod
    def list_skills(self) -> List[dict]:
        pass

    def put_agent(self, agent: dict) -> str:
        return agent.get("agent_id", "")

    def get_agent(self, agent_id: str) -> Optional[dict]:
        return None

    def list_agents(self) -> List[dict]:
        return []

    def delete_agent(self, agent_id: str) -> bool:
        return False

    def put_conversation(self, conversation: dict) -> str:
        return conversation.get("conversation_id", "")

    def list_conversations(self, agent_id: str = None) -> List[dict]:
        return []

    def put_edge(self, edge: dict) -> str:
        return edge.get("edge_id", "")

    def get_edges(self, memory_id: str) -> List[dict]:
        return []

    def delete_edge(self, edge_id: str) -> bool:
        return False

    def list_edges(self, limit: int = 100) -> List[dict]:
        return []

    @abstractmethod
    def close(self):
        pass

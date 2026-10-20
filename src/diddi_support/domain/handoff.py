from enum import StrEnum
from uuid import UUID


class ConversationMode(StrEnum):
    AI = "ai"
    HUMAN_REQUESTED = "human_requested"
    HUMAN_ACTIVE = "human_active"


class HandoffConflictError(ValueError):
    pass


class ConversationModeService:
    def __init__(self) -> None:
        self.modes: dict[UUID, ConversationMode] = {}

    def get(self, case_id: UUID) -> ConversationMode:
        return self.modes.get(case_id, ConversationMode.AI)

    def request_human(self, case_id: UUID) -> ConversationMode:
        mode = self.get(case_id)
        if mode == ConversationMode.HUMAN_ACTIVE:
            return mode
        self.modes[case_id] = ConversationMode.HUMAN_REQUESTED
        return ConversationMode.HUMAN_REQUESTED

    def activate_human(self, case_id: UUID) -> ConversationMode:
        mode = self.get(case_id)
        if mode not in {ConversationMode.HUMAN_REQUESTED, ConversationMode.HUMAN_ACTIVE}:
            raise HandoffConflictError("HUMAN_HANDOFF_NOT_REQUESTED")
        self.modes[case_id] = ConversationMode.HUMAN_ACTIVE
        return ConversationMode.HUMAN_ACTIVE

    def can_ai_reply(self, case_id: UUID) -> bool:
        return self.get(case_id) == ConversationMode.AI

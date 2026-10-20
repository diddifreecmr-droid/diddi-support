from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from diddi_support.domain.actions import SupportAction
from diddi_support.infrastructure.persistence.repository import PostgresSupportCaseRepository


class ActionService:
    def __init__(self) -> None:
        self.actions: dict[UUID, SupportAction] = {}
        self.by_operation_key: dict[str, UUID] = {}

    def request(self, action: SupportAction) -> tuple[SupportAction, bool]:
        existing_id = self.by_operation_key.get(action.operation_key)
        if existing_id is not None:
            return self.actions[existing_id], False
        self.by_operation_key[action.operation_key] = action.id
        action.mark_pending()
        self.actions[action.id] = action
        return action, True

    def get(self, action_id: UUID) -> SupportAction | None:
        return self.actions.get(action_id)

    def get_by_operation_key(self, operation_key: str) -> SupportAction | None:
        action_id = self.by_operation_key.get(operation_key)
        return self.actions.get(action_id) if action_id else None


class PersistentActionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PostgresSupportCaseRepository(session)

    async def add(self, action: SupportAction, *, request_id: str | None = None) -> SupportAction:
        return await self.repository.add_action(action, request_id=request_id)

    async def get(self, action_id: UUID) -> SupportAction | None:
        return await self.repository.get_action(action_id)

    async def get_by_operation_key(self, operation_key: str) -> SupportAction | None:
        return await self.repository.get_action_by_operation_key(operation_key)

    async def save(self, action: SupportAction, *, request_id: str | None = None) -> SupportAction:
        return await self.repository.save_action(action, request_id=request_id)

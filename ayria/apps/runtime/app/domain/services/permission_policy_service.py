from __future__ import annotations

from pydantic import BaseModel

from app.core.config import AppConfig
from app.domain.models.tool import ToolSpec


class PermissionDecision(BaseModel):
    decision: str
    reason: str
    requires_approval: bool = False


class PermissionPolicyService:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def _policy_for_level(self, permission_level: str) -> str:
        mapping = {
            'safe_read': self._config.permission_safe_read_policy,
            'external_read': self._config.permission_external_read_policy,
            'sensitive_read': self._config.permission_sensitive_read_policy,
            'action': self._config.permission_action_policy,
            'action_or_external': self._config.permission_action_policy,
        }
        return mapping.get(permission_level, 'deny')

    def describe_tool_policy(self, tool: ToolSpec) -> dict:
        policy = self._policy_for_level(tool.permission_level)
        return {
            'permission_level': tool.permission_level,
            'data_sensitivity': tool.data_sensitivity,
            'default_policy': policy,
            'requires_confirmation': tool.requires_confirmation,
        }

    def evaluate(self, *, tool: ToolSpec, confirmed: bool) -> PermissionDecision:
        policy = self._policy_for_level(tool.permission_level)

        if policy == 'deny':
            return PermissionDecision(decision='denied', reason=f'policy_denied:{tool.permission_level}')

        if confirmed:
            return PermissionDecision(decision='allowed', reason='user_confirmed', requires_approval=False)

        if tool.requires_confirmation or policy == 'ask':
            return PermissionDecision(
                decision='approval_required',
                reason=f'approval_required:{tool.permission_level}',
                requires_approval=True,
            )

        return PermissionDecision(decision='allowed', reason='policy_allowed', requires_approval=False)

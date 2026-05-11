from __future__ import annotations

_BLOCKED_CAPABILITIES = {"targeting", "disinformation_optimization", "operational_recommendation"}



def enforce_export_policy(payload: dict[str, object]) -> None:
    if bool(payload.get("contains_personal_data")):
        raise PermissionError("Export blocked: personal data in payload")
    capability = str(payload.get("capability", "analysis"))
    if capability in _BLOCKED_CAPABILITIES:
        raise PermissionError(f"Export blocked: capability {capability} is outside MVP governance")

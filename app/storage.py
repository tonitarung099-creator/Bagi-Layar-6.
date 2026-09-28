from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QStandardPaths


DEFAULT_WORKSPACES = ["ChatGPT 6 Runner", "Kerja Harian", "Desain & Riset"]


class Storage:
    """Penyimpanan workspace dengan migrasi dari format v1 lama."""

    def __init__(self) -> None:
        base = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation))
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / "workspace.json"

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _write_raw(self, data: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def load_state(self) -> dict:
        raw = self._read_raw()
        if raw.get("version") == 2 and isinstance(raw.get("workspaces"), dict):
            raw.setdefault("active_workspace", DEFAULT_WORKSPACES[0])
            return raw

        workspaces: dict[str, dict] = {}
        if raw:
            old_name = str(raw.get("workspace") or DEFAULT_WORKSPACES[0])
            old_name = old_name.replace("▣", "").strip() or DEFAULT_WORKSPACES[0]
            workspaces[old_name] = {key: deepcopy(value) for key, value in raw.items() if key != "workspace"}
            active = old_name
        else:
            active = DEFAULT_WORKSPACES[0]

        state = {"version": 2, "active_workspace": active, "workspaces": workspaces}
        if raw:
            self._write_raw(state)
        return state

    def list_workspaces(self) -> list[str]:
        state = self.load_state()
        names = list(DEFAULT_WORKSPACES)
        for name in state["workspaces"].keys():
            if name not in names:
                names.append(name)
        return names

    def active_workspace(self) -> str:
        return str(self.load_state().get("active_workspace") or DEFAULT_WORKSPACES[0])

    def set_active_workspace(self, name: str) -> None:
        state = self.load_state()
        state["active_workspace"] = name
        self._write_raw(state)

    def get_workspace(self, name: str) -> dict:
        state = self.load_state()
        data = state["workspaces"].get(name, {})
        return deepcopy(data) if isinstance(data, dict) else {}

    def save_workspace(self, name: str, data: dict) -> None:
        state = self.load_state()
        state["active_workspace"] = name
        state["workspaces"][name] = deepcopy(data)
        self._write_raw(state)

    def create_workspace(self, name: str) -> None:
        state = self.load_state()
        state["active_workspace"] = name
        state["workspaces"].setdefault(name, {})
        self._write_raw(state)

    def load(self) -> dict:
        name = self.active_workspace()
        data = self.get_workspace(name)
        return {"workspace": name, **data} if data else {}

    def save(self, data: dict) -> None:
        payload = deepcopy(data)
        name = str(payload.pop("workspace", "") or self.active_workspace())
        name = name.replace("▣", "").strip() or DEFAULT_WORKSPACES[0]
        self.save_workspace(name, payload)

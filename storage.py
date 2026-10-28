"""
Хранилище целей отслеживания на основе JSON.
Сохраняет цели даже при перезапуске сервера.
"""

import json
import os
import threading

class Storage:
    def __init__(self, file_path: str = "targets.json"):
        self.file_path = file_path
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except Exception:
                    self.data = {"targets": {}}
            else:
                self.data = {"targets": {}}

    def _save(self):
        with self._lock:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_target(self, chat_id: int, user_id: int, username: str, nickname: str, bio: str):
        cid = str(chat_id)
        uid = str(user_id)
        if cid not in self.data["targets"]:
            self.data["targets"][cid] = []

        # Проверяем нет ли уже этой цели
        for item in self.data["targets"][cid]:
            if str(item["user_id"]) == uid:
                item["username"] = username
                item["nickname"] = nickname
                item["bio"] = bio
                self._save()
                return

        self.data["targets"][cid].append({
            "user_id": user_id,
            "username": username,
            "nickname": nickname,
            "bio": bio
        })
        self._save()

    def remove_target(self, chat_id: int, user_id: int) -> bool:
        cid = str(chat_id)
        uid = str(user_id)
        if cid in self.data["targets"]:
            initial_len = len(self.data["targets"][cid])
            self.data["targets"][cid] = [
                item for item in self.data["targets"][cid] if str(item["user_id"]) != uid
            ]
            if len(self.data["targets"][cid]) < initial_len:
                self._save()
                return True
        return False

    def get_targets(self, chat_id: int) -> list:
        cid = str(chat_id)
        return self.data["targets"].get(cid, [])

    def get_subscribers_for_target(self, user_id: int) -> list:
        """Возвращает список chat_id, которые отслеживают данного пользователя"""
        uid = str(user_id)
        subscribers = []
        for cid, targets in self.data["targets"].items():
            for t in targets:
                if str(t["user_id"]) == uid:
                    subscribers.append(int(cid))
                    break
        return subscribers

    def get_target_by_id(self, user_id: int) -> dict:
        uid = str(user_id)
        for cid, targets in self.data["targets"].items():
            for t in targets:
                if str(t["user_id"]) == uid:
                    return t
        return None

    def get_all_tracked_user_ids(self) -> set:
        """Возвращает множество всех уникальных ID отслеживаемых целей"""
        uids = set()
        for cid, targets in self.data["targets"].items():
            for t in targets:
                uids.add(t["user_id"])
        return uids

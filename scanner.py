import asyncio
import os
from pikpakapi import PikPakApi
from dotenv import load_dotenv
from database import upsert_files, mark_folder_done, is_folder_scanned

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class PikPakScanner:
    def __init__(self):
        self.client = PikPakApi(
            username=os.getenv("PIKPAK_USERNAME", ""),
            password=os.getenv("PIKPAK_PASSWORD", ""),
        )
        self.is_scanning = False
        self.should_stop = False
        self.scanned_files = 0
        self.scanned_folders = 0
        self.current_path = ""
        self._listeners: list = []

    def add_listener(self, callback):
        self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def _notify(self, event: dict):
        for cb in self._listeners:
            try:
                await cb(event)
            except Exception:
                pass

    async def login(self):
        await self.client.login()

    async def scan(self, full_rescan: bool = False):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.should_stop = False
        self.scanned_files = 0
        self.scanned_folders = 0

        try:
            await self.login()
            # Pre-load cached counts for incremental scan
            from database import get_file_count, get_scanned_folder_count
            self.scanned_files = await get_file_count()
            self.scanned_folders = await get_scanned_folder_count()
            await self._notify({"type": "started"})
            await self._scan_folder(parent_id="", path="/", skip_scanned=not full_rescan)
            # Refresh final counts from DB
            self.scanned_files = await get_file_count()
            self.scanned_folders = await get_scanned_folder_count()
            await self._notify({
                "type": "completed",
                "files": self.scanned_files,
                "folders": self.scanned_folders,
            })
        except Exception as e:
            await self._notify({"type": "error", "message": str(e)})
        finally:
            self.is_scanning = False

    async def stop(self):
        self.should_stop = True

    async def _scan_folder(self, parent_id: str, path: str, skip_scanned: bool = True):
        if self.should_stop:
            return

        folder_key = parent_id if parent_id else "root"

        if skip_scanned and await is_folder_scanned(folder_key):
            return

        self.current_path = path
        next_page_token = None
        child_folders = []
        batch = []

        while True:
            if self.should_stop:
                break

            try:
                result = await self.client.file_list(
                    parent_id=parent_id or None,
                    size=100,
                    next_page_token=next_page_token,
                )
            except Exception as e:
                await self._notify({"type": "error", "message": f"Error listing {path}: {e}"})
                await asyncio.sleep(2)
                continue

            files = result.get("files", [])
            for f in files:
                file_record = {
                    "id": f["id"],
                    "name": f.get("name", ""),
                    "size": int(f.get("size", 0)),
                    "mime_type": f.get("mime_type", ""),
                    "kind": f.get("kind", ""),
                    "parent_id": f.get("parent_id", parent_id),
                    "path": path + f.get("name", ""),
                    "created_time": f.get("created_time", ""),
                }
                batch.append(file_record)

                if "folder" in f.get("kind", ""):
                    child_folders.append((f["id"], path + f["name"] + "/"))
                else:
                    self.scanned_files += 1

            if batch:
                await upsert_files(batch)
                batch = []

            await self._notify({
                "type": "progress",
                "files": self.scanned_files,
                "folders": self.scanned_folders,
                "current_path": self.current_path,
            })

            next_page_token = result.get("next_page_token")
            if not next_page_token:
                break

        await mark_folder_done(folder_key)
        self.scanned_folders += 1

        # Recurse into child folders with concurrency control
        sem = asyncio.Semaphore(3)

        async def scan_child(folder_id, folder_path):
            async with sem:
                await self._scan_folder(folder_id, folder_path, skip_scanned)

        tasks = [scan_child(fid, fpath) for fid, fpath in child_folders]
        await asyncio.gather(*tasks)

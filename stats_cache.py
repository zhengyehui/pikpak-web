"""Pre-compute all stats once, serve from memory."""

from database import get_all_files, get_all_folders


class StatsCache:
    def __init__(self):
        self._ready = False
        # Raw data
        self._files: list[dict] = []
        self._folders: list[dict] = []
        # Pre-computed
        self.size_distribution: list[dict] = []
        self.type_distribution: list[dict] = []
        self.top_files: list[dict] = []
        self.top_folders: list[dict] = []
        # Treemap tree: folder_id -> {children, direct_size, recursive_size, ...}
        self._folder_name: dict[str, str] = {}
        self._folder_path: dict[str, str] = {}
        self._children_of: dict[str, list[str]] = {}
        self._recursive_size: dict[str, int] = {}
        self._recursive_count: dict[str, int] = {}
        self._direct_size: dict[str, int] = {}
        self._direct_count: dict[str, int] = {}

    @property
    def ready(self):
        return self._ready

    async def rebuild(self):
        """Rebuild all caches from DB. Call after scan or on startup."""
        self._files = await get_all_files()
        self._folders = await get_all_folders()
        self._build_tree()
        self._build_size_distribution()
        self._build_type_distribution()
        self._build_top_files()
        self._build_top_folders()
        self._ready = True

    def _build_tree(self):
        self._folder_name.clear()
        self._folder_path.clear()
        self._children_of.clear()
        self._recursive_size.clear()
        self._recursive_count.clear()
        self._direct_size.clear()
        self._direct_count.clear()

        self._children_of[""] = []

        for folder in self._folders:
            fid = folder["id"]
            pid = folder.get("parent_id", "") or ""
            self._folder_name[fid] = folder["name"]
            self._folder_path[fid] = folder.get("path", "")
            if pid not in self._children_of:
                self._children_of[pid] = []
            self._children_of[pid].append(fid)
            if fid not in self._children_of:
                self._children_of[fid] = []

        for f in self._files:
            pid = f.get("parent_id", "") or ""
            self._direct_size[pid] = self._direct_size.get(pid, 0) + f["size"]
            self._direct_count[pid] = self._direct_count.get(pid, 0) + 1

        # Bottom-up recursive calc
        def calc(fid: str) -> tuple[int, int]:
            if fid in self._recursive_size:
                return self._recursive_size[fid], self._recursive_count[fid]
            size = self._direct_size.get(fid, 0)
            count = self._direct_count.get(fid, 0)
            for child_id in self._children_of.get(fid, []):
                cs, cc = calc(child_id)
                size += cs
                count += cc
            self._recursive_size[fid] = size
            self._recursive_count[fid] = count
            return size, count

        calc("")
        for fid in self._folder_name:
            calc(fid)

    def get_treemap(self, parent_id: str = "") -> dict:
        children = []
        for child_id in self._children_of.get(parent_id, []):
            rsize = self._recursive_size.get(child_id, 0)
            if rsize > 0:
                children.append({
                    "id": child_id,
                    "name": self._folder_name.get(child_id, "?"),
                    "value": rsize,
                    "file_count": self._recursive_count.get(child_id, 0),
                    "has_children": len(self._children_of.get(child_id, [])) > 0,
                    "path": self._folder_path.get(child_id, ""),
                })

        loose = self._direct_size.get(parent_id, 0)
        if loose > 0:
            children.append({
                "id": "__files__",
                "name": "[文件]",
                "value": loose,
                "file_count": self._direct_count.get(parent_id, 0),
                "has_children": False,
                "path": "",
            })

        children.sort(key=lambda x: x["value"], reverse=True)

        return {
            "id": parent_id,
            "name": self._folder_name.get(parent_id, "PikPak") if parent_id else "PikPak",
            "total_size": self._recursive_size.get(parent_id, 0),
            "children": children,
        }

    def _build_size_distribution(self):
        buckets = [
            ("< 1 MB", 0, 1_048_576),
            ("1-10 MB", 1_048_576, 10_485_760),
            ("10-100 MB", 10_485_760, 104_857_600),
            ("100 MB-1 GB", 104_857_600, 1_073_741_824),
            ("1-5 GB", 1_073_741_824, 5_368_709_120),
            ("5-10 GB", 5_368_709_120, 10_737_418_240),
            ("> 10 GB", 10_737_418_240, float("inf")),
        ]
        self.size_distribution = []
        for label, lo, hi in buckets:
            count = sum(1 for f in self._files if lo <= f["size"] < hi)
            total = sum(f["size"] for f in self._files if lo <= f["size"] < hi)
            self.size_distribution.append({"label": label, "count": count, "total_size": total})

    def _build_type_distribution(self):
        categories = {
            "视频": ["video/"],
            "图片": ["image/"],
            "音频": ["audio/"],
            "文档": ["application/pdf", "application/msword", "application/vnd.", "text/"],
            "压缩包": ["application/zip", "application/x-rar", "application/x-7z", "application/x-tar", "application/gzip"],
        }
        result: dict[str, dict] = {}
        for f in self._files:
            mime = f.get("mime_type", "") or ""
            matched = False
            for cat, prefixes in categories.items():
                if any(mime.startswith(p) for p in prefixes):
                    if cat not in result:
                        result[cat] = {"count": 0, "total_size": 0}
                    result[cat]["count"] += 1
                    result[cat]["total_size"] += f["size"]
                    matched = True
                    break
            if not matched:
                if "其他" not in result:
                    result["其他"] = {"count": 0, "total_size": 0}
                result["其他"]["count"] += 1
                result["其他"]["total_size"] += f["size"]
        self.type_distribution = [{"name": k, **v} for k, v in result.items()]

    def _build_top_files(self):
        self.top_files = sorted(self._files, key=lambda f: f["size"], reverse=True)[:100]

    def _build_top_folders(self):
        ranked = []
        for fid in self._folder_name:
            rsize = self._recursive_size.get(fid, 0)
            if rsize > 0:
                ranked.append({
                    "id": fid,
                    "name": self._folder_name[fid],
                    "path": self._folder_path.get(fid, ""),
                    "size": rsize,
                    "file_count": self._recursive_count.get(fid, 0),
                })
        ranked.sort(key=lambda x: x["size"], reverse=True)
        self.top_folders = ranked[:100]

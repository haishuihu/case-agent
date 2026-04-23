from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChangedFile:
    filename: str
    status: str  # added / modified / deleted
    additions: int = 0
    deletions: int = 0


@dataclass
class ParsedDiff:
    changed_files: list[ChangedFile] = field(default_factory=list)
    added_lines: int = 0
    deleted_lines: int = 0
    modified_functions: list[str] = field(default_factory=list)
    api_changes: list[str] = field(default_factory=list)


class CodeAnalyzer:
    """解析 Git Diff，提取变更文件、函数、行数等结构化信息"""

    def parse_diff(self, git_diff: str) -> ParsedDiff:
        """解析 Git Diff，返回结构化的变更信息"""
        if not git_diff:
            return ParsedDiff()

        result = ParsedDiff()
        lines = git_diff.split("\n")

        current_file: Optional[str] = None
        current_status: Optional[str] = None
        diff_start = -1  # 当前 diff 块开始位置

        # ---- 第一遍：收集所有 diff --git 块信息 ----
        for i, line in enumerate(lines):
            if line.startswith("diff --git"):
                diff_start = i
                # 解析 diff --git a/src/foo.py b/src/foo.py
                m = re.match(r"diff --git a/(.+?) b/(.+?)(?:\s*$|\s)", line)
                if m:
                    current_file = m.group(2)
                    current_status = None
                continue

            if diff_start < 0:
                continue

            # 处理 new file / deleted file
            if line.startswith("new file mode"):
                current_status = "added"
                continue
            if line.startswith("deleted file mode"):
                current_status = "deleted"
                continue

            # 遇到下一个 diff --git 或文件结束，重置状态
            if line.startswith("diff --git"):
                diff_start = i
                m = re.match(r"diff --git a/(.+?) b/(.+?)(?:\s*$|\s)", line)
                if m:
                    current_file = m.group(2)
                    current_status = None
                continue

            # 处理 --- /dev/null / --- a/src/foo.py
            if line.startswith("--- "):
                path_part = line[4:].strip()
                if path_part == "/dev/null":
                    # 新文件
                    current_status = "added"
                else:
                    current_status = None  # 重置为 modified

            # 处理 +++ b/src/foo.py
            if line.startswith("+++ "):
                path_part = line[4:].strip()
                if path_part == "/dev/null":
                    # 删除文件
                    current_status = "deleted"
                elif path_part.startswith("b/"):
                    inferred = path_part[2:]
                    if inferred and inferred != current_file:
                        current_file = inferred

            # @@ 函数签名行
            hm = re.search(r"@@ [-\d]+(?:,\d+)? \+(\d+)(?:,(\d+))? @@(.*)$", line)
            if hm and hm.group(3):
                func = hm.group(3).strip()
                if func:
                    result.modified_functions.append(func)

            # +行统计
            if line.startswith("+") and not line.startswith("+++"):
                result.added_lines += 1
            # -行统计
            if line.startswith("-") and not line.startswith("---"):
                result.deleted_lines += 1

        # ---- 第二遍：提取文件变更列表 ----
        # 遍历 diff --git 块
        for m in re.finditer(r"diff --git a/(.+?) b/(.+?)(?:\s*$|\s)", git_diff, re.MULTILINE):
            fname = m.group(2)
            status = "modified"
            # 在 diff 块前后各 300 字符内查找 new/delete 标记（new file mode 出现在 diff --git 之后）
            start = m.start()
            search_end = start + 300
            search_window = git_diff[start:search_end]
            if "new file mode" in search_window or "new file" in search_window:
                status = "added"
            elif "deleted file mode" in search_window or "deleted file" in search_window:
                status = "deleted"
            result.changed_files.append(ChangedFile(filename=fname, status=status))

        return result

    def extract_api_changes(self, git_diff: str) -> list[str]:
        """从 Diff 中识别 API 签名变更"""
        changes: list[str] = []
        patterns = [
            (r"(GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}]+)", "HTTP路由变更"),
            (r"def\s+(\w+)\s*\(", "函数签名变更"),
            (r"class\s+(\w+)\s*[:(]", "类定义变更"),
            (r"async\s+def\s+(\w+)\s*\(", "异步函数签名变更"),
            (r"interface\s+(\w+)", "接口定义变更"),
            (r"^\s*\"(\w+)\":", "JSON字段变更"),
        ]

        for pattern, desc in patterns:
            for m in re.finditer(pattern, git_diff, re.MULTILINE):
                changes.append(f"[{desc}] {m.group(1)}")

        # 去重
        seen = set()
        unique: list[str] = []
        for c in changes:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique[:50]

    def get_changed_modules(self, parsed: ParsedDiff) -> list[str]:
        """从变更文件中提取模块名列表"""
        modules: list[str] = []
        for f in parsed.changed_files:
            parts = f.filename.replace("\\", "/").split("/")
            if len(parts) >= 2:
                modules.append(f"{parts[-2]}/{parts[-1]}")
            elif len(parts) == 1:
                modules.append(parts[0])
        return list(dict.fromkeys(modules))  # 去重保持顺序

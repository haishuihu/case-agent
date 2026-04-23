from __future__ import annotations

import ast
import os
import re
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModuleEdge:
    caller: str
    callee: str
    edge_type: str = "calls"  # calls / imports / inherits


@dataclass
class ImpactPath:
    module: str
    depth: int
    path_type: str  # direct / indirect
    via_modules: list[str] = field(default_factory=list)


class CodeBaseAnalyzer:
    """
    基于 AST 的 Python 代码分析器。
    从源码目录中提取模块、函数、类及其调用关系，构建真实的依赖图。
    """

    def __init__(self, source_root: Optional[str] = None):
        self.source_root = source_root or self._detect_source_root()
        self._cache: Optional[dict] = None

    def _detect_source_root(self) -> str:
        """尝试自动检测源码根目录"""
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", ".."),
            os.path.join(os.path.dirname(__file__), "..", "..", ".."),
        ]
        for candidate in candidates:
            resolved = os.path.abspath(candidate)
            if os.path.isdir(resolved):
                return resolved
        return os.getcwd()

    def analyze_directory(self, root: Optional[str] = None) -> dict:
        """
        分析源码目录，返回模块依赖关系。

        Returns:
            {
                "modules": {"module_name": {"file": "...", "functions": [...], "classes": [...]}},
                "edges": [("caller_module", "callee_module"), ...],
                "function_calls": [("caller_file", "caller_func", "callee_func"), ...],
            }
        """
        root_dir = root or self.source_root
        if not os.path.isdir(root_dir):
            return {"modules": {}, "edges": [], "function_calls": []}

        modules: dict = {}
        edges: list = []
        function_calls: list = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in (
                "node_modules", "__pycache__", ".venv", "venv", ".git", "dist", "build", "htmlcov"
            )]

            for filename in filenames:
                if not filename.endswith(".py") or filename.startswith("_"):
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    result = self._analyze_file(filepath, root_dir)
                    if result:
                        module_name = result["module"]
                        modules[module_name] = result
                        edges.extend(result.get("module_edges", []))
                        function_calls.extend(result.get("function_calls", []))
                except Exception:
                    continue

        return {
            "modules": modules,
            "edges": list(dict.fromkeys(edges)),
            "function_calls": function_calls,
        }

    def _analyze_file(self, filepath: str, root: str) -> Optional[dict]:
        """使用 AST 解析单个 Python 文件"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            return None

        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return None

        module_name = self._filepath_to_module(filepath, root)
        functions: list[dict] = []
        classes: list[dict] = []
        imports: list[str] = []
        local_calls: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "methods": methods,
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                callee = self._get_call_name(node.func)
                if callee and not callee.startswith("_"):
                    local_calls.append(callee)

        rel_path = os.path.relpath(filepath, root)
        module_parts = rel_path.replace(os.sep, "/").split("/")
        if len(module_parts) > 1:
            module_dir = "/".join(module_parts[:-1])
        else:
            module_dir = ""

        module_edges = []
        for imp in imports:
            imp_parts = imp.split(".")
            if imp_parts[0] not in ("sys", "os", "re", "json", "logging", "typing", "datetime", "uuid", "hashlib"):
                module_edges.append((module_dir or module_name, imp_parts[0]))

        return {
            "module": module_name,
            "file": filepath,
            "rel_path": rel_path,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "local_calls": list(dict.fromkeys(local_calls)),
            "module_edges": module_edges,
            "function_calls": [],
        }

    def _filepath_to_module(self, filepath: str, root: str) -> str:
        """将文件路径转换为模块名"""
        rel = os.path.relpath(filepath, root)
        parts = rel.replace(os.sep, "/").split("/")
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")
        return "/".join(parts)

    def _get_call_name(self, node: ast.AST) -> str:
        """从 AST 节点获取被调用名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        elif isinstance(node, ast.Subscript):
            return self._get_call_name(node.value)
        return ""


class CodeGraphBuilder:
    """
    基于真实代码分析构建 DependencyGraph。
    使用 AST 分析源码目录，自动构建模块间调用关系图。
    """

    def __init__(self, source_root: Optional[str] = None):
        self.analyzer = CodeBaseAnalyzer(source_root)

    def build_graph(self) -> DependencyGraph:
        """
        分析源码目录，生成 DependencyGraph。

        Returns:
            DependencyGraph: 包含真实代码依赖关系的图
        """
        graph = DependencyGraph()
        analysis = self.analyzer.analyze_directory()

        # 添加真实模块依赖边
        for caller, callee in analysis["edges"]:
            if caller and callee and caller != callee:
                graph.add_edge(caller, callee, edge_type="imports")

        # 如果图太小（真实代码分析结果少），补充种子数据
        if len(graph._forward) < 5:
            _seed_default_edges(graph)

        return graph


class DependencyGraph:
    """
    模块依赖关系图谱（内存存储）。

    支持：
    - 添加依赖关系（add_edge）
    - 查找受影响的模块（get_impacted_modules，BFS遍历）
    - 获取调用链（get_call_chain）
    - 获取关键路径模块（高频出现在调用链中的模块）
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # caller -> set of callees
        self._forward: dict[str, set[str]] = defaultdict(set)
        # callee -> set of callers
        self._reverse: dict[str, set[str]] = defaultdict(set)
        self._edge_count: dict[tuple[str, str], int] = defaultdict(int)

    def add_edge(self, caller: str, callee: str, edge_type: str = "calls") -> None:
        """添加一条依赖关系"""
        with self._lock:
            self._forward[caller].add(callee)
            self._reverse[callee].add(caller)
            self._edge_count[(caller, callee)] += 1

    def add_module_edges(self, module: str, depends_on: list[str]) -> None:
        """添加一个模块及其依赖列表"""
        for dep in depends_on:
            self.add_edge(module, dep)

    def get_impacted_modules(
        self,
        changed_modules: list[str],
        max_depth: int = 3,
    ) -> list[ImpactPath]:
        """给定变更模块，返回所有受影响的模块及其路径"""
        with self._lock:
            result: list[ImpactPath] = []
            visited: dict[str, int] = {}

            # BFS: 从变更模块出发，沿调用方向向外扩散
            queue: list[tuple[str, int, list[str]]] = [
                (m, 0, []) for m in changed_modules
            ]

            while queue:
                current, depth, via = queue.pop(0)
                if depth > max_depth:
                    continue
                if current in visited and visited[current] <= depth:
                    continue
                visited[current] = depth

                is_direct = depth == 0
                result.append(ImpactPath(
                    module=current,
                    depth=depth,
                    path_type="direct" if is_direct else "indirect",
                    via_modules=via.copy(),
                ))

                for callee in self._forward.get(current, set()):
                    if callee not in visited or visited[callee] > depth + 1:
                        new_via = via + [current]
                        queue.append((callee, depth + 1, new_via))

            return result

    def get_call_chain(self, module: str, direction: str = "downstream", max_depth: int = 5) -> list[str]:
        """
        获取从指定模块出发的调用链。

        direction: 'downstream' (该模块调用了谁) 或 'upstream' (谁调用了该模块)
        """
        with self._lock:
            chain: list[str] = [module]
            visited: set[str] = {module}
            queue: list[tuple[str, int]] = [(module, 0)]

            while queue:
                current, depth = queue.pop(0)
                if depth >= max_depth:
                    continue

                neighbors = (
                    self._forward.get(current, set()) if direction == "downstream"
                    else self._reverse.get(current, set())
                )

                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        chain.append(neighbor)
                        queue.append((neighbor, depth + 1))

            return chain

    def get_key_path_modules(self, top_n: int = 10) -> list[str]:
        """返回被依赖最多的模块（高风险核心模块）"""
        with self._lock:
            incoming_count = {m: len(callers) for m, callers in self._reverse.items()}
            sorted_modules = sorted(incoming_count.items(), key=lambda x: x[1], reverse=True)
            return [m for m, _ in sorted_modules[:top_n]]

    def to_dict(self) -> dict:
        """导出依赖图（用于调试/序列化）"""
        with self._lock:
            return {
                "nodes": list(self._forward.keys()),
                "edges": [
                    {"from": c, "to": callee}
                    for c, callees in self._forward.items()
                    for callee in callees
                ],
                "key_modules": self.get_key_path_modules(),
            }


# 全局单例：进程内复用依赖图
_global_graph: Optional[DependencyGraph] = None
_graph_lock = threading.Lock()


def get_dependency_graph() -> DependencyGraph:
    """
    获取全局单例依赖图。

    优先尝试从真实代码库构建依赖图；若分析失败或数据不足，
    则使用预置的种子数据作为兜底。
    """
    global _global_graph
    with _graph_lock:
        if _global_graph is None:
            try:
                builder = CodeGraphBuilder()
                _global_graph = builder.build_graph()
            except Exception:
                _global_graph = DependencyGraph()
                _seed_default_edges(_global_graph)
        return _global_graph


def _seed_default_edges(g: DependencyGraph) -> None:
    """
    预置通用模块依赖关系种子数据。

    仅在真实代码分析结果不足时作为兜底使用。
    覆盖常见的业务模块依赖关系，可按项目实际需求扩展。
    """
    seed = [
        ("auth", ["database", "cache", "logging"]),
        ("user", ["auth", "database", "cache"]),
        ("order", ["user", "payment", "inventory", "notification"]),
        ("payment", ["order", "billing", "notification"]),
        ("notification", ["messaging", "logging"]),
        ("billing", ["payment", "invoice"]),
        ("inventory", ["warehouse", "order"]),
        ("api", ["auth", "user", "order"]),
        ("service", ["database", "cache", "logging"]),
        ("model", ["database"]),
        ("utils", ["logging"]),
    ]
    for caller, callees in seed:
        for callee in callees:
            g.add_edge(caller, callee)

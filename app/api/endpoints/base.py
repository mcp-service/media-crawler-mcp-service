# -*- coding: utf-8 -*-
"""Decorator-friendly blueprint used by API endpoint modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from starlette.routing import BaseRoute, Mount, Route

RegisteredTool = Tuple[str, Callable]

_blueprints: List["MCPBlueprint"] = []


def get_registered_blueprints() -> Iterable["MCPBlueprint"]:
    """Return the registered blueprints."""
    return tuple(_blueprints)


def get_tools_summary() -> Dict[str, Any]:
    """Aggregate MCP tool information across all blueprints."""
    categories: Dict[str, List[str]] = {}
    total_tools = 0

    for bp in _blueprints:
        tools = bp.tools_info or []
        if not tools:
            continue
        names = [tool.name for tool in tools]
        if not names:
            continue
        categories.setdefault(bp.category, [])
        categories[bp.category].extend(names)
        total_tools += len(names)

    return {
        "categories": categories,
        "total_tools": total_tools,
        "blueprints_count": len(_blueprints),
    }


@dataclass
class RouteInfo:
    path: str
    methods: Optional[List[str]]
    name: str
    kind: str = "route"  # route or mount


@dataclass
class ToolInfo:
    name: str
    description: Optional[str]
    http_path: Optional[str]
    http_methods: List[str]


class MCPBlueprint:
    """Collect HTTP routes and MCP tools via decorators."""

    def __init__(
        self,
        prefix: str = "",
        *,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> None:
        normalized_prefix = prefix.rstrip("/")
        if normalized_prefix and not normalized_prefix.startswith("/"):
            normalized_prefix = f"/{normalized_prefix}"

        self.prefix = normalized_prefix
        self.name = name or (self.prefix.strip("/") or "root")
        self.tags = tags or []
        self.category = category or self.name
        self._routes: List[BaseRoute] = []
        self._routes_info: List[RouteInfo] = []
        self._tools: List[RegisteredTool] = []
        self._tools_info: List[ToolInfo] = []

        if self not in _blueprints:
            _blueprints.append(self)

    @property
    def routes(self) -> List[BaseRoute]:
        return list(self._routes)

    @property
    def routes_info(self) -> List[RouteInfo]:
        return list(self._routes_info)

    @property
    def tools(self) -> List[RegisteredTool]:
        return list(self._tools)

    @property
    def tools_info(self) -> List[ToolInfo]:
        return list(self._tools_info)

    def route(
        self,
        path: str,
        methods: Optional[List[str]] = None,
        *,
        name: Optional[str] = None,
    ) -> Callable[[Callable], Callable]:
        """Decorator registering a Starlette route."""
        methods = methods or ["GET"]
        route_name = name or ""

        def deco(fn: Callable) -> Callable:
            full_path = f"{self.prefix}{path}"
            self._routes.append(Route(full_path, fn, methods=methods, name=route_name or None))
            self._routes_info.append(
                RouteInfo(path=full_path, methods=list(methods), name=route_name or fn.__name__)
            )
            return fn

        return deco

    def mount(self, path: str, app, *, name: Optional[str] = None) -> None:
        """Register a Starlette Mount route."""
        full_path = f"{self.prefix}{path}"
        self._routes.append(Mount(full_path, app=app, name=name))
        self._routes_info.append(RouteInfo(path=full_path, methods=None, name=name or app.__class__.__name__, kind="mount"))

    def tool(
        self,
        name: Optional[str] = None,
        *,
        description: Optional[str] = None,
        http_path: Optional[str] = None,
        http_methods: Optional[List[str]] = None,
    ) -> Callable[[Callable], Callable]:
        """Decorator registering an MCP tool."""

        def deco(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            self._tools.append((tool_name, fn))
            self._tools_info.append(
                ToolInfo(
                    name=tool_name,
                    description=description,
                    http_path=f"{self.prefix}{http_path}" if http_path else None,
                    http_methods=http_methods or [],
                )
            )
            return fn

        return deco

    def install(self, mcp, asgi_app) -> None:
        """Install collected routes and tools to the MCP/Starlette apps."""
        for tool_name, fn in self._tools:
            mcp.tool(name=tool_name)(fn)

        asgi_app.router.routes.extend(self._routes)

    def summary(self) -> Dict[str, Any]:
        """Return metadata summary for this blueprint."""
        return {
            "name": self.name,
            "category": self.category,
            "prefix": self.prefix,
            "tags": self.tags,
            "routes": [
                {
                    "path": info.path,
                    "methods": info.methods or [],
                    "kind": info.kind,
                }
                for info in self._routes_info
            ],
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "http_path": tool.http_path,
                    "http_methods": tool.http_methods,
                }
                for tool in self._tools_info
            ],
        }

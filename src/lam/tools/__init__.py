from __future__ import annotations

from lam.rag.graph_store import GraphStore
from lam.tools.calculator import CALCULATOR_TOOL
from lam.tools.file_reader import FILE_READER_TOOL
from lam.tools.graph_tools import build_graph_tool
from lam.tools.registry import Tool


def default_tools(graph: GraphStore | None = None) -> list[Tool]:
    tools = [CALCULATOR_TOOL, FILE_READER_TOOL]
    if graph is not None:
        tools.append(build_graph_tool(graph))
    return tools

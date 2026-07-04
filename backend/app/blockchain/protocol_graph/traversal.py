"""Protocol graph traversal utilities (M8.2)."""

from __future__ import annotations

from collections import deque

from app.blockchain.protocol_graph.models import ProtocolGraph


class ProtocolGraphTraversal:
    """Traversal helpers over a protocol dependency graph."""

    def __init__(self, graph: ProtocolGraph) -> None:
        self._graph = graph
        self._outgoing = graph.adjacency_map
        self._incoming = _build_reverse_adjacency(graph)

    @property
    def root(self) -> str:
        return self._graph.root_node

    def neighbors(self, address: str) -> tuple[str, ...]:
        return self._outgoing.get(address.lower(), ())

    def bfs(self, start: str | None = None) -> tuple[str, ...]:
        origin = (start or self.root).lower()
        if origin not in {node.address for node in self._graph.nodes}:
            return ()
        visited: list[str] = []
        seen = {origin}
        queue = deque([origin])
        while queue:
            current = queue.popleft()
            visited.append(current)
            for neighbor in self.neighbors(current):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        return tuple(visited)

    def dfs(self, start: str | None = None) -> tuple[str, ...]:
        origin = (start or self.root).lower()
        if origin not in {node.address for node in self._graph.nodes}:
            return ()
        visited: list[str] = []
        seen: set[str] = set()

        def _walk(node: str) -> None:
            if node in seen:
                return
            seen.add(node)
            visited.append(node)
            for neighbor in self.neighbors(node):
                _walk(neighbor)

        _walk(origin)
        return tuple(visited)

    def topological_sort(self) -> tuple[str, ...]:
        indegree = {node.address: 0 for node in self._graph.nodes}
        for source, targets in self._outgoing.items():
            for target in targets:
                if target in indegree:
                    indegree[target] += 1
        queue = deque(sorted(address for address, degree in indegree.items() if degree == 0))
        ordering: list[str] = []
        while queue:
            current = queue.popleft()
            ordering.append(current)
            for neighbor in self.neighbors(current):
                if neighbor not in indegree:
                    continue
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        if len(ordering) != len(indegree):
            return ()
        return tuple(ordering)

    def ancestors(self, address: str) -> tuple[str, ...]:
        normalized = address.lower()
        collected: list[str] = []
        seen: set[str] = set()
        stack = list(self._incoming.get(normalized, ()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            collected.append(current)
            stack.extend(self._incoming.get(current, ()))
        return tuple(sorted(collected))

    def descendants(self, address: str) -> tuple[str, ...]:
        normalized = address.lower()
        collected: list[str] = []
        seen: set[str] = set()
        stack = list(self.neighbors(normalized))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            collected.append(current)
            stack.extend(self.neighbors(current))
        return tuple(sorted(collected))

    def shortest_path(self, source: str, target: str) -> tuple[str, ...] | None:
        start = source.lower()
        end = target.lower()
        if start == end:
            return (start,)
        queue = deque([(start, [start])])
        seen = {start}
        while queue:
            current, path = queue.popleft()
            for neighbor in self.neighbors(current):
                if neighbor in seen:
                    continue
                next_path = path + [neighbor]
                if neighbor == end:
                    return tuple(next_path)
                seen.add(neighbor)
                queue.append((neighbor, next_path))
        return None

    def disconnected_from_root(self) -> list[str]:
        reachable = set(self.bfs(self.root))
        return [node.address for node in self._graph.nodes if node.address not in reachable]

    def find_cycles(self) -> tuple[tuple[str, ...], ...]:
        cycles: list[tuple[str, ...]] = []
        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []

        def _visit(node: str) -> None:
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in self.neighbors(node):
                if neighbor not in visited:
                    _visit(neighbor)
                elif neighbor in stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(tuple(path[cycle_start:] + [neighbor]))
            stack.remove(node)
            path.pop()

        for node in sorted(node.address for node in self._graph.nodes):
            if node not in visited:
                _visit(node)
        return tuple(sorted(cycles))

    def is_dag(self) -> bool:
        return bool(self.topological_sort())


def _build_reverse_adjacency(graph: ProtocolGraph) -> dict[str, tuple[str, ...]]:
    incoming: dict[str, set[str]] = {node.address: set() for node in graph.nodes}
    for source, targets in graph.adjacency_map.items():
        for target in targets:
            incoming.setdefault(target, set()).add(source)
    return {address: tuple(sorted(parents)) for address, parents in incoming.items()}

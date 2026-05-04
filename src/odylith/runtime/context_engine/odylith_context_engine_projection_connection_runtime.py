"""In-memory projection connection for Context Engine snapshot reads."""

from __future__ import annotations

from typing import Any

context_engine_store: Any = None


def _context_engine_store() -> Any:
    global context_engine_store
    if context_engine_store is None:
        from odylith.runtime.context_engine import odylith_context_engine_store as loaded_store

        context_engine_store = loaded_store
    return context_engine_store


class ProjectionConnection:
    def __init__(self, *, repo_root: Path, snapshot: Mapping[str, Any]) -> None:
        _context_engine_store()
        self.repo_root = context_engine_store.Path(repo_root).resolve()
        raw_tables = snapshot.get("tables", {}) if isinstance(snapshot, context_engine_store.Mapping) else {}
        self._tables = {
            str(name).strip(): [dict(row) for row in rows if isinstance(row, context_engine_store.Mapping)]
            for name, rows in raw_tables.items()
            if str(name).strip() and isinstance(rows, list)
        }

    def close(self) -> None:
        return None

    def commit(self) -> None:
        return None

    def table_rows(self, table_name: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._tables.get(str(table_name).strip(), [])]

    def has_table(self, table_name: str) -> bool:
        return str(table_name).strip() in self._tables

    def execute(self, query: str, params: Sequence[Any] = ()) -> _ProjectionCursor:
        normalized = " ".join(str(query or "").strip().split())
        rows = self._select_rows(normalized, tuple(params))
        return context_engine_store._ProjectionCursor(rows)

    def _select_rows(self, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        if not query:
            return []
        if query.startswith("SELECT COUNT(*) AS row_count FROM "):
            table_name = str(query.partition("FROM ")[2]).strip()
            return [{"row_count": len(self.table_rows(table_name))}]
        if " GROUP BY " in query and "COUNT(*) AS " in query:
            grouped = self._select_grouped_rows(query=query)
            if grouped is not None:
                return grouped
        if "WHERE (source_kind = ? AND source_id = ?)" in query and "OR (target_kind = ? AND target_id = ?)" in query:
            return self._select_traceability_bidirectional(query=query, params=params)
        return self._select_rows_generic(query=query, params=params)

    def _select_grouped_rows(self, *, query: str) -> list[dict[str, Any]] | None:
        match = context_engine_store.re.match(
            r"^SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s+GROUP BY\s+(.+?)(?:\s+HAVING\s+COUNT\(\*\)\s*>\s*(\d+))?$",
            query,
        )
        if match is None:
            return None
        select_clause = str(match.group(1) or "").strip()
        table_name = str(match.group(2) or "").strip()
        group_clause = str(match.group(3) or "").strip()
        having_threshold = int(str(match.group(4) or "0").strip() or 0)
        select_terms = [str(token).strip() for token in select_clause.split(",") if str(token).strip()]
        group_fields = [str(token).strip() for token in group_clause.split(",") if str(token).strip()]
        count_alias = ""
        projected_fields: list[str] = []
        for term in select_terms:
            count_match = context_engine_store.re.match(r"^COUNT\(\*\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)$", term, flags=context_engine_store.re.IGNORECASE)
            if count_match is not None:
                count_alias = str(count_match.group(1) or "").strip()
                continue
            projected_fields.append(term)
        if not group_fields or not count_alias:
            return None
        grouped_rows: dict[tuple[str, ...], dict[str, Any]] = {}
        grouped_counts: dict[tuple[str, ...], int] = {}
        for row in self.table_rows(table_name):
            key = tuple(str(row.get(field, "")).strip() for field in group_fields)
            grouped_counts[key] = grouped_counts.get(key, 0) + 1
            if key in grouped_rows:
                continue
            grouped_rows[key] = {field: row.get(field) for field in projected_fields or group_fields}
        results: list[dict[str, Any]] = []
        for key in sorted(grouped_rows):
            count = grouped_counts.get(key, 0)
            if count <= having_threshold:
                continue
            projected = dict(grouped_rows[key])
            projected[count_alias] = count
            results.append(projected)
        return results

    def _select_traceability_bidirectional(self, *, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        relation_limit = int(params[4] or 0) if len(params) >= 5 else 0
        source_kind, source_id, target_kind, target_id = (
            str(params[0] or "").strip(),
            str(params[1] or "").strip(),
            str(params[2] or "").strip(),
            str(params[3] or "").strip(),
        )
        rows = [
            dict(row)
            for row in self.table_rows("traceability_edges")
            if (
                str(row.get("source_kind", "")).strip() == source_kind
                and str(row.get("source_id", "")).strip() == source_id
            )
            or (
                str(row.get("target_kind", "")).strip() == target_kind
                and str(row.get("target_id", "")).strip() == target_id
            )
        ]
        rows.sort(
            key=lambda row: (
                str(row.get("relation", "")),
                str(row.get("source_kind", "")),
                str(row.get("source_id", "")),
                str(row.get("target_kind", "")),
                str(row.get("target_id", "")),
            )
        )
        return rows[: max(1, relation_limit)] if relation_limit else rows

    def _select_rows_generic(self, *, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        match = context_engine_store.re.match(r"^SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", query)
        if match is None:
            return []
        select_clause = str(match.group(1) or "").strip()
        table_name = str(match.group(2) or "").strip()
        remainder = str(match.group(3) or "").strip()
        where_clause = ""
        order_clause = ""
        limit_clause = ""
        if remainder.startswith("WHERE "):
            where_clause = remainder[6:]
            for token in (" ORDER BY ", " LIMIT "):
                if token in where_clause:
                    where_clause, trailer = where_clause.split(token, 1)
                    if token.strip() == "ORDER BY":
                        order_clause = trailer
                    else:
                        limit_clause = trailer
                    break
        elif remainder.startswith("ORDER BY "):
            order_clause = remainder[9:]
        elif remainder.startswith("LIMIT "):
            limit_clause = remainder[6:]
        if order_clause and " LIMIT " in order_clause:
            order_clause, limit_clause = order_clause.split(" LIMIT ", 1)
        rows = self.table_rows(table_name)
        rows = self._apply_where(rows=rows, where_clause=where_clause, params=params)
        rows = self._apply_order(rows=rows, table_name=table_name, order_clause=order_clause)
        rows = self._apply_limit(rows=rows, limit_clause=limit_clause, params=params)
        return [self._project_row(row=row, select_clause=select_clause) for row in rows]

    def _apply_where(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        where_clause: str,
        params: tuple[Any, ...],
    ) -> list[dict[str, Any]]:
        clause = str(where_clause or "").strip()
        if not clause:
            return [dict(row) for row in rows]
        parts = [part.strip() for part in context_engine_store.re.split(r"\s+AND\s+", clause) if part.strip()]
        param_index = 0
        predicates: list[Any] = []
        for part in parts:
            match_lower = context_engine_store.re.match(r"^lower\(([A-Za-z_][A-Za-z0-9_]*)\)\s*=\s*(.+)$", part)
            if match_lower is not None:
                field = str(match_lower.group(1) or "").strip()
                rhs = str(match_lower.group(2) or "").strip()
                if rhs == "?":
                    value = str(params[param_index] if param_index < len(params) else "").strip().casefold()
                    param_index += 1
                else:
                    value = rhs.strip("'").casefold()
                predicates.append(lambda row, f=field, v=value: str(row.get(f, "")).strip().casefold() == v)
                continue
            match_eq = context_engine_store.re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", part)
            if match_eq is not None:
                field = str(match_eq.group(1) or "").strip()
                rhs = str(match_eq.group(2) or "").strip()
                if rhs == "?":
                    value = str(params[param_index] if param_index < len(params) else "").strip()
                    param_index += 1
                else:
                    value = rhs.strip("'")
                predicates.append(lambda row, f=field, v=value: str(row.get(f, "")).strip() == v)
                continue
            match_in = context_engine_store.re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+IN\s+\((.+)\)$", part)
            if match_in is not None:
                field = str(match_in.group(1) or "").strip()
                rhs = str(match_in.group(2) or "").strip()
                values: list[str] = []
                if "?" in rhs:
                    placeholder_count = rhs.count("?")
                    values = [
                        str(item).strip()
                        for item in params[param_index : param_index + placeholder_count]
                        if str(item).strip()
                    ]
                    param_index += placeholder_count
                else:
                    values = [token.strip().strip("'") for token in rhs.split(",") if token.strip().strip("'")]
                allowed = set(values)
                predicates.append(lambda row, f=field, a=allowed: str(row.get(f, "")).strip() in a)
                continue
        filtered = [dict(row) for row in rows]
        for predicate in predicates:
            filtered = [row for row in filtered if predicate(row)]
        return filtered

    def _apply_order(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        table_name: str,
        order_clause: str,
    ) -> list[dict[str, Any]]:
        clause = str(order_clause or "").strip()
        ordered = [dict(row) for row in rows]
        if not clause:
            return ordered
        if table_name == "workstreams" and "CASE" in clause and "rank" in clause:
            ordered.sort(
                key=lambda row: (
                    999999
                    if str(row.get("rank", "")).strip() == "-"
                    else int(str(row.get("rank", "")).strip())
                    if str(row.get("rank", "")).strip().isdigit()
                    else 999999,
                    str(row.get("idea_id", "")),
                )
            )
            return ordered
        terms = [term.strip() for term in clause.split(",") if term.strip()]
        for term in reversed(terms):
            pieces = term.split()
            field = str(pieces[0] or "").strip()
            descending = len(pieces) > 1 and str(pieces[1] or "").strip().upper() == "DESC"
            ordered.sort(key=lambda row, f=field: self._sortable_value(row.get(f)), reverse=descending)
        return ordered

    def _apply_limit(
        self,
        *,
        rows: Sequence[Mapping[str, Any]],
        limit_clause: str,
        params: tuple[Any, ...],
    ) -> list[dict[str, Any]]:
        clause = str(limit_clause or "").strip()
        if not clause:
            return [dict(row) for row in rows]
        if clause == "?":
            limit_value = int(params[-1] or 0) if params else 0
        else:
            try:
                limit_value = int(clause)
            except ValueError:
                limit_value = 0
        return [dict(row) for row in rows[: max(0, limit_value)]] if limit_value > 0 else [dict(row) for row in rows]

    def _project_row(self, *, row: Mapping[str, Any], select_clause: str) -> dict[str, Any]:
        clause = str(select_clause or "").strip()
        if clause == "*":
            return dict(row)
        columns = [str(token).strip() for token in clause.split(",") if str(token).strip()]
        return {column: row.get(column) for column in columns}

    @staticmethod
    def _sortable_value(value: Any) -> Any:
        if isinstance(value, (int, float)):
            return value
        token = str(value or "").strip()
        if token.isdigit():
            return int(token)
        return token

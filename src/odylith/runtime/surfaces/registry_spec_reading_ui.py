"""Registry specification disclosure, prose and table reading layout."""


def css() -> str:
    """Keep prose within the disclosure and horizontal scrolling local to tables."""
    return """
.spec-expand {
  border: 1px solid #d6e3f7;
  border-radius: 10px;
  background: linear-gradient(180deg, #f9fcff, #ffffff);
  overflow: hidden;
}
.spec-expand > summary {
  list-style: none;
  cursor: pointer;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border-bottom: 1px solid #e3ecf9;
  transition: background-color 120ms ease;
}
.spec-expand > summary:hover {
  background: #f3f8ff;
}
.spec-summary-main {
  margin: 0;
  display: flex;
  align-items: center;
}
.spec-summary-meta {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  align-items: center;
}
.spec-expand[open] > summary {
  border-bottom-color: #d8e5f7;
}
.spec-expand-body {
  padding: 10px 12px;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}
.spec-links-block {
  display: grid;
  gap: 6px;
}
.spec-doc {
  min-width: 0;
  overflow-wrap: anywhere;
  grid-template-columns: minmax(0, 1fr);
  border: 1px solid #e3ecf9;
  border-radius: 8px;
  background: #ffffff;
  padding: 10px;
  display: grid;
  gap: 8px;
}
.spec-doc h3,
.spec-doc h4,
.spec-doc h5 {
  margin: 0;
}
.spec-doc p {
  margin: 0;
}
.spec-doc ul {
  margin: 0;
  padding-left: 18px;
  display: block;
  list-style: disc;
}
.spec-doc li {
  margin: 0 0 4px;
}
.spec-doc li:last-child {
  margin-bottom: 0;
}
.spec-doc li > ul {
  margin-top: 4px;
  padding-left: 18px;
  list-style-type: circle;
}
.spec-doc li > ul > li > ul {
  list-style-type: square;
}
.spec-doc code {
  background: #f3f6fb;
  border: 1px solid #d9e6fa;
  border-radius: 4px;
  padding: 0 4px;
}
.spec-table-scroll {
  overflow-x: auto;
  border: 1px solid #dbe6f7;
  border-radius: 8px;
  background: #f8fbff;
}
.spec-table {
  width: 100%;
  min-width: 640px;
  border-collapse: collapse;
  background: #ffffff;
}
.spec-table th,
.spec-table td {
  padding: 8px 10px;
  vertical-align: top;
  text-align: left;
  border-bottom: 1px solid #dbe6f7;
  border-right: 1px solid #e3ecf9;
}
.spec-table th:last-child,
.spec-table td:last-child {
  border-right: 0;
}
.spec-table thead th {
  background: #f1f6ff;
  white-space: nowrap;
}
.spec-table tbody tr:last-child td {
  border-bottom: 0;
}
""".strip()

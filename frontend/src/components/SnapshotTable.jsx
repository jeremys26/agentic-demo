import { Box, Button, Typography } from "@mui/material";

function cellText(value) {
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function SnapshotTable({ table, purpose, onPage }) {
  if (!table) return null;
  const columns = table.columns || [];
  const rows = table.rows || [];
  const from = table.total === 0 ? 0 : table.offset + 1;
  const to = table.offset + rows.length;
  const canPrev = table.offset > 0;
  const canNext = to < table.total;

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 2, mb: 1, flexWrap: "wrap" }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontWeight: 700, fontSize: 15, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
            {table.db_table}
          </Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            model {table.model}
            {table.database ? ` · database ${table.database}` : ""}
            {purpose ? ` — ${purpose}` : ""}
          </Typography>
        </Box>
        <Typography sx={{ fontSize: 12, color: "text.secondary", whiteSpace: "nowrap" }}>
          {table.total === 0 ? "0 rows" : `Showing ${from}–${to} of ${table.total}`}
        </Typography>
      </Box>
      <Box
        sx={{
          overflowX: "auto",
          border: "1px solid rgba(20, 22, 31, 0.08)",
          borderRadius: 2,
          backgroundColor: "#fff",
        }}
      >
        <Box
          component="table"
          sx={{
            borderCollapse: "collapse",
            width: "max-content",
            minWidth: "100%",
            fontSize: 13,
            "& th, & td": {
              padding: "8px 12px",
              borderBottom: "1px solid rgba(20, 22, 31, 0.08)",
              textAlign: "left",
              whiteSpace: "nowrap",
              maxWidth: 320,
              overflow: "hidden",
              textOverflow: "ellipsis",
            },
            "& th": {
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              color: "text.secondary",
              backgroundColor: "#F4F5FC",
              position: "sticky",
              top: 0,
            },
            "& tr:last-of-type td": { borderBottom: "none" },
          }}
        >
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.name} title={`${col.type}${col.primary_key ? " · PK" : ""}${col.nullable ? " · nullable" : ""}`}>
                  {col.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(columns.length, 1)} style={{ color: "#5B6270" }}>
                  No rows in this snapshot.
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={row.id ?? index}>
                  {columns.map((col) => {
                    const text = cellText(row[col.name]);
                    return (
                      <td key={col.name} title={text}>
                        {text}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </Box>
      </Box>
      {(canPrev || canNext) && onPage && (
        <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
          <Button size="small" variant="outlined" disabled={!canPrev} onClick={() => onPage(Math.max(table.offset - table.limit, 0))}>
            Previous
          </Button>
          <Button size="small" variant="outlined" disabled={!canNext} onClick={() => onPage(table.offset + table.limit)}>
            Next
          </Button>
        </Box>
      )}
    </Box>
  );
}

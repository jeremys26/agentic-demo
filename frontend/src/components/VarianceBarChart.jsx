import { useState } from "react";
import { useNavigate } from "react-router-dom";

// Horizontal bars, one per campaign, comparing CPL variance vs. target across
// the whole portfolio at a glance — the Overview page's answer to "which
// campaigns need attention" without opening each one. Color follows the
// same three-state read as StatusPill's tones (good/neutral/flagged), not a
// categorical hue, since it's one measure's magnitude, not identity.
const GOOD = "#166534";
const WATCH = "#5B6270";
const FLAGGED = "#B42318";

function colorFor(variancePct) {
  if (variancePct == null) return WATCH;
  if (variancePct > 15) return FLAGGED;
  if (variancePct <= 0) return GOOD;
  return WATCH;
}

const ROW_HEIGHT = 32;
const WIDTH = 760;
const LABEL_W = 230;
const CHART_RIGHT_PAD = 56;

export default function VarianceBarChart({ campaigns }) {
  const [hoverId, setHoverId] = useState(null);
  const navigate = useNavigate();

  const sorted = [...campaigns]
    .filter((c) => c.cpl_variance_pct != null)
    .sort((a, b) => b.cpl_variance_pct - a.cpl_variance_pct);

  if (sorted.length === 0) {
    return (
      <div style={{ fontSize: 14, color: "#5B6270" }}>
        No campaign performance to chart yet.
      </div>
    );
  }

  const maxAbs = Math.max(15, ...sorted.map((c) => Math.abs(c.cpl_variance_pct)));
  const barAreaW = WIDTH - LABEL_W - CHART_RIGHT_PAD;
  const scale = (v) => (Math.abs(v) / maxAbs) * (barAreaW / 2);
  const zeroX = LABEL_W + barAreaW / 2;
  const height = sorted.length * ROW_HEIGHT + 8;

  return (
    <div>
      <p style={{ fontSize: 13, color: "#5B6270", margin: "0 0 12px", lineHeight: 1.55 }}>
        Last 7 days vs. each campaign&apos;s target cost per lead. Right of center is over target;
        red means more than 15% over — that&apos;s the flag. Click a campaign to open it.
      </p>
    <svg
      viewBox={`0 0 ${WIDTH} ${height}`}
      width="100%"
      role="img"
      aria-label="CPL variance by campaign"
      style={{ display: "block", height: "auto", maxWidth: "100%" }}
    >
      {/* Zero/target reference line */}
      <line x1={zeroX} x2={zeroX} y1={0} y2={height} stroke="rgba(20, 22, 31, 0.15)" strokeWidth={1} />
      {sorted.map((c, i) => {
        const y = i * ROW_HEIGHT + 8;
        const w = scale(c.cpl_variance_pct);
        const color = colorFor(c.cpl_variance_pct);
        const isPositive = c.cpl_variance_pct >= 0;
        const barX = isPositive ? zeroX : zeroX - w;
        const hovered = hoverId === c.id;
        return (
          <g
            key={c.id}
            onMouseEnter={() => setHoverId(c.id)}
            onMouseLeave={() => setHoverId(null)}
            onClick={() => navigate(`/campaigns/${c.id}/show`)}
            style={{ cursor: "pointer" }}
          >
            <title>{c.name}</title>
            <text
              x={LABEL_W - 12}
              y={y + 15}
              textAnchor="end"
              fontSize={12}
              fontWeight={hovered ? 700 : 500}
              fill="#14161F"
            >
              {c.name.length > 32 ? `${c.name.slice(0, 30)}…` : c.name}
            </text>
            <rect x={barX} y={y + 4} width={Math.max(w, 1.5)} height={16} rx={3} fill={color} opacity={hovered ? 1 : 0.85} />
            <text
              x={isPositive ? barX + w + 8 : barX - 8}
              y={y + 15}
              textAnchor={isPositive ? "start" : "end"}
              fontSize={12}
              fontWeight={600}
              fill={color}
            >
              {c.cpl_variance_pct > 0 ? "+" : ""}
              {c.cpl_variance_pct.toFixed(0)}%
            </text>
          </g>
        );
      })}
    </svg>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 12, fontSize: 12, color: "#5B6270" }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: GOOD }} />
          At or under target
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: WATCH }} />
          Up to 15% over
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: FLAGGED }} />
          Flagged — more than 15% over
        </span>
      </div>
    </div>
  );
}

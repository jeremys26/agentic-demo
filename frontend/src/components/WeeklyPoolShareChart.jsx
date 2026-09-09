import { useMemo, useState } from "react";

// Percentage-stacked weekly bars showing call volume shifting between pools
// over time — this is the direct visual proof of PLANNING.md §9's headline
// finding ("call volume quietly shifting into a lower-converting,
// non-certified pool"), which a single current-state snapshot can't show.
// Color carries identity here (which pool), so it's categorical, not
// sequential — fixed order, always legended since there are 2+ series.

const CERTIFIED_COLOR = "#0A21C7"; // brand — "the pool this is supposed to go to"
const UNCERTIFIED_COLOR = "#B42318"; // reserved "critical" red — this is the pool the scenario flags

const WIDTH = 640;
const HEIGHT = 220;
const PAD = { top: 8, right: 16, bottom: 40, left: 40 };

function weekBucketsFromEvents(events, pools) {
  if (events.length === 0) return [];
  const sorted = [...events].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const start = new Date(sorted[0].timestamp);

  const buckets = new Map(); // weekIndex -> { poolId: count, total }
  for (const ev of sorted) {
    const days = Math.floor((new Date(ev.timestamp) - start) / 86400000);
    const weekIdx = Math.floor(days / 7);
    if (!buckets.has(weekIdx)) buckets.set(weekIdx, { total: 0, byPool: {} });
    const bucket = buckets.get(weekIdx);
    bucket.total += 1;
    bucket.byPool[ev.routed_pool] = (bucket.byPool[ev.routed_pool] || 0) + 1;
  }

  const weekStart = (idx) => {
    const d = new Date(start);
    d.setUTCDate(d.getUTCDate() + idx * 7);
    return d;
  };

  return [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([idx, bucket]) => ({
      label: weekStart(idx).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" }),
      total: bucket.total,
      segments: pools.map((p) => ({
        poolId: p.id,
        name: p.name,
        certified: p.is_certified_medicare,
        count: bucket.byPool[p.id] || 0,
        pct: bucket.total ? ((bucket.byPool[p.id] || 0) / bucket.total) * 100 : 0,
      })),
    }));
}

export default function WeeklyPoolShareChart({ events, pools }) {
  const [hover, setHover] = useState(null);

  const weeks = useMemo(() => weekBucketsFromEvents(events, pools), [events, pools]);
  if (weeks.length === 0) return null;

  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const barW = Math.min(72, (innerW / weeks.length) * 0.55);
  const slot = innerW / weeks.length;

  return (
    <div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width="100%"
        style={{ display: "block", height: "auto" }}
        role="img"
        aria-label="Weekly call share by pool"
      >
        {[0, 50, 100].map((pct) => (
          <g key={pct}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={PAD.top + innerH * (1 - pct / 100)}
              y2={PAD.top + innerH * (1 - pct / 100)}
              stroke="rgba(20, 22, 31, 0.08)"
              strokeWidth={1}
            />
            <text x={PAD.left - 8} y={PAD.top + innerH * (1 - pct / 100) + 4} textAnchor="end" fontSize={11} fill="#5B6270">
              {pct}%
            </text>
          </g>
        ))}

        {weeks.map((week, i) => {
          const x = PAD.left + slot * i + (slot - barW) / 2;
          let cumulativeY = PAD.top + innerH;
          return (
            <g key={i} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              {week.segments.map((seg) => {
                const segH = innerH * (seg.pct / 100);
                cumulativeY -= segH;
                const color = seg.certified ? CERTIFIED_COLOR : UNCERTIFIED_COLOR;
                return (
                  <rect
                    key={seg.poolId}
                    x={x}
                    y={cumulativeY}
                    width={barW}
                    height={Math.max(segH, 0)}
                    fill={color}
                    opacity={hover === null || hover === i ? 0.92 : 0.4}
                  />
                );
              })}
              <text x={x + barW / 2} y={PAD.top + innerH + 18} textAnchor="middle" fontSize={11} fill="#5B6270">
                {week.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend — always present for 2+ series */}
      <div style={{ display: "flex", gap: 20, marginTop: 8, fontSize: 12, color: "#5B6270", flexWrap: "wrap" }}>
        {pools.map((p) => (
          <span key={p.id} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                backgroundColor: p.is_certified_medicare ? CERTIFIED_COLOR : UNCERTIFIED_COLOR,
                display: "inline-block",
              }}
            />
            {p.name} {p.is_certified_medicare ? "(certified)" : "(not certified)"}
          </span>
        ))}
      </div>

      {hover != null && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#14161F" }}>
          <strong>Week of {weeks[hover].label}</strong> — {weeks[hover].total} calls:{" "}
          {weeks[hover].segments.map((s) => `${s.name} ${s.pct.toFixed(0)}%`).join(", ")}
        </div>
      )}
    </div>
  );
}

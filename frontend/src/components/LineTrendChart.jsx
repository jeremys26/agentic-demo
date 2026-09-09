import { useMemo, useState } from "react";

// Generic single-series trend line with an optional dashed reference line —
// used for CPL vs. target (campaigns.jsx) and CTR vs. first-week baseline
// (creatives.jsx). One series never needs a legend box (the chart's own
// heading names it); the reference line carries its own inline label
// instead of a second legend entry.

const WIDTH = 720;
const HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 28, left: 56 };

const LINE_COLOR_DEFAULT = "#0A21C7"; // brand primary.dark
const REFERENCE_COLOR = "#5B6270"; // text.secondary — a threshold, not a second series

function formatDate(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}

export default function LineTrendChart({
  data,
  valueFormat = (v) => v.toFixed(2),
  yTickFormat = valueFormat,
  referenceLine,
  lineColor = LINE_COLOR_DEFAULT,
  ariaLabel,
}) {
  const [hoverIdx, setHoverIdx] = useState(null);

  const { points, yScale, xScale, minY, maxY } = useMemo(() => {
    const values = data.map((d) => d.value);
    const refValue = referenceLine?.value;
    const lo = Math.min(refValue != null ? refValue : values[0], ...values);
    const hi = Math.max(refValue != null ? refValue : values[0], ...values);
    const span = hi - lo || Math.abs(hi) * 0.1 || 1;
    const minY = lo - span * 0.12;
    const maxY = hi + span * 0.12;

    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = HEIGHT - PAD.top - PAD.bottom;

    const xScale = (i) => PAD.left + (data.length === 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
    const yScale = (v) => PAD.top + innerH - ((v - minY) / (maxY - minY)) * innerH;

    const points = data.map((d, i) => ({ x: xScale(i), y: yScale(d.value), ...d }));
    return { points, yScale, xScale, minY, maxY };
  }, [data, referenceLine]);

  if (data.length === 0) return null;

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${(HEIGHT - PAD.bottom).toFixed(1)} L ${points[0].x.toFixed(1)} ${(HEIGHT - PAD.bottom).toFixed(1)} Z`;
  const fillColor = `${lineColor}14`; // ~8% tint

  // Tick values live in data-space (minY/maxY from the scale above), each
  // mapped through yScale for pixel position — not reverse-looked-up from a
  // point's pixel y, which only matches an actual data point by coincidence.
  const yTicks = [maxY, (minY + maxY) / 2, minY].map((value) => ({ y: yScale(value), value }));
  const xTickIdxs = data.length > 1 ? [0, Math.floor((data.length - 1) / 2), data.length - 1] : [0];

  const hovered = hoverIdx != null ? points[hoverIdx] : null;

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let best = Infinity;
    points.forEach((p, i) => {
      const dist = Math.abs(p.x - px);
      if (dist < best) {
        best = dist;
        nearest = i;
      }
    });
    setHoverIdx(nearest);
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width="100%"
        style={{ display: "block", height: "auto" }}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
        role="img"
        aria-label={ariaLabel || `Trend over ${data.length} days`}
      >
        {/* Recessive horizontal gridlines + value labels (dedupe close ticks) */}
        {[...new Map(yTicks.map((t) => [t.y.toFixed(0), t])).values()].map((t, i) => (
          <g key={i}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={t.y} y2={t.y} stroke="rgba(20, 22, 31, 0.08)" strokeWidth={1} />
            <text x={PAD.left - 8} y={t.y + 4} textAnchor="end" fontSize={11} fill="#5B6270">
              {yTickFormat(t.value)}
            </text>
          </g>
        ))}

        {xTickIdxs.map((i) => (
          <text key={i} x={xScale(i)} y={HEIGHT - PAD.bottom + 18} textAnchor="middle" fontSize={11} fill="#5B6270">
            {formatDate(data[i].date)}
          </text>
        ))}

        {referenceLine && (
          <>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={yScale(referenceLine.value)}
              y2={yScale(referenceLine.value)}
              stroke={referenceLine.color || REFERENCE_COLOR}
              strokeWidth={1.5}
              strokeDasharray="4 4"
            />
            <text
              x={WIDTH - PAD.right}
              y={yScale(referenceLine.value) - 6}
              textAnchor="end"
              fontSize={11}
              fill={referenceLine.color || REFERENCE_COLOR}
              fontWeight={600}
            >
              {referenceLine.label}
            </text>
          </>
        )}

        <path d={areaPath} fill={fillColor} stroke="none" />
        <path d={linePath} fill="none" stroke={lineColor} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {hovered && (
          <>
            <line x1={hovered.x} x2={hovered.x} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="rgba(20, 22, 31, 0.25)" strokeWidth={1} />
            <circle cx={hovered.x} cy={hovered.y} r={4} fill={lineColor} stroke="#FFFFFF" strokeWidth={1.5} />
          </>
        )}
      </svg>

      {hovered && (
        <div
          style={{
            position: "absolute",
            left: `${Math.min(Math.max((hovered.x / WIDTH) * 100, 12), 88)}%`,
            top: 4,
            transform: "translateX(-50%)",
            background: "#14161F",
            color: "#FFFFFF",
            borderRadius: 8,
            padding: "6px 10px",
            fontSize: 12,
            pointerEvents: "none",
            whiteSpace: "nowrap",
            boxShadow: "0 4px 12px rgba(20, 22, 31, 0.25)",
          }}
        >
          <div style={{ fontWeight: 700 }}>{formatDate(hovered.date)}</div>
          <div>{valueFormat(hovered.value)}</div>
        </div>
      )}
    </div>
  );
}

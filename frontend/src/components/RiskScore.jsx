import StatusPill from "./StatusPill";
import { formatRisk, riskColor } from "../labels";

const HINT =
  "0–100. Below 30 can run on its own; 30–70 waits for you; 70+ is blocked. A hard safety cap can still hold a low score for review.";

export default function RiskScore({ score, breakdown, showHardCap = true }) {
  const label = formatRisk(score);
  if (label == null) return "—";

  const hardCap = showHardCap && Boolean(breakdown?.hard_cap_exceeded);

  return (
    <span
      title={hardCap ? `${HINT} This one was held by the hard safety cap.` : HINT}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: riskColor(score),
        fontWeight: 700,
        fontVariantNumeric: "tabular-nums",
        whiteSpace: "nowrap",
        verticalAlign: "middle",
      }}
    >
      {label}
      {hardCap ? <StatusPill label="Hard cap" tone="warning" /> : null}
    </span>
  );
}

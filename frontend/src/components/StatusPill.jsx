// Shared status-pill component: a colored dot + label pill, used by both
// the Campaigns and Agent Actions list/show views so status styling lives
// in one place instead of being hand-rolled per resource. Soft tint
// background + colored text + a small leading dot — the "status chip with
// dot" pattern common across modern dashboard UIs (Linear, GitHub, Vercel),
// not tied to any one product's branding.

const TONES = {
  success: { fg: "#166534", bg: "#DCFCE7" },
  warning: { fg: "#9A6700", bg: "#FEF3C7" },
  error: { fg: "#B42318", bg: "#FEE4E2" },
  info: { fg: "#0A21C7", bg: "rgba(13, 43, 255, 0.08)" },
  neutral: { fg: "#5B6270", bg: "#EEF0F4" },
};

export default function StatusPill({ label, tone = "neutral" }) {
  const { fg, bg } = TONES[tone] || TONES.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 10px 3px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        color: fg,
        backgroundColor: bg,
        whiteSpace: "nowrap",
        lineHeight: 1.6,
        verticalAlign: "middle",
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: fg,
          opacity: 0.85,
          flexShrink: 0,
        }}
      />
      {label}
    </span>
  );
}

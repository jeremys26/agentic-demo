// A small rounded-square colored icon badge, used as a leading visual on
// table rows (channel type, action type) — the "colored icon chip per row"
// pattern common in modern file/list UIs, helping a row be scanned by
// shape/color before reading the text.

export default function IconTag({ icon, color = "#5B6270", bg }) {
  const background = bg || `${color}1A`; // ~10% tint of the icon color
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 26,
        height: 26,
        borderRadius: 7,
        backgroundColor: background,
        color,
        flexShrink: 0,
        verticalAlign: "middle",
      }}
    >
      {icon}
    </span>
  );
}

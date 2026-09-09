import { Box, Card, CardContent, Typography, Tooltip } from "@mui/material";
import IconTag from "./IconTag";

// Plain-language "what am I looking at?" banner for the four platform
// explorers. The tables already existed; they didn't say what a row *is*.
//
// Term definitions used to render as a permanent grid under the summary —
// full defs, always on screen, for every row whether you needed them or
// not. Now the terms themselves sit inline in the summary line as
// dotted-underline hover targets; the definition only appears in a Tooltip
// when someone actually points at the term. Same `terms` prop shape, so
// none of the four call sites needed to change.
const Term = ({ term, def }) => (
  <Tooltip title={def} arrow enterDelay={200} leaveDelay={100}>
    <Box
      component="span"
      tabIndex={0}
      sx={{
        textDecoration: "underline dotted",
        textUnderlineOffset: 3,
        cursor: "help",
        fontWeight: 600,
        color: "text.primary",
        "&:focus-visible": { outline: "2px solid", outlineOffset: 2, outlineColor: "primary.main" },
      }}
    >
      {term}
    </Box>
  </Tooltip>
);

export default function ResourceExplainer({ icon, color, platform, role, summary, terms }) {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
        <Box sx={{ display: "flex", gap: 1.5, alignItems: "flex-start" }}>
          <IconTag icon={icon} color={color} />
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontWeight: 700, fontSize: 15 }}>
              {platform}{" "}
              <Typography component="span" sx={{ fontWeight: 400, color: "text.secondary", fontSize: 14 }}>
                — {role}
              </Typography>
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.6 }}>
              {summary}
            </Typography>
            {terms?.length > 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, lineHeight: 1.8 }}>
                Terms:{" "}
                {terms.map((t, i) => (
                  <span key={t.term}>
                    <Term term={t.term} def={t.def} />
                    {i < terms.length - 1 ? "  ·  " : ""}
                  </span>
                ))}
              </Typography>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

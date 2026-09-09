import { useState } from "react";
import { Box, Card, CardContent, Collapse, Typography } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

// Shared collapsible-header pattern for every major page section, plus
// (via layout="row") dense nested items like a single MCP tool. One place
// to keep "click header to toggle, chevron shows state, content unmounts
// while collapsed" consistent instead of every page hand-rolling it.
// Controlled (pass `expanded` + `onToggle`) when a page needs to force-open
// a section from a quick-nav link; uncontrolled (`defaultExpanded` only)
// otherwise.
export default function Collapsible({
  id,
  title,
  subtitle,
  action,
  expanded: expandedProp,
  defaultExpanded = true,
  onToggle,
  children,
  layout = "card",
}) {
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);
  const expanded = expandedProp ?? internalExpanded;

  const toggle = () => {
    if (onToggle) onToggle(!expanded);
    else setInternalExpanded((prev) => !prev);
  };

  const header = (
    <Box
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      }}
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
        cursor: "pointer",
        userSelect: "none",
        mb: expanded ? (layout === "row" ? 1 : 2) : 0,
        outline: "none",
        borderRadius: 1,
        "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main", outlineOffset: 2 },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
        <ExpandMoreIcon
          fontSize={layout === "plain" ? "medium" : "small"}
          sx={{
            color: "text.secondary",
            flexShrink: 0,
            transform: expanded ? "rotate(0deg)" : "rotate(-90deg)",
            transition: "transform 0.15s ease",
          }}
        />
        <Box sx={{ minWidth: 0 }}>
          {typeof title === "string" && layout === "plain" ? (
            <Typography variant="h5" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {title}
            </Typography>
          ) : typeof title === "string" ? (
            <Typography
              sx={{
                fontSize: layout === "card" ? "1.1rem" : 14,
                fontWeight: layout === "card" ? 500 : 700,
                fontFamily: layout === "card" ? '"Fraunces", Georgia, serif' : undefined,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {title}
            </Typography>
          ) : (
            title
          )}
          {subtitle && !expanded ? (
            <Typography
              sx={{ fontSize: 12, color: "text.secondary", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            >
              {subtitle}
            </Typography>
          ) : null}
        </Box>
      </Box>
      {action ? (
        <Box onClick={(e) => e.stopPropagation()} sx={{ flexShrink: 0 }}>
          {action}
        </Box>
      ) : null}
    </Box>
  );

  if (layout === "row") {
    return (
      <Box sx={{ py: 1.5, borderBottom: "1px solid rgba(20, 22, 31, 0.08)", "&:last-of-type": { borderBottom: "none" } }} id={id}>
        {header}
        <Collapse in={expanded} timeout={200} unmountOnExit>
          <Box sx={{ pl: 3, pt: 0.5 }}>{children}</Box>
        </Collapse>
      </Box>
    );
  }

  if (layout === "plain") {
    return (
      <Box component="section" id={id} sx={{ mb: 5, scrollMarginTop: 80 }}>
        {header}
        <Collapse in={expanded} timeout={200} unmountOnExit>
          {children}
        </Collapse>
      </Box>
    );
  }

  return (
    <Card sx={{ mb: 3, scrollMarginTop: 72 }} id={id}>
      <CardContent sx={{ pb: expanded ? undefined : "16px !important" }}>
        {header}
        <Collapse in={expanded} timeout={200} unmountOnExit>
          {children}
        </Collapse>
      </CardContent>
    </Card>
  );
}

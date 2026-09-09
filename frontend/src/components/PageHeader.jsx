import { Box, Typography, Link as MuiLink } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export default function PageHeader({ title, subtitle, backTo, backLabel }) {
  return (
    <Box sx={{ mb: 2.5 }}>
      {backTo ? (
        <MuiLink
          component={RouterLink}
          to={backTo}
          sx={{ fontSize: 13, fontWeight: 600, display: "inline-block", mb: 0.75 }}
        >
          ← {backLabel || "Back"}
        </MuiLink>
      ) : null}
      <Typography variant="h5" sx={{ fontFamily: '"Fraunces", Georgia, serif' }}>
        {title}
      </Typography>
      {subtitle ? (
        <Typography sx={{ fontSize: 14, color: "text.secondary", mt: 0.75, lineHeight: 1.65, maxWidth: 720 }}>
          {subtitle}
        </Typography>
      ) : null}
    </Box>
  );
}

export const JUMP_CHIP_SX = {
  fontSize: 13,
  fontWeight: 600,
  background: "rgba(20, 22, 31, 0.05)",
  border: 0,
  cursor: "pointer",
  borderRadius: 999,
  px: 1.5,
  py: 0.5,
  textDecoration: "none",
  color: "text.primary",
  "&:hover": { background: "rgba(20, 22, 31, 0.09)" },
};

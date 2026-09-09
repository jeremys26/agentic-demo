import { Box, Typography } from "@mui/material";

export default function CodeBlock({ label, file, children }) {
  if (!children) return null;
  return (
    <Box sx={{ minWidth: 0 }}>
      {(label || file) && (
        <Typography
          sx={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: "text.secondary",
            mb: 0.75,
          }}
        >
          {label}
          {file ? (
            <Typography component="span" sx={{ fontWeight: 500, textTransform: "none", letterSpacing: 0, ml: 1 }}>
              {file}
            </Typography>
          ) : null}
        </Typography>
      )}
      <pre>{children}</pre>
    </Box>
  );
}

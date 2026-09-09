import { createTheme } from "@mui/material/styles";

// A restrained, dashboard-appropriate theme — not a clone of any site's
// branding. Pulls a handful of structural cues from BMG360's public
// marketing site (their accent blue, sampled at #0D2BFF; the serif-headline
// + grotesk-body font pairing; generous line-height on headings) and
// re-implements them with fonts we actually hold a license for — BMG360's
// own typefaces (Signifier, Founders Grotesk) are commercial Klim Type
// Foundry fonts, not reproduced here. No logo, no copied marketing copy or
// layout.
const BRAND_BLUE = "#0D2BFF";
const HEADLINE_FONT = '"Fraunces", Georgia, "Times New Roman", serif';
const BODY_FONT =
  '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

const palette = {
  mode: "light",
  primary: {
    main: BRAND_BLUE,
    light: "#5C6FFF",
    dark: "#0A21C7",
    contrastText: "#FFFFFF",
  },
  secondary: {
    main: "#1A2138",
    contrastText: "#FFFFFF",
  },
  background: {
    // A soft periwinkle tint rather than neutral grey — echoes the light
    // tinted section backgrounds BMG360 alternates against white, without
    // reusing their exact color value.
    default: "#F4F5FC",
    paper: "#FFFFFF",
  },
  text: {
    primary: "#14161F",
    secondary: "#5B6270",
  },
};

const theme = createTheme({
  palette,
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: BODY_FONT,
    h1: { fontFamily: HEADLINE_FONT, fontWeight: 500, letterSpacing: "-0.01em" },
    h2: { fontFamily: HEADLINE_FONT, fontWeight: 500, letterSpacing: "-0.01em" },
    h3: { fontFamily: HEADLINE_FONT, fontWeight: 500 },
    h4: { fontFamily: HEADLINE_FONT, fontWeight: 500 },
    h5: { fontFamily: HEADLINE_FONT, fontWeight: 500 },
    h6: {
      fontFamily: HEADLINE_FONT,
      fontWeight: 500,
      fontSize: "1.375rem",
      letterSpacing: "-0.005em",
    },
  },
});

theme.components = {
  ...theme.components,
  MuiCssBaseline: {
    styleOverrides: {
      html: { overflowX: "hidden" },
      body: { overflowX: "hidden" },
      "#root": { minHeight: "100vh" },
      // Datagrid columns use table-layout:auto, which stretches every
      // column (including short ones like an icon+label or a right-aligned
      // currency value) to fill leftover row width — that's what reads as
      // a big gap before a right-aligned number. Marking a column's cells
      // with .col-fit shrinks it back to its content's width so only the
      // free-text columns (name, campaign, reasoning) absorb the slack.
      ".col-fit": { width: "1%", whiteSpace: "nowrap" },
      // Campaign/name-style columns are free text sharing the row's
      // leftover width with other flexible columns — a floor keeps them
      // from being squeezed down to single-word wrapping once their
      // neighbors are pinned to .col-fit. (min-width on the field's own
      // sx is a no-op: react-admin fields render as inline <span>s, which
      // CSS never sizes by width/min-width — it has to live on the <td>.)
      ".col-campaign": { minWidth: "180px" },
      ".col-wide": { minWidth: "280px", maxWidth: "420px" },
    },
  },
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: "none",
        fontWeight: 600,
        borderRadius: theme.shape.borderRadius,
        boxShadow: "none",
      },
      contained: {
        boxShadow: "none",
        "&:hover": { boxShadow: "none" },
      },
    },
  },
  MuiIconButton: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        "&:hover": {
          backgroundColor: "rgba(13, 43, 255, 0.08)",
        },
      },
    },
  },
  MuiButtonBase: {
    styleOverrides: {
      root: {
        "&.Mui-focusVisible": {
          outline: `2px solid ${theme.palette.primary.main}`,
          outlineOffset: 2,
        },
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        backgroundImage: "none",
      },
      elevation1: {
        boxShadow: "0 1px 3px rgba(20, 22, 31, 0.08)",
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 14,
        boxShadow: "0 1px 2px rgba(20, 22, 31, 0.06), 0 8px 24px rgba(20, 22, 31, 0.05)",
        overflow: "hidden",
      },
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: theme.spacing(2.5),
        "&:last-child": { paddingBottom: theme.spacing(2.5) },
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: 999,
        fontWeight: 600,
      },
    },
  },
  MuiTableRow: {
    styleOverrides: {
      root: {
        "&:hover": {
          backgroundColor: "rgba(13, 43, 255, 0.035)",
        },
      },
    },
  },
  MuiTableCell: {
    styleOverrides: {
      root: {
        padding: theme.spacing(1.75),
        borderBottomColor: "rgba(20, 22, 31, 0.08)",
        verticalAlign: "middle",
      },
      head: {
        fontWeight: 700,
        fontSize: "0.72rem",
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        color: theme.palette.text.secondary,
        whiteSpace: "nowrap",
      },
    },
  },
  MuiTablePagination: {
    styleOverrides: {
      root: { overflow: "hidden" },
      toolbar: { flexWrap: "wrap", minHeight: 52 },
      displayedRows: { whiteSpace: "nowrap" },
    },
  },
  MuiAccordion: {
    styleOverrides: {
      root: {
        "&:before": { display: "none" },
        overflow: "hidden",
      },
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: { minHeight: 56, gap: 12 },
      content: { margin: "12px 0", overflow: "hidden" },
    },
  },
};

export default theme;

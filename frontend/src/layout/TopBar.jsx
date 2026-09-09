import { AppBar as MuiAppBar, Toolbar, Box, Typography } from "@mui/material";
import { NavLink, Link } from "react-router-dom";
import { LoadingIndicator } from "react-admin";
import HomeIcon from "@mui/icons-material/Home";
import CampaignIcon from "@mui/icons-material/Campaign";
import GavelIcon from "@mui/icons-material/Gavel";
import TimelineIcon from "@mui/icons-material/Timeline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import HubIcon from "@mui/icons-material/Hub";

const HEADLINE_FONT = '"Fraunces", Georgia, "Times New Roman", serif';

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: <HomeIcon fontSize="small" />, end: true },
  { to: "/campaigns", label: "Campaigns", icon: <CampaignIcon fontSize="small" /> },
  { to: "/agent_actions", label: "Agent Actions", icon: <GavelIcon fontSize="small" /> },
  { to: "/tool_calls", label: "Tool Calls", icon: <TimelineIcon fontSize="small" /> },
  { to: "/systems", label: "Systems", icon: <HubIcon fontSize="small" /> },
  { to: "/faq", label: "Guide", icon: <HelpOutlineIcon fontSize="small" /> },
];

// react-router's NavLink always appends a literal "active" class when the
// route matches, even when a plain string className is supplied (not just
// the function form) — see NavLink's own source. That's what "&.active"
// below hooks into, so no isActive plumbing is needed here.
const NavItem = ({ to, label, icon, end }) => (
  <Box
    component={NavLink}
    to={to}
    end={end}
    sx={{
      display: "inline-flex",
      alignItems: "center",
      flexShrink: 0,
      gap: 0.75,
      px: 1.5,
      py: 0.75,
      borderRadius: 2,
      fontSize: 14,
      fontWeight: 600,
      color: "text.secondary",
      textDecoration: "none",
      whiteSpace: "nowrap",
      "&:hover": { color: "text.primary", backgroundColor: "rgba(20, 22, 31, 0.05)" },
      "&.active": {
        color: "primary.main",
        backgroundColor: "rgba(13, 43, 255, 0.08)",
      },
    }}
  >
    {icon}
    {label}
  </Box>
);

// The one spot Agent360's own brand/wordmark appears — deliberately not
// duplicated as a page title elsewhere, since the active nav item already
// says which screen you're on (see App.jsx / this file's history).
const Brand = () => (
  <Box
    component={Link}
    to="/"
    sx={{
      display: "inline-flex",
      alignItems: "center",
      gap: 1,
      textDecoration: "none",
      mr: 3,
      flexShrink: 0,
    }}
  >
    <Box
      sx={{
        width: 28,
        height: 28,
        borderRadius: "8px",
        backgroundColor: "primary.main",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: HEADLINE_FONT,
        fontWeight: 600,
        fontSize: 15,
      }}
    >
      A
    </Box>
    <Typography
      sx={{
        fontFamily: HEADLINE_FONT,
        fontWeight: 600,
        fontSize: "1.15rem",
        letterSpacing: "-0.01em",
        color: "text.primary",
      }}
    >
      Agent360
    </Typography>
  </Box>
);

// Full-width top bar, replacing react-admin's default icon-rail sidebar —
// gives the data tables the full page width instead of losing a fixed
// column to a permanently-open drawer. See layout/AppLayout.jsx.
const TopBar = () => (
  <MuiAppBar
    position="fixed"
    color="inherit"
    elevation={0}
    sx={{
      backgroundColor: "background.paper",
      borderBottom: "1px solid rgba(20, 22, 31, 0.08)",
    }}
  >
    <Toolbar
      variant="dense"
      disableGutters
      sx={{
        px: { xs: 1.5, md: 2 },
        gap: 1,
        overflow: "hidden",
      }}
    >
      <Brand />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          overflowX: "auto",
          minWidth: 0,
          flex: 1,
          scrollbarWidth: "none",
          "&::-webkit-scrollbar": { display: "none" },
        }}
      >
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </Box>
      <Box sx={{ flexShrink: 0, display: "flex", alignItems: "center" }}>
        <LoadingIndicator />
      </Box>
    </Toolbar>
  </MuiAppBar>
);

export default TopBar;

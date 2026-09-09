import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Title } from "react-admin";
import { Box, Card, CardContent, CircularProgress, Typography } from "@mui/material";
import CampaignIcon from "@mui/icons-material/Campaign";
import InsightsIcon from "@mui/icons-material/Insights";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import HubIcon from "@mui/icons-material/Hub";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import PageHeader from "../../components/PageHeader";
import IconTag from "../../components/IconTag";
import { fetchCatalog } from "../../dataProvider";

const ICONS = {
  onesource360: <CampaignIcon fontSize="small" />,
  smartspot360: <InsightsIcon fontSize="small" />,
  captivator360: <AutorenewIcon fontSize="small" />,
  maestro360: <PhoneInTalkIcon fontSize="small" />,
  rankpulse: <TravelExploreIcon fontSize="small" />,
  agent360: <HubIcon fontSize="small" />,
};

const SystemsIndex = () => {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCatalog()
      .then(setCatalog)
      .catch((err) => setError(err.message || "Failed to load catalog"));
  }, []);

  return (
    <Box sx={{ width: "100%", maxWidth: 1200, mx: "auto" }}>
      <Title title="Systems" />
      <PageHeader
        title="Systems"
        subtitle="Each simulated application is its own process. The four Django platforms each have their own Postgres database; RankPulse-sim is in-memory FastAPI. Open a platform to see what it’s for, the live tables the agent reads, every REST endpoint, and the tools that wrap those endpoints."
      />

      {error ? (
        <Typography sx={{ color: "#B42318", fontSize: 14 }}>{error}</Typography>
      ) : !catalog ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, color: "text.secondary" }}>
          <CircularProgress size={18} /> Loading catalog…
        </Box>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" },
            gap: 2,
          }}
        >
          {catalog.platforms.map((platform) => (
            <Card
              key={platform.slug}
              component={RouterLink}
              to={`/systems/${platform.slug}`}
              sx={{ textDecoration: "none", display: "block", height: "100%" }}
            >
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, mb: 1 }}>
                  <IconTag icon={ICONS[platform.slug] || <HubIcon fontSize="small" />} color={platform.color} />
                  <Box sx={{ minWidth: 0 }}>
                    <Typography sx={{ fontWeight: 700, fontSize: 16 }}>{platform.name}</Typography>
                    <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{platform.role}</Typography>
                  </Box>
                </Box>
                <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.55, mb: 1.5 }}>
                  {platform.purpose}
                </Typography>
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                  {platform.database ? `Postgres · ${platform.database}` : "No database"}
                  {` · ${platform.tools?.length || 0} MCP tool${(platform.tools?.length || 0) === 1 ? "" : "s"}`}
                  {platform.slug === "rankpulse" && !platform.registered ? " · not registered yet" : ""}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default SystemsIndex;

import { List, Datagrid, TextField, NumberField, DateField, FunctionField, Show, useRecordContext } from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import TvIcon from "@mui/icons-material/Tv";
import RadioIcon from "@mui/icons-material/Radio";
import InsightsIcon from "@mui/icons-material/Insights";
import IconTag from "../components/IconTag";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";

const MEDIUM_ICON = {
  tv: { icon: <TvIcon fontSize="small" />, color: "#0A21C7" },
  radio: { icon: <RadioIcon fontSize="small" />, color: "#9A6700" },
};

const StationTag = ({ name, medium }) => {
  const meta = MEDIUM_ICON[medium] || MEDIUM_ICON.tv;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10, verticalAlign: "middle" }}>
      <IconTag icon={meta.icon} color={meta.color} />
      {name}
    </span>
  );
};

export const SpotList = () => (
  <>
    <PageHeader
      title="Spots"
      subtitle="Each row is one airing of an ad — a station, time of day, and date. Opened from SmartSpot360."
    />
    <ResourceExplainer
      icon={<InsightsIcon fontSize="small" />}
      color="#9A6700"
      platform="SmartSpot360"
      role="TV & radio media buying"
      summary="Spot CPL is what that single airing cost, divided by the conversions it drove — a finer-grained view than the campaign-level CPL on the Campaigns page."
      terms={[
        { term: "Spot", def: "One paid airing. “WSVN Miami / Daytime on Aug 15 for $210” is a spot." },
        { term: "Station", def: "The TV or radio channel in a market (WSVN Miami, WQBA Miami)." },
        { term: "Daypart", def: "The time-of-day window. Prime costs more than Daytime (1.5× here)." },
        { term: "Spot CPL", def: "What that one airing cost, divided by how many conversions it produced." },
      ]}
    />
    <List title="Spots" sort={{ field: "air_date", order: "DESC" }} actions={false}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <FunctionField
        label="Campaign"
        cellClassName="col-campaign"
        headerClassName="col-campaign"
        render={(record) => record.campaign_name || "—"}
      />
      <FunctionField
        label="Station"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <StationTag name={record.station_name} medium={record.station_medium} />}
      />
      <TextField source="daypart_name" label="Daypart" cellClassName="col-fit" headerClassName="col-fit" />
      <DateField source="air_date" label="Air date" cellClassName="col-fit" headerClassName="col-fit" />
      <NumberField
        source="cost"
        options={{ style: "currency", currency: "USD" }}
        cellClassName="col-fit"
        headerClassName="col-fit"
      />
      <TextField source="creative_label" label="Creative" cellClassName="col-fit" headerClassName="col-fit" />
      <FunctionField
        label="Spot CPL"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => (record.cpl != null ? `$${Number(record.cpl).toFixed(2)}` : "—")}
      />
    </Datagrid>
  </List>
  </>
);

const SpotDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={record.station_name || "Spot"}
        subtitle={`${record.campaign_name || "Unknown campaign"} · ${record.daypart_name || ""} · ${record.air_date || ""}`}
        backTo="/spots"
        backLabel="All spots"
      />
      <Card>
        <CardContent>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: 2,
            }}
          >
            <Box>
              <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "text.secondary" }}>Cost</Typography>
              <Typography sx={{ fontSize: 22, fontWeight: 600, fontFamily: '"Fraunces", Georgia, serif' }}>
                {record.cost != null ? `$${Number(record.cost).toLocaleString()}` : "—"}
              </Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "text.secondary" }}>Spot CPL</Typography>
              <Typography sx={{ fontSize: 22, fontWeight: 600, fontFamily: '"Fraunces", Georgia, serif' }}>
                {record.cpl != null ? `$${Number(record.cpl).toFixed(2)}` : "—"}
              </Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "text.secondary" }}>Calls</Typography>
              <Typography sx={{ fontSize: 22, fontWeight: 600, fontFamily: '"Fraunces", Georgia, serif' }}>{record.calls ?? "—"}</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "text.secondary" }}>Conversions</Typography>
              <Typography sx={{ fontSize: 22, fontWeight: 600, fontFamily: '"Fraunces", Georgia, serif' }}>{record.conversions ?? "—"}</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "text.secondary" }}>Creative</Typography>
              <Typography sx={{ fontSize: 16, fontWeight: 600 }}>{record.creative_label || "—"}</Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export const SpotShow = () => (
  <Show actions={false}>
    <SpotDetail />
  </Show>
);

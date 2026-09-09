import { Admin, Resource, CustomRoutes } from "react-admin";
import { Route } from "react-router-dom";
import CampaignIcon from "@mui/icons-material/Campaign";
import GavelIcon from "@mui/icons-material/Gavel";
import TimelineIcon from "@mui/icons-material/Timeline";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import InsightsIcon from "@mui/icons-material/Insights";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import { dataProvider } from "./dataProvider";
import theme from "./theme";
import AppLayout from "./layout/AppLayout";
import Overview from "./pages/Overview";
import SystemsIndex from "./pages/systems/SystemsIndex";
import SystemPage from "./pages/systems/SystemPage";
import { CampaignList, CampaignShow } from "./resources/campaigns";
import { AgentActionList, AgentActionShow } from "./resources/agentActions";
import { ToolCallList, ToolCallShow } from "./resources/toolCalls";
import { CreativeList, CreativeShow } from "./resources/creatives";
import { SpotList, SpotShow } from "./resources/spots";
import { CallRoutingList, CallRoutingShow } from "./resources/callRouting";
import { FaqPage } from "./pages/Faq";

const App = () => (
  <Admin title="Agent360" dataProvider={dataProvider} theme={theme} layout={AppLayout} dashboard={Overview}>
    <CustomRoutes>
      <Route path="/faq" element={<FaqPage />} />
      <Route path="/systems" element={<SystemsIndex />} />
      <Route path="/systems/:slug" element={<SystemPage />} />
    </CustomRoutes>
    <Resource
      name="campaigns"
      list={CampaignList}
      show={CampaignShow}
      icon={CampaignIcon}
    />
    <Resource
      name="agent_actions"
      options={{ label: "Agent Actions" }}
      list={AgentActionList}
      show={AgentActionShow}
      icon={GavelIcon}
    />
    <Resource
      name="tool_calls"
      options={{ label: "Tool Calls" }}
      list={ToolCallList}
      show={ToolCallShow}
      icon={TimelineIcon}
    />
    <Resource
      name="spots"
      options={{ label: "Spots" }}
      list={SpotList}
      show={SpotShow}
      icon={InsightsIcon}
    />
    <Resource
      name="creatives"
      options={{ label: "Creatives" }}
      list={CreativeList}
      show={CreativeShow}
      icon={AutorenewIcon}
    />
    <Resource
      name="call_routing"
      options={{ label: "Call Routing" }}
      list={CallRoutingList}
      show={CallRoutingShow}
      icon={PhoneInTalkIcon}
    />
  </Admin>
);

export default App;

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.captivator360  # noqa: F401
import tools.maestro360  # noqa: F401
import tools.onesource360  # noqa: F401
import tools.smartspot360  # noqa: F401
from catalog import build_catalog
from registry import all_tools, tool_schema


class TestCatalog:
    def test_four_django_platforms_plus_rankpulse_and_gateway(self):
        catalog = build_catalog()
        slugs = [p["slug"] for p in catalog["platforms"]]
        assert slugs == [
            "onesource360",
            "smartspot360",
            "captivator360",
            "maestro360",
            "rankpulse",
            "agent360",
        ]

    def test_registered_tools_match_registry(self):
        catalog = build_catalog()
        names = {tool["name"] for tool in catalog["tools"]}
        assert names == {spec.name for spec in all_tools()}
        assert "get_organic_performance" not in names

    def test_list_campaigns_maps_to_onesource_get(self):
        schema = next(t for t in build_catalog()["tools"] if t["name"] == "list_campaigns")
        assert schema["service"] == "onesource360"
        assert schema["rest"][0]["method"] == "GET"
        assert schema["rest"][0]["path"] == "/api/campaigns/"
        assert "def list_campaigns" in schema["source"]
        assert "mcp_server/tools/onesource360.py" in schema["source_file"] or schema["source_file"].endswith(
            "tools/onesource360.py"
        )

    def test_declining_creatives_maps_to_captivator(self):
        schema = next(t for t in build_catalog()["tools"] if t["name"] == "get_declining_creatives")
        assert schema["service"] == "captivator360"
        assert schema["rest"][0]["path"] == "/api/creatives/declining/"
        assert "get_fatigued_creatives" not in {t["name"] for t in build_catalog()["tools"]}

    def test_write_tools_mark_execute_calls(self):
        schema = next(t for t in build_catalog()["tools"] if t["name"] == "reallocate_budget")
        whens = {call["when"] for call in schema["rest"]}
        assert "on_execute" in whens
        assert any(call["path"].endswith("/apply/") for call in schema["rest"])

    def test_onesource_page_lists_its_tools(self):
        onesource = next(p for p in build_catalog()["platforms"] if p["slug"] == "onesource360")
        assert set(onesource["tools"]) == {
            "list_campaigns",
            "get_campaign_performance",
            "get_performance_anomalies",
        }
        assert onesource["database"] == "onesource360"
        assert onesource["inspect_path"] == "/api/inspect/"

    def test_rankpulse_is_listed_but_unregistered(self):
        rankpulse = next(p for p in build_catalog()["platforms"] if p["slug"] == "rankpulse")
        assert rankpulse["registered"] is False
        assert rankpulse["tools"] == []

    def test_guardrail_source_is_attached(self):
        guardrail = build_catalog()["guardrail"]
        assert "def compute_score" in guardrail["scoring_source"]
        assert "def route" in guardrail["policy_source"]
        assert guardrail["auto_execute_threshold"] == 30.0

    def test_tool_schema_includes_rest_even_from_registry_helper(self):
        spec = next(s for s in all_tools() if s.name == "get_routing_summary")
        schema = tool_schema(spec)
        assert schema["rest"][0]["path"] == "/api/calls/summary/"
        assert schema["rest"][0]["query_from"]["campaign_id"] == "campaign_id"

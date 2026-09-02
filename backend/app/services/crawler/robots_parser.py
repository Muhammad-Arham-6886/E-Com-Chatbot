import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import httpx

from app.services.crawler.ssrf_guard import SSRFGuard


class RobotsRuleSet:
    def __init__(self):
        self.disallow_rules: List[str] = []
        self.allow_rules: List[str] = []
        self.crawl_delay: Optional[float] = None
        self.sitemaps: List[str] = []

    def is_allowed(self, path: str) -> bool:
        """
        Evaluates whether a relative or absolute path is allowed.
        Standard robots precedence: Most specific rule or Allow overrides Disallow of equal/lesser length.
        """
        if not path:
            path = "/"
        parsed = urlparse(path)
        clean_path = parsed.path or "/"
        if parsed.query:
            clean_path = f"{clean_path}?{parsed.query}"

        # If any allow rule matches and is longer or equal to matching disallow rules, allow
        matching_allow = [
            rule for rule in self.allow_rules if clean_path.startswith(rule)
        ]
        matching_disallow = [
            rule for rule in self.disallow_rules if clean_path.startswith(rule)
        ]

        if not matching_disallow:
            return True

        if not matching_allow:
            return False

        max_allow_len = max(len(r) for r in matching_allow)
        max_disallow_len = max(len(r) for r in matching_disallow)

        return max_allow_len >= max_disallow_len


class RobotsParser:
    @staticmethod
    def parse_robots_text(content: str, user_agent: str = "*", base_url: str = "") -> RobotsRuleSet:
        rule_set = RobotsRuleSet()
        lines = content.splitlines()

        current_agents = []
        in_target_agent_section = False
        target_agent_lower = user_agent.lower()

        for line in lines:
            # Strip comments and extra whitespace
            line = line.split("#")[0].strip()
            if not line:
                continue

            if ":" not in line:
                continue

            field, _, val = line.partition(":")
            field = field.strip().lower()
            val = val.strip()

            if field == "user-agent":
                agent_name = val.lower()
                current_agents = [agent_name]
                if agent_name in (target_agent_lower, "*"):
                    in_target_agent_section = True
                else:
                    in_target_agent_section = False

            elif field == "disallow" and in_target_agent_section:
                if val:  # non-empty disallow path
                    rule_set.disallow_rules.append(val)

            elif field == "allow" and in_target_agent_section:
                if val:
                    rule_set.allow_rules.append(val)

            elif field == "crawl-delay" and in_target_agent_section:
                try:
                    rule_set.crawl_delay = float(val)
                except ValueError:
                    pass

            elif field == "sitemap":
                if val:
                    full_sitemap_url = urljoin(base_url, val) if base_url else val
                    if full_sitemap_url not in rule_set.sitemaps:
                        rule_set.sitemaps.append(full_sitemap_url)

        return rule_set

    @classmethod
    async def fetch_and_parse(
        cls,
        base_url: str,
        user_agent: str = "*",
        client: Optional[httpx.AsyncClient] = None,
    ) -> RobotsRuleSet:
        robots_url = urljoin(base_url, "/robots.txt")
        should_close = False
        if client is None:
            client = httpx.AsyncClient(
                timeout=5.0,
                headers={"User-Agent": "AICommerceBot/1.0 (+https://ai-commerce.internal/bot)"},
                follow_redirects=True,
            )
            should_close = True

        try:
            # Perform SSRF check on robots.txt URL
            allow_mock = client is not None and not should_close
            SSRFGuard.validate_url(robots_url, allow_mock_hosts=allow_mock)
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                return cls.parse_robots_text(resp.text, user_agent, base_url)
        except Exception:
            # If robots.txt fails or 404s, default to permissive ruleset
            pass
        finally:
            if should_close:
                await client.aclose()

        return RobotsRuleSet()

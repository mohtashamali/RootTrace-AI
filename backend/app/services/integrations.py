"""Outbound integrations: GitHub (logs and diffs) and Slack (notifications)."""
import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)
API = "https://api.github.com"


def fetch_github_context(repo: str, run_id: str, sha: str) -> tuple[str, str]:
    """Returns (failed-job logs, commit diff). Empty strings when GITHUB_TOKEN is not set."""
    token = get_settings().github_token
    if not token:
        return "", ""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    logs, diff = "", ""
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as c:
        try:
            jobs = c.get(f"{API}/repos/{repo}/actions/runs/{run_id}/jobs").json().get("jobs", [])
            for job in [j for j in jobs if j.get("conclusion") == "failure"][:2]:
                r = c.get(f"{API}/repos/{repo}/actions/jobs/{job['id']}/logs")
                if r.status_code == 200:
                    logs += f"### job: {job['name']}\n" + "\n".join(r.text.splitlines()[-250:]) + "\n"
        except (httpx.HTTPError, ValueError):
            log.warning("could not fetch GitHub job logs for %s run %s", repo, run_id)
        try:
            r = c.get(f"{API}/repos/{repo}/commits/{sha}", headers={"Accept": "application/vnd.github.v3.diff"})
            if r.status_code == 200:
                diff = r.text
        except httpx.HTTPError:
            log.warning("could not fetch GitHub diff for %s@%s", repo, sha)
    return logs[-16000:], diff[:12000]


def post_slack(text: str) -> bool:
    url = get_settings().slack_webhook_url
    if not url:
        return False
    try:
        httpx.post(url, json={"text": text}, timeout=10).raise_for_status()
        return True
    except httpx.HTTPError:
        log.warning("slack notification failed")
        return False

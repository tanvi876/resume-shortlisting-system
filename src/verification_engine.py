"""
Claim Verification Engine
==========================
Verifies candidate-provided GitHub URLs by querying the GitHub REST API.
No auth required for public repos (60 req/hr limit); add GITHUB_TOKEN
for 5000 req/hr.

What we check:
  - Account existence and basic activity (created_at, public repos count)
  - Recent commit frequency (are they actually active?)
  - Language distribution (does it match claimed skills?)
  - Repo quality signals (stars received, repo descriptions, READMEs)
  - Red flags: brand-new accounts, no original repos, all forks
"""

from __future__ import annotations
import re
import time
import requests

from .config import GITHUB_TOKEN, GITHUB_API_BASE
from .models import ParsedResume, VerificationResult

_HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    _HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def _get(endpoint: str) -> dict | list | None:
    """Make a GitHub API GET request. Returns None on error."""
    try:
        resp = requests.get(
            f"{GITHUB_API_BASE}{endpoint}",
            headers=_HEADERS,
            timeout=8,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


def _extract_github_username(url: str) -> str | None:
    """Extract username from github.com/username or github.com/username/repo."""
    match = re.search(r"github\.com/([^/\s?#]+)", url or "")
    return match.group(1) if match else None


def verify_github(url: str) -> VerificationResult:
    """
    Verify a GitHub profile URL and return a VerificationResult with
    activity signals and any red flags.
    """
    username = _extract_github_username(url)

    if not username:
        return VerificationResult(
            platform="GitHub",
            url=url,
            verified=False,
            red_flags=["Could not parse a valid GitHub username from the URL"],
        )

    user_data = _get(f"/users/{username}")
    if not user_data:
        return VerificationResult(
            platform="GitHub",
            url=url,
            verified=False,
            red_flags=[f"GitHub user '{username}' not found or API unavailable"],
        )

    result = VerificationResult(platform="GitHub", url=url, verified=True)
    details: dict = {}
    red_flags: list[str] = []
    positive_signals: list[str] = []

    # ── Basic account signals ──────────────────────────────────────────────
    public_repos: int = user_data.get("public_repos", 0)
    followers: int = user_data.get("followers", 0)
    created_at: str = user_data.get("created_at", "")

    details["username"] = username
    details["public_repos"] = public_repos
    details["followers"] = followers
    details["account_created"] = created_at[:10] if created_at else "unknown"
    details["profile_url"] = f"https://github.com/{username}"

    if public_repos == 0:
        red_flags.append("Account has zero public repositories")
    elif public_repos >= 10:
        positive_signals.append(f"Active account with {public_repos} public repositories")

    # Account age check (less than 3 months old is suspicious for senior devs)
    if created_at:
        from datetime import datetime, timezone
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days
        details["account_age_days"] = age_days
        if age_days < 90:
            red_flags.append(f"Account is only {age_days} days old — may be newly created")
        elif age_days > 365 * 2:
            positive_signals.append(f"Established account ({age_days // 365} years old)")

    # ── Repo quality analysis ──────────────────────────────────────────────
    repos_data = _get(f"/users/{username}/repos?per_page=30&sort=updated")
    if repos_data and isinstance(repos_data, list):
        total_stars = sum(r.get("stargazers_count", 0) for r in repos_data)
        forked_count = sum(1 for r in repos_data if r.get("fork", False))
        original_count = len(repos_data) - forked_count

        languages = {}
        for repo in repos_data:
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        details["total_stars_received"] = total_stars
        details["original_repos"] = original_count
        details["forked_repos"] = forked_count
        details["top_languages"] = sorted(languages, key=lambda l: -languages[l])[:5]

        if forked_count > 0 and original_count == 0:
            red_flags.append("All public repos are forks — no original work visible")
        elif original_count >= 3:
            positive_signals.append(f"{original_count} original (non-fork) repositories found")

        if total_stars > 50:
            positive_signals.append(f"Repos have received {total_stars} total stars from the community")

        if languages:
            positive_signals.append(f"Primary languages: {', '.join(details['top_languages'][:3])}")

    # ── Recent activity: events ────────────────────────────────────────────
    events = _get(f"/users/{username}/events/public?per_page=30")
    if events and isinstance(events, list):
        push_events = [e for e in events if e.get("type") == "PushEvent"]
        details["recent_push_events"] = len(push_events)

        if push_events:
            latest = push_events[0].get("created_at", "")
            details["last_push"] = latest[:10] if latest else "unknown"
            positive_signals.append(f"Recent commit activity detected (last push: {details['last_push']})")
        else:
            red_flags.append("No recent push events found — account may be inactive")

    result.details = details
    result.red_flags = red_flags
    result.positive_signals = positive_signals
    return result


def verify_all(resume: ParsedResume) -> list[VerificationResult]:
    """Run all available verification checks for a candidate."""
    results: list[VerificationResult] = []

    if resume.github_url:
        results.append(verify_github(resume.github_url))
        time.sleep(0.5)  # gentle rate limiting

    # LinkedIn: we can't scrape it, but we validate the URL format
    if resume.linkedin_url:
        is_valid_linkedin = bool(
            re.match(r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?$", resume.linkedin_url)
        )
        results.append(VerificationResult(
            platform="LinkedIn",
            url=resume.linkedin_url,
            verified=is_valid_linkedin,
            details={"note": "LinkedIn blocks automated scraping; URL format validated only"},
            positive_signals=["Valid LinkedIn profile URL format"] if is_valid_linkedin else [],
            red_flags=["LinkedIn URL format appears invalid"] if not is_valid_linkedin else [],
        ))

    return results
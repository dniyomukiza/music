"""
Optional dev endpoint: X API v2 Recent Search + OpenAI for radio prep briefs / on-air scripts.

- Posts: GET https://api.x.com/2/tweets/search/recent (Bearer), then if the time window
  matches full-archive fallback rules and there are no hits, GET …/2/tweets/search/all
  (full archive; requires product access). See:
  https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent
  https://docs.x.com/x-api/posts/search-all-posts
- Optional thread replies: query conversation_id:<root> is:reply when reply_thread_root_id is set.
- Copy: OpenAI Chat Completions (OPENAI_AI_KEY), not xAI.

Removal: delete this file and remove the register_xai_radio_research(app) block in __init__.py
(inside create_app's app_context). No other modules import this package.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from flask import Blueprint, jsonify, render_template_string, request

xai_radio_research_bp = Blueprint(
    "xai_radio_research",
    __name__,
    url_prefix="/api/dev/xai-radio-research",
)

X_RECENT_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
X_ALL_SEARCH_URL = "https://api.x.com/2/tweets/search/all"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
MAX_QUERY_CHARS = 512
MAX_SEARCH_PAGES = int(os.getenv("X_RADIO_SEARCH_MAX_PAGES", "5"))
MAX_TWEETS_IN_PROMPT = int(os.getenv("X_RADIO_MAX_TWEETS_IN_PROMPT", "80"))

_TOPIC_MIN_CHARS = 3
_TOPIC_MAX_CHARS = 280
_TOPIC_MAX_WORDS = 32

_SCOPE_BRIEF = """**Scope lock:** Stay strictly within the topic(s) listed above. Summarize only discussion that clearly ties to those themes using the CONTEXT posts; skip unrelated pile-ons."""

_THIN_RESULTS_BRIEF = """**If CONTEXT is thin:** Do not write "no tweets" or meta about APIs. Give a tight brief on why the themes still matter and what to listen for—hedged, without inventing posts not in CONTEXT."""

_SCOPE_SCRIPT = """**Scope lock (critical):** **Topic 1** and **Topic 2** are the **only** subjects. Use **only** CONTEXT below for concrete quotes and attributions; never invent tweet text."""

_THIN_RESULTS_SCRIPT = """**If CONTEXT is thin (automation-safe):**
- **Never** say "no tweets found", "search empty", "API", etc.
- **Do** a smooth segment on why **Topic 1** and **Topic 2** still matter—hedged general language—without fake quotes. No verbatim lines unless they appear in CONTEXT."""


def register_xai_radio_research(app):
    app.register_blueprint(xai_radio_research_bp)


def _x_bearer() -> str | None:
    return (os.getenv("X_BEARER_TOKEN") or os.getenv("BEARER_TOKEN") or "").strip() or None


def _openai_key() -> str | None:
    return (os.getenv("OPENAI_AI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip() or None


def _health_payload() -> dict:
    return {
        "feature_enabled": os.getenv("ENABLE_XAI_RADIO_RESEARCH") == "1",
        "x_bearer_configured": bool(_x_bearer()),
        "openai_configured": bool(_openai_key()),
        "secret_required": bool(os.getenv("XAI_RADIO_RESEARCH_SECRET")),
        "brief_post_url": "/api/dev/xai-radio-research/brief",
        "script_post_url": "/api/dev/xai-radio-research/script",
        "post_url": "/api/dev/xai-radio-research/brief",
        "docs_x_search_posts": "https://docs.x.com/x-api/posts/search/introduction",
        "docs_recent": "https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent",
        "docs_search_all": "https://docs.x.com/x-api/posts/search-all-posts",
        "topic_rules": "Per topic: 3–280 chars, ≤32 words, not URL-only. loose_topic_validation:true relaxes. Optional: x_query (full query, ≤512 chars), reply_thread_root_id, allowed_x_handles. "
        "If Recent Search returns no posts in the recency window and recency_hours ≥ X_RADIO_ARCHIVE_FALLBACK_MIN_HOURS (default 48), tries full-archive GET /2/tweets/search/all over X_RADIO_ARCHIVE_FALLBACK_DAYS (default 30). Disable with X_RADIO_ARCHIVE_FALLBACK=0.",
    }


def _wants_json() -> bool:
    fmt = (request.args.get("format") or "").lower()
    if fmt == "json":
        return True
    if fmt == "html":
        return False
    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return True
    return False


def _auth_error() -> tuple | None:
    if os.getenv("ENABLE_XAI_RADIO_RESEARCH") != "1":
        return (
            jsonify(
                error="feature_disabled",
                hint="Set ENABLE_XAI_RADIO_RESEARCH=1 in the environment.",
            ),
            403,
        )
    if not _x_bearer():
        return (
            jsonify(
                error="missing_x_bearer",
                hint="Set X_BEARER_TOKEN or BEARER_TOKEN (X app-only Bearer).",
            ),
            503,
        )
    if not _openai_key():
        return (
            jsonify(
                error="missing_openai_key",
                hint="Set OPENAI_AI_KEY or OPENAI_API_KEY for brief/script generation.",
            ),
            503,
        )
    secret = os.getenv("XAI_RADIO_RESEARCH_SECRET")
    if secret and request.headers.get("X-XAI-Radio-Research") != secret:
        return (
            jsonify(
                error="unauthorized",
                hint="Send header X-XAI-Radio-Research matching XAI_RADIO_RESEARCH_SECRET.",
            ),
            401,
        )
    return None


def _sanitize_topic(raw: str) -> tuple[str | None, str | None]:
    s = raw.strip()
    s = re.sub(r"[\u200b-\u200f\uFEFF]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < _TOPIC_MIN_CHARS:
        return None, "too_short"
    if len(s) > _TOPIC_MAX_CHARS:
        return None, "too_long"
    words = s.split()
    if len(words) > _TOPIC_MAX_WORDS:
        return None, "too_many_words"
    if re.fullmatch(r"https?://\S+", s, re.I):
        return None, "url_only"
    letters = sum(1 for c in s if c.isalpha())
    digits = sum(1 for c in s if c.isdigit())
    if len(s) > 12 and letters + digits < len(s) * 0.25:
        return None, "low_signal"
    return s, None


def _topic_validation_hint(code: str) -> str:
    return {
        "too_short": f"Each topic must be at least {_TOPIC_MIN_CHARS} characters.",
        "too_long": f"Keep each topic under {_TOPIC_MAX_CHARS} characters.",
        "too_many_words": f"Use at most {_TOPIC_MAX_WORDS} words per topic.",
        "url_only": "Don't send only a URL; describe the angle in plain language.",
        "low_signal": "Topic looks like gibberish; use plain-language keywords.",
    }.get(code, "Fix this topic string and retry.")


def _topics_from_json(data: dict, *, max_topics: int, exact: int | None = None) -> tuple[list[str] | None, tuple | None]:
    topics = data.get("topics")
    if topics is None and data.get("topic_1") is not None:
        topics = [data.get("topic_1"), data.get("topic_2")]
    if isinstance(topics, str):
        topics = [topics]
    if not topics or not isinstance(topics, list):
        return None, (
            jsonify(error="invalid_body", hint='Include "topics": ["…", "…"] or topic_1 and topic_2.'),
            400,
        )

    loose = data.get("loose_topic_validation") is True
    sanitized: list[str] = []
    for t in topics:
        if len(sanitized) >= max_topics:
            break
        if t is None or not str(t).strip():
            continue
        if loose:
            s = re.sub(r"\s+", " ", str(t).strip())
            if len(s) > 2000:
                return None, (
                    jsonify(error="invalid_topic", code="too_long", hint="Topic exceeds 2000 characters."),
                    400,
                )
            sanitized.append(s)
            continue
        s, code = _sanitize_topic(str(t))
        if code:
            return None, (
                jsonify(
                    error="invalid_topic",
                    code=code,
                    topic_number=len(sanitized) + 1,
                    hint=_topic_validation_hint(code),
                ),
                400,
            )
        sanitized.append(s)

    if exact is not None and len(sanitized) != exact:
        return None, (
            jsonify(
                error="invalid_topics",
                hint=f"Provide exactly {exact} valid topics (got {len(sanitized)}).",
            ),
            400,
        )
    if not sanitized:
        return None, (jsonify(error="invalid_topics", hint="Provide at least one non-empty topic string."), 400)

    if (
        exact == 2
        and len(sanitized) >= 2
        and sanitized[0].casefold() == sanitized[1].casefold()
    ):
        return None, (
            jsonify(error="duplicate_topics", hint="Use two different topics for /script."),
            400,
        )

    return sanitized, None


def _quote_topic_for_query(t: str) -> str:
    t = t.strip().replace('"', "")
    if re.search(r"[\s:()]", t):
        return f'"{t}"'
    return t


def _build_main_query(topics: list[str], data: dict) -> str:
    custom = data.get("x_query")
    if custom is not None and str(custom).strip():
        return str(custom).strip()[:MAX_QUERY_CHARS]

    parts = [_quote_topic_for_query(t) for t in topics]
    inner = " OR ".join(parts)
    q = f"({inner}) lang:en -is:retweet"

    handles = data.get("allowed_x_handles")
    if isinstance(handles, list) and handles:
        from_clause = " OR ".join(f"from:{str(h).lstrip('@')}" for h in handles[:10])
        q = f"({from_clause}) ({inner}) lang:en -is:retweet"

    if len(q) > MAX_QUERY_CHARS:
        q = q[:MAX_QUERY_CHARS]
    return q


def _recency_time_bounds(data: dict) -> tuple[str | None, str | None, dict]:
    """UTC RFC3339 for X start_time/end_time, or (None,None) for full recent window."""
    meta: dict = {"applied": False}
    if data.get("skip_time_window") is True:
        meta["reason"] = "skip_time_window"
        return None, None, meta

    raw = data.get("recency_hours")
    if raw is None:
        raw = os.getenv("X_RADIO_SEARCH_RECENCY_HOURS", "24")
    try:
        hours = int(str(raw).strip())
    except ValueError:
        hours = 24
    hours = 24 if hours <= 24 else 48

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    start_s = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_s = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    meta.update(
        {
            "applied": True,
            "recency_hours": hours,
            "start_time": start_s,
            "end_time": end_s,
        }
    )
    return start_s, end_s, meta


def _archive_fallback_time_bounds(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=max(1, min(365, days)))
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def _x_search_pages(
    bearer: str,
    query: str,
    *,
    search_url: str,
    max_results_cap: int,
    start_time: str | None,
    end_time: str | None,
    max_pages: int = MAX_SEARCH_PAGES,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any] | None, int | None]:
    headers = {"Authorization": f"Bearer {bearer}"}
    try:
        want = int(os.getenv("X_RADIO_MAX_RESULTS", "100"))
    except ValueError:
        want = 100
    max_results = max(10, min(max_results_cap, want))
    base_params: dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,conversation_id,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name,verified",
    }
    if start_time:
        base_params["start_time"] = start_time
    if end_time:
        base_params["end_time"] = end_time

    all_tweets: list[dict[str, Any]] = []
    users_by_id: dict[str, Any] = {}
    next_token: str | None = None
    last_meta: dict[str, Any] = {}

    for page in range(max_pages):
        params = dict(base_params)
        if next_token:
            params["next_token"] = next_token
        try:
            resp = requests.get(
                search_url,
                headers=headers,
                params=params,
                timeout=60,
            )
        except requests.RequestException as exc:
            return [], users_by_id, jsonify(error="x_api_unreachable", detail=str(exc)), 502

        try:
            body = resp.json()
        except ValueError:
            return [], users_by_id, jsonify(error="x_api_bad_json", raw=resp.text[:500]), 502

        if resp.status_code >= 400:
            return [], users_by_id, jsonify(error="x_api_error", status=resp.status_code, body=body), 502

        for tw in body.get("data") or []:
            if isinstance(tw, dict):
                all_tweets.append(tw)
        for u in (body.get("includes") or {}).get("users") or []:
            if isinstance(u, dict) and u.get("id"):
                users_by_id[str(u["id"])] = u

        last_meta = body.get("meta") or {}
        next_token = last_meta.get("next_token")
        if not next_token:
            break

    return all_tweets, users_by_id, None, None


def _x_recent_search_pages(
    bearer: str,
    query: str,
    *,
    start_time: str | None,
    end_time: str | None,
    max_pages: int = MAX_SEARCH_PAGES,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any] | None, int | None]:
    return _x_search_pages(
        bearer,
        query,
        search_url=X_RECENT_SEARCH_URL,
        max_results_cap=100,
        start_time=start_time,
        end_time=end_time,
        max_pages=max_pages,
    )


def _format_context_block(tweets: list[dict[str, Any]], users_by_id: dict[str, Any], *, label: str) -> str:
    lines = [f"### {label}"]
    for tw in tweets[:MAX_TWEETS_IN_PROMPT]:
        uid = str(tw.get("author_id") or "")
        u = users_by_id.get(uid) or {}
        un = u.get("username") or "unknown"
        nm = u.get("name") or ""
        cid = tw.get("conversation_id") or ""
        txt = (tw.get("text") or "").replace("\n", " ")
        lines.append(
            f"- id={tw.get('id')} convo={cid} @{un} ({nm}) at {tw.get('created_at')}: {txt}"
        )
    if len(lines) == 1:
        lines.append("(no posts in this batch)")
    return "\n".join(lines)


def _openai_chat_completion(*, system: str, user: str, model: str) -> tuple[str | None, object | None, int | None]:
    key = _openai_key()
    assert key
    try:
        resp = requests.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.65,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        return None, jsonify(error="openai_unreachable", detail=str(exc)), 502

    try:
        body = resp.json()
    except ValueError:
        return None, jsonify(error="openai_bad_json", raw=resp.text[:500]), 502

    if resp.status_code >= 400:
        return None, jsonify(error="openai_error", status=resp.status_code, body=body), 502

    choices = body.get("choices") or []
    if not choices:
        return None, jsonify(error="openai_no_choices", body=body), 502
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip(), None, None
    return None, jsonify(error="openai_empty_content", body=body), 502


def _strip_broadcast_citations(text: str | None) -> str | None:
    if not text or not isinstance(text, str):
        return text
    s = text
    s = re.sub(r"\[\[\d+\]\]\([^)]*\)", "", s)
    s = re.sub(r"\[\d+\]\([^)]*\)", "", s)
    s = re.sub(r"\[\^\d+\]", "", s)
    s = re.sub(r"https?://(?:www\.)?(?:x\.com|twitter\.com)[^\s)\]]+", "", s)
    s = re.sub(r" +", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


_HEALTH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>X API radio research (dev)</title>
  <style>
    :root { --bg:#0f1412; --card:#151c19; --text:#e8eee9; --muted:#8a9a90; --ok:#34d399; --warn:#fbbf24; --bad:#f87171; --accent:#60a5fa; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 1.5rem; line-height: 1.5; max-width: 46rem; }
    h1 { font-size: 1.15rem; font-weight: 600; margin: 0 0 0.25rem; }
    p.sub { color: var(--muted); font-size: 0.9rem; margin: 0 0 1.25rem; }
    .card { background: var(--card); border: 1px solid rgba(255,255,255,.08); border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 1rem; }
    dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.35rem 1rem; font-size: 0.9rem; }
    dt { color: var(--muted); }
    dd { margin: 0; }
    .pill { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
    .on { background: rgba(52,211,153,.2); color: var(--ok); }
    .off { background: rgba(248,113,113,.2); color: var(--bad); }
    code { font-size: 0.8rem; background: rgba(0,0,0,.35); padding: 0.12rem 0.35rem; border-radius: 4px; }
    a { color: var(--accent); }
    pre { font-size: 0.8rem; background: rgba(0,0,0,.35); padding: 0.75rem; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
    label { display: block; font-size: 0.85rem; color: var(--muted); margin: 0.5rem 0 0.25rem; }
    input[type=text], textarea { width: 100%; padding: 0.5rem 0.6rem; border-radius: 6px; border: 1px solid rgba(255,255,255,.12); background: rgba(0,0,0,.25); color: var(--text); font-size: 0.95rem; }
    textarea { min-height: 140px; font-family: inherit; }
    button { margin-top: 0.75rem; padding: 0.5rem 1rem; border-radius: 6px; border: none; background: var(--accent); color: #0f1412; font-weight: 600; cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .err { color: var(--bad); font-size: 0.9rem; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>X API + OpenAI (radio dev)</h1>
  <p class="sub">POST uses <code>X Recent Search</code> (with optional <a href="https://docs.x.com/x-api/posts/search-all-posts" rel="noopener">full-archive</a> fallback when 48h has no hits) + <code>OpenAI</code> chat — not xAI. Env: <code>X_BEARER_TOKEN</code>, <code>OPENAI_AI_KEY</code>, <code>ENABLE_XAI_RADIO_RESEARCH=1</code>.</p>
  <div class="card">
    <dl>
      <dt>Feature</dt>
      <dd>{% if feature_enabled %}<span class="pill on">ENABLED</span>{% else %}<span class="pill off">DISABLED</span>{% endif %}</dd>
      <dt>X Bearer</dt>
      <dd>{% if x_bearer_configured %}<span class="pill on">set</span>{% else %}<span class="pill off">missing</span>{% endif %}</dd>
      <dt>OpenAI</dt>
      <dd>{% if openai_configured %}<span class="pill on">set</span>{% else %}<span class="pill off">missing</span>{% endif %}</dd>
      <dt>Secret header</dt>
      <dd>{% if secret_required %}<span class="pill on">required</span>{% else %}<span class="pill off">optional</span>{% endif %}</dd>
    </dl>
  </div>
  <div class="card">
    <p style="margin:0 0 0.75rem;"><strong>Live script</strong> (2 topics → X search → OpenAI script)</p>
    <label>Topic 1</label>
    <input type="text" id="topic1" placeholder="Short phrase" autocomplete="off" maxlength="300">
    <label>Topic 2</label>
    <input type="text" id="topic2" placeholder="Second angle" autocomplete="off" maxlength="300">
    <label>Approx. on-air length (seconds)</label>
    <input type="text" id="duration" value="120" inputmode="numeric" style="max-width:8rem">
    <label>Time window</label>
    <select id="recencyHours" style="max-width:100%;padding:0.45rem;border-radius:6px;background:rgba(0,0,0,.25);color:inherit;">
      <option value="24" selected>Last ~24h (UTC)</option>
      <option value="48">Last ~48h (UTC)</option>
    </select>
    <label style="display:flex;align-items:center;gap:0.5rem;margin-top:0.65rem;cursor:pointer;">
      <input type="checkbox" id="includeQuotes" checked style="width:auto;"> Verbatim quotes from CONTEXT only
    </label>
    <button type="button" id="btnScript" {% if not feature_enabled %}disabled{% endif %}>Generate script</button>
    <div class="err" id="scriptErr" hidden></div>
    <label style="margin-top:1rem;">Script</label>
    <textarea id="scriptOut" readonly placeholder="…"></textarea>
  </div>
  <div class="card">
    <p style="margin:0 0 0.5rem; font-size:0.9rem;"><strong>JSON:</strong> <pre>{{ health_json_url }}</pre></p>
    <p style="margin:0;"><a href="{{ docs_recent }}" rel="noopener">X Recent Search</a> · <a href="https://docs.x.com/x-api/posts/search-all-posts" rel="noopener">Search all posts</a></p>
  </div>
  <div class="card">
    <pre>curl -sS -X POST "{{ curl_base }}{{ script_post_url }}" -H "Content-Type: application/json" \
 -d '{"topics":["A","B"],"recency_hours":48}'</pre>
  </div>
<script>
(function () {
  var secret = {{ xai_research_secret | tojson }};
  var btn = document.getElementById('btnScript');
  var t1 = document.getElementById('topic1');
  var t2 = document.getElementById('topic2');
  var dur = document.getElementById('duration');
  var rec = document.getElementById('recencyHours');
  var qChk = document.getElementById('includeQuotes');
  var out = document.getElementById('scriptOut');
  var err = document.getElementById('scriptErr');
  if (!btn) return;
  btn.addEventListener('click', function () {
    err.hidden = true;
    out.value = '';
    var a = (t1 && t1.value || '').trim();
    var b = (t2 && t2.value || '').trim();
    if (!a || !b) { err.textContent = 'Enter two topics.'; err.hidden = false; return; }
    var secs = parseInt((dur && dur.value) || '120', 10);
    if (!secs || secs < 30) secs = 120;
    var rh = rec ? parseInt(rec.value, 10) : 24;
    if (rh !== 48) rh = 24;
    btn.disabled = true;
    var headers = { 'Content-Type': 'application/json' };
    if (secret) headers['X-XAI-Radio-Research'] = secret;
    fetch('{{ curl_base }}{{ script_post_url }}', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        topics: [a, b],
        approximate_duration_seconds: secs,
        recency_hours: rh,
        include_public_figure_quotes: qChk ? qChk.checked : true
      })
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) {
        btn.disabled = false;
        if (!x.ok) {
          err.textContent = (x.j && (x.j.error + (x.j.hint ? ': ' + x.j.hint : ''))) || 'Request failed';
          err.hidden = false;
          return;
        }
        out.removeAttribute('readonly');
        out.value = (x.j && x.j.script) || '';
      }).catch(function (e) {
        btn.disabled = false;
        err.textContent = String(e);
        err.hidden = false;
      });
  });
})();
</script>
</body>
</html>
"""


@xai_radio_research_bp.route("/", methods=["GET"])
def index():
    payload = _health_payload()
    if _wants_json():
        return jsonify(payload)
    base = request.url_root.rstrip("/")
    health_json_url = f"{base}/api/dev/xai-radio-research/health?format=json"
    return render_template_string(
        _HEALTH_HTML,
        **payload,
        health_json_url=health_json_url,
        curl_base=base,
        docs_recent="https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent",
        xai_research_secret=os.getenv("XAI_RADIO_RESEARCH_SECRET") or "",
    )


@xai_radio_research_bp.route("/health", methods=["GET"])
def health():
    payload = _health_payload()
    if _wants_json():
        return jsonify(payload)
    base = request.url_root.rstrip("/")
    health_json_url = f"{base}/api/dev/xai-radio-research/health?format=json"
    return render_template_string(
        _HEALTH_HTML,
        **payload,
        health_json_url=health_json_url,
        curl_base=base,
        docs_recent="https://developer.x.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent",
        xai_research_secret=os.getenv("XAI_RADIO_RESEARCH_SECRET") or "",
    )


def _gather_x_context(
    bearer: str,
    topics: list[str],
    data: dict,
) -> tuple[str, dict[str, Any], object | None, int | None]:
    """Returns (context_block, meta, err_response, status)."""
    start_t, end_t, time_meta = _recency_time_bounds(data)
    main_query = _build_main_query(topics, data)

    tweets, users, err, st = _x_recent_search_pages(
        bearer, main_query, start_time=start_t, end_time=end_t
    )
    if err is not None:
        return "", {}, err, st

    archive_fetch: dict[str, Any] = {"attempted": False}
    if os.getenv("X_RADIO_ARCHIVE_FALLBACK", "1").strip() == "1":
        try:
            min_hours = int(os.getenv("X_RADIO_ARCHIVE_FALLBACK_MIN_HOURS", "48"))
        except ValueError:
            min_hours = 48
        try:
            fb_days = int(os.getenv("X_RADIO_ARCHIVE_FALLBACK_DAYS", "30"))
        except ValueError:
            fb_days = 30
        if (
            len(tweets) == 0
            and time_meta.get("applied")
            and time_meta.get("recency_hours", 0) >= min_hours
        ):
            archive_fetch["attempted"] = True
            archive_fetch["min_recency_hours"] = min_hours
            archive_fetch["lookback_days"] = fb_days
            arch_s, arch_e = _archive_fallback_time_bounds(fb_days)
            atweets, ausers, aerr, _ast = _x_search_pages(
                bearer,
                main_query,
                search_url=X_ALL_SEARCH_URL,
                max_results_cap=500,
                start_time=arch_s,
                end_time=arch_e,
            )
            if aerr is None and atweets:
                tweets, users = atweets, ausers
                start_t, end_t = arch_s, arch_e
                archive_fetch["used"] = True
                archive_fetch["endpoint"] = X_ALL_SEARCH_URL
            elif aerr is not None:
                archive_fetch["used"] = False
                try:
                    ej = aerr.get_json(silent=True) or {}
                    archive_fetch["detail"] = {
                        "error": ej.get("error"),
                        "status": ej.get("status"),
                    }
                except Exception:
                    archive_fetch["detail"] = {"error": "archive_unavailable"}

    blocks = [_format_context_block(tweets, users, label="Posts (main search)")]

    root_raw = data.get("reply_thread_root_id") or data.get("thread_root_id")
    if root_raw is not None and str(root_raw).strip().isdigit():
        rid = str(root_raw).strip()
        reply_q = f"conversation_id:{rid} is:reply lang:en -is:retweet"[:MAX_QUERY_CHARS]
        rp = min(3, MAX_SEARCH_PAGES)
        if archive_fetch.get("used"):
            rtweets, rusers, err2, st2 = _x_search_pages(
                bearer,
                reply_q,
                search_url=X_ALL_SEARCH_URL,
                max_results_cap=500,
                start_time=start_t,
                end_time=end_t,
                max_pages=rp,
            )
        else:
            rtweets, rusers, err2, st2 = _x_recent_search_pages(
                bearer, reply_q, start_time=start_t, end_time=end_t, max_pages=rp
            )
        if err2 is None:
            users.update(rusers)
            blocks.append(_format_context_block(rtweets, users, label=f"Replies in conversation {rid}"))
            meta_reply_count = len(rtweets)
        else:
            meta_reply_count = 0
    else:
        meta_reply_count = 0

    meta: dict[str, Any] = {
        "main_query": main_query,
        "time_window": time_meta,
        "main_tweet_count": len(tweets),
        "reply_tweet_count": meta_reply_count,
        "x_recent_search_url": X_RECENT_SEARCH_URL,
        "x_search_all_url": X_ALL_SEARCH_URL,
        "x_main_endpoint": archive_fetch.get("endpoint") or X_RECENT_SEARCH_URL,
        "archive_fallback": archive_fetch,
    }
    return "\n\n".join(blocks), meta, None, None


@xai_radio_research_bp.route("/brief", methods=["POST"])
def whats_happening_brief():
    err = _auth_error()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    topics, terr = _topics_from_json(data, max_topics=2, exact=None)
    if terr:
        return terr

    bearer = _x_bearer()
    assert bearer

    context, xmeta, xerr, xst = _gather_x_context(bearer, topics, data)
    if xerr is not None:
        return xerr, xst

    model = str(
        data.get("openai_model") or os.getenv("OPENAI_RADIO_MODEL") or DEFAULT_OPENAI_MODEL
    ).strip()

    topics_block = "\n".join(f"- {t}" for t in topics)
    user_prompt = f"""Topics:
{topics_block}

{_SCOPE_BRIEF}
{_THIN_RESULTS_BRIEF}

---
CONTEXT (raw X posts from search — recent or full-archive fallback; use only this for specifics):
{context}
---

Produce a **radio host prep brief** (not on-air script):
- Per topic: current narrative, thread/reply themes if visible in CONTEXT, 3–5 talking points, flag rumors.
- Where CONTEXT shows focal posts vs replies, call that out.
- Reference attribution as @username + paraphrase. No URLs or tweet IDs on air."""

    system = "You are an editorial assistant for music/culture radio. Never invent tweet text missing from CONTEXT."

    text, oerr, ost = _openai_chat_completion(system=system, user=user_prompt, model=model)
    if oerr is not None:
        return oerr, ost

    out: dict[str, Any] = {
        "openai_model": model,
        "topics": topics,
        "x_fetch": xmeta,
        "brief": text,
        "context_char_count": len(context),
    }
    if not os.getenv("XAI_RADIO_RESEARCH_SECRET"):
        out["warning"] = "XAI_RADIO_RESEARCH_SECRET is not set; anyone who can reach this route can spend X/OpenAI quota."
    return jsonify(out), 200


@xai_radio_research_bp.route("/script", methods=["POST"])
def live_radio_script():
    err = _auth_error()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    topics, terr = _topics_from_json(data, max_topics=2, exact=2)
    if terr:
        return terr

    bearer = _x_bearer()
    assert bearer

    context, xmeta, xerr, xst = _gather_x_context(bearer, topics, data)
    if xerr is not None:
        return xerr, xst

    model = str(
        data.get("openai_model") or os.getenv("OPENAI_RADIO_MODEL") or DEFAULT_OPENAI_MODEL
    ).strip()
    raw_dur = data.get("approximate_duration_seconds", 120)
    try:
        duration_s = max(30, min(600, int(raw_dur)))
    except (TypeError, ValueError):
        duration_s = 120
    target_words = max(75, min(800, int(duration_s * 2.5)))

    t1, t2 = topics[0], topics[1]
    inc = data.get("include_public_figure_quotes", True)
    if isinstance(inc, str):
        include_quotes = inc.strip().lower() in ("1", "true", "yes")
    elif isinstance(inc, bool):
        include_quotes = inc
    else:
        include_quotes = True

    handles_hint = ""
    ah = data.get("allowed_x_handles")
    if isinstance(ah, list) and ah:
        handles_hint = "\nPrioritize voices from: " + ", ".join(str(h).lstrip("@") for h in ah[:10]) + " (if they appear in CONTEXT).\n"

    if include_quotes:
        quotes_rules = f"""
**Quotes:** Up to four **short** verbatim lines **only** from CONTEXT tweet text. Attribute with @username or display name from CONTEXT; say "posted on X…". No invented quotes. Do not read raw tweet IDs.{handles_hint}
"""
    else:
        quotes_rules = f"""
**No verbatim quotes.** Paraphrase CONTEXT only; attribute with @username where helpful.{handles_hint}
"""

    user_prompt = f"""**Topic 1:** {t1}
**Topic 2:** {t2}

{_SCOPE_SCRIPT}

Duration target: ~{duration_s} seconds (~{target_words} words).

---
CONTEXT (X search + optional replies block):
{context}
---

{_THIN_RESULTS_SCRIPT}

{quotes_rules}

Rules:
- One continuous **on-air script** for a music/culture "what's happening" segment.
- Natural spoken English; [PAUSE] sparingly.
- **No** footnotes, markdown links, or x.com URLs in output.
- Do not mention APIs, searches failing, or "no tweets".

Output **only** the script (optional one-line title, blank line, then script)."""

    system = "You write broadcast scripts. Use ONLY CONTEXT for factual tweet content."

    script_raw, oerr, ost = _openai_chat_completion(system=system, user=user_prompt, model=model)
    if oerr is not None:
        return oerr, ost

    script_text = _strip_broadcast_citations(script_raw)

    out: dict[str, Any] = {
        "openai_model": model,
        "topics": [t1, t2],
        "approximate_duration_seconds": duration_s,
        "include_public_figure_quotes": include_quotes,
        "x_fetch": xmeta,
        "script": script_text or None,
        "context_char_count": len(context),
    }
    if not os.getenv("XAI_RADIO_RESEARCH_SECRET"):
        out["warning"] = "XAI_RADIO_RESEARCH_SECRET is not set; anyone who can reach this route can spend X/OpenAI quota."
    return jsonify(out), 200

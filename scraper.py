# scraper.py
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Optional
from urllib.parse import urlparse

from requests_html import HTMLSession
from staffspy import LinkedInAccount


def scrape_generic(
    url: str,
    fields: Sequence[Mapping[str, Any]],
    render_js: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Scrape arbitrary content from a page using XPath expressions.

    :param url: The URL to scrape.
    :param fields: A sequence of field definitions, each of which is a mapping
                   with at least:
                     - ``name``: display name / key for the field
                     - ``type``: one of ``\"single\"``, ``\"multiple\"``, ``\"image\"``
                     - ``selector``: XPath string (often copied directly from your browser devtools)
    :param render_js: Whether to render the page with JavaScript (Pyppeteer).

    :return: A dict with the scraped data, e.g.:
             {
               "url": "...",
               "Title": "My page title",
               "Ingredients": ["Item 1", "Item 2"],
               "Hero image": "https://example.com/image.jpg",
             }
    """
    session = HTMLSession()
    data: Dict[str, Any] = {"url": url}
    debug_info: Dict[str, Any] = {}
    # Always initialise so we can safely reference it even if an exception
    # occurs before we start iterating over fields.
    field_debug: Dict[str, Any] = {}

    try:
        response = session.get(url)

        if debug:
            debug_info["status_code"] = getattr(response, "status_code", None)
            debug_info["ok"] = getattr(response, "ok", None)
            debug_info["final_url"] = str(getattr(response, "url", url))

        if render_js:
            # Render JS if needed (this can be slow)
            response.html.render(sleep=1, timeout=20)

        # Use the underlying lxml tree so XPaths copied from browser devtools
        # (including \"Copy full XPath\") work as expected.
        root = getattr(response.html, "lxml", None)
        if root is None:
            # Fallback: let requests-html build the lxml tree.
            root = response.html

        for field in fields:
            # Defensive access – tolerate partial/malformed configs.
            name = str(field.get("name") or "").strip() or "field"
            field_type = str(field.get("type") or "single").lower()
            xpath = str(field.get("selector") or "").strip()

            if not xpath:
                data[name] = None
                continue

            # MULTIPLE: return list of text values.
            if field_type == "multiple":
                elems = root.xpath(xpath)
                items: List[str] = []
                for elem in elems:
                    # Element or raw string (e.g. //img/@src)
                    if hasattr(elem, "text"):
                        text = (getattr(elem, "text", "") or "").strip()
                    else:
                        text = str(elem).strip()
                    if text:
                        items.append(text)
                data[name] = items

                if debug:
                    sample: Optional[str] = None
                    if elems:
                        first = elems[0]
                        if hasattr(first, "text"):
                            sample = (getattr(first, "text", "") or "").strip()
                        else:
                            sample = str(first).strip()
                    field_debug[name] = {
                        "type": field_type,
                        "xpath": xpath,
                        "match_count": len(elems),
                        "sample": sample,
                    }
                continue

            # IMAGE: return a best-guess URL-like attribute if present.
            if field_type == "image":
                nodes = root.xpath(xpath)
                value: Any = None
                if nodes:
                    elem = nodes[0]
                    # If the XPath targets an attribute directly (//img/@src) we
                    # will get back a plain string.
                    if not hasattr(elem, "attrib") and not hasattr(elem, "attrs"):
                        value = str(elem).strip() or None
                    else:
                        # Try lxml-style attributes first, then requests-html attrs.
                        attrs: MutableMapping[str, Any] = {}
                        if hasattr(elem, "attrib"):
                            attrs.update(getattr(elem, "attrib", {}) or {})
                        if hasattr(elem, "attrs"):
                            attrs.update(getattr(elem, "attrs", {}) or {})

                        value = (
                            attrs.get("src")
                            or attrs.get("data-src")
                            or attrs.get("data-image")
                            or attrs.get("href")
                        )
                        # As a fallback, try the element text.
                        if value is None:
                            text = (getattr(elem, "text", "") or "").strip()
                            value = text or None

                data[name] = value

                if debug:
                    field_debug[name] = {
                        "type": field_type,
                        "xpath": xpath,
                        "match_count": len(nodes),
                        "sample": value,
                    }
                continue

            # SINGLE (default): first node's text or string value.
            nodes = root.xpath(xpath)
            if nodes:
                elem = nodes[0]
                if hasattr(elem, "text"):
                    text = (getattr(elem, "text", "") or "").strip()
                else:
                    text = str(elem).strip()
                value = text or None
                data[name] = value
            else:
                value = None

            if debug:
                field_debug[name] = {
                    "type": field_type,
                    "xpath": xpath,
                    "match_count": len(nodes),
                    "sample": value,
                }

    except Exception as e:  # pragma: no cover - defensive logging
        if debug:
            debug_info["error"] = repr(e)
        else:
            print(f"Error scraping {url} - {e}")

    if debug:
        debug_info["fields"] = field_debug
        data["_debug"] = debug_info

    return data


def scrape_recipe(
    url: str,
    selectors: Mapping[str, str],
    render_js: bool = False,
) -> Dict[str, Any]:
    """
    Backwards-compatible helper that uses ``scrape_generic`` under the hood.

    ``selectors`` is expected to be a mapping with keys like
    ``\"title\"``, ``\"ingredients\"``, ``\"instructions\"``.
    """
    fields: List[Dict[str, Any]] = [
        {
            "name": "title",
            "type": "single",
            "selector": selectors.get("title", ""),
        },
        {
            "name": "ingredients",
            "type": "multiple",
            "selector": selectors.get("ingredients", ""),
        },
        {
            "name": "instructions",
            "type": "multiple",
            "selector": selectors.get("instructions", ""),
        },
    ]

    generic_result = scrape_generic(url, fields, render_js=render_js)

    return {
        "url": generic_result.get("url"),
        "title": generic_result.get("title"),
        "ingredients": generic_result.get("ingredients") or [],
        "instructions": generic_result.get("instructions") or [],
    }


def _extract_linkedin_user_id(profile_url: str) -> Optional[str]:
    """
    Extract the LinkedIn user id/slug from a profile URL.

    Example:
      https://www.linkedin.com/in/dougmcmillon -> dougmcmillon
    """
    try:
        parsed = urlparse(profile_url)
        path = (parsed.path or "").strip("/")
        if not path:
            return None
        segments = path.split("/")
        if "in" in segments:
            idx = segments.index("in")
            if idx + 1 < len(segments):
                return segments[idx + 1]
        # Fallback: last segment
        return segments[-1] if segments else None
    except Exception:
        return None


def scrape_linkedin_profiles(
    profile_urls: Sequence[str],
    session_file: str = "linkedin_session.pkl",
    username: Optional[str] = None,
    password: Optional[str] = None,
    log_level: int = 1,
) -> List[Dict[str, Any]]:
    """
    Scrape LinkedIn profiles using the StaffSpy library.

    This expects full LinkedIn profile URLs and converts them into the
    username/slug format StaffSpy's ``scrape_users`` API expects.

    Authentication is handled by StaffSpy:
      - If ``session_file`` exists, it will reuse saved cookies.
      - If ``username`` and ``password`` are provided, it can perform login.

    Returns a list of dicts (one per profile).
    """
    user_ids: List[str] = []
    for url in profile_urls:
        user_id = _extract_linkedin_user_id(url)
        if user_id:
            user_ids.append(user_id)

    if not user_ids:
        return []

    account_kwargs: Dict[str, Any] = {
        "session_file": session_file,
        "log_level": log_level,
    }
    if username and password:
        account_kwargs["username"] = username
        account_kwargs["password"] = password

    account = LinkedInAccount(**account_kwargs)

    # Call StaffSpy one user at a time so that a failure for a single profile
    # (e.g. hidden / not found) doesn't break the entire batch.
    all_rows: List[Dict[str, Any]] = []

    for user_id in user_ids:
        try:
            result = account.scrape_users(user_ids=[user_id])
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            # Log to stdout so it's visible in the container / Streamlit logs,
            # but continue with other users.
            print(f"StaffSpy error for user_id {user_id!r}: {exc!r}")
            continue

        if hasattr(result, "to_dict"):
            # type: ignore[call-arg]
            rows = result.to_dict(orient="records")
        elif isinstance(result, list):
            rows = result  # type: ignore[assignment]
        else:
            rows = [result]  # type: ignore[list-item]

        all_rows.extend(rows)

    return all_rows

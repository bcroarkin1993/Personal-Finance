"""
scripts/theme.py — Shared UI theme for the Personal Finance app.

Import color constants and call page_header() / apply_base_css() from every
page so the visual language stays consistent without repeating CSS or color
hex codes across files.

Color palette
─────────────
  GREEN   = "#2ecc71"   positive values, profit, in-budget, fresh data
  RED     = "#e74c3c"   negative values, loss, over-budget, stale data
  BLUE    = "#3498db"   neutral emphasis (savings rate, area fills, links)
  YELLOW  = "#f39c12"   warnings, moderately stale data

  DARK_BG     = "#0b1621"   metric card background
  CARD_BORDER = "#243447"   metric card border
  BANNER_BG   = "#1e2530"   info / freshness banner background

Chart library conventions
─────────────────────────
  Altair  — time-series line and area charts (trends over time)
  Plotly  — categorical charts: bar, pie, treemap, radar; RdYlGn score maps

  Both libraries appear in the app; the rule above governs which to reach for
  when adding a new chart to any page.
"""

from __future__ import annotations

import streamlit as st

# ── Color palette ─────────────────────────────────────────────────────────────

GREEN  = "#2ecc71"
RED    = "#e74c3c"
BLUE   = "#3498db"
YELLOW = "#f39c12"

DARK_BG     = "#0b1621"
CARD_BORDER = "#243447"
BANNER_BG   = "#1e2530"

_HERO_GRADIENT = "linear-gradient(135deg, #1e3c72 0%, #2a5298 40%, #3b8d99 100%)"

# ── Shared CSS ────────────────────────────────────────────────────────────────

_BASE_CSS = f"""
<style>
/* ── Hero header ── */
.hero-container {{
    padding: 1.5rem 1.75rem;
    border-radius: 18px;
    background: {_HERO_GRADIENT};
    color: white;
    margin-bottom: 0.75rem;
}}
.hero-title {{
    font-size: 2.1rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}}
.hero-subtitle {{
    font-size: 1rem;
    opacity: 0.9;
    margin-top: 0.25rem;
}}
.hero-pill {{
    display: inline-block;
    padding: 0.15rem 0.7rem;
    border-radius: 999px;
    background-color: rgba(255,255,255,0.12);
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
}}

/* ── Metric cards ── */
div[data-testid="metric-container"] {{
    background-color: {DARK_BG};
    padding: 10px 14px;
    border-radius: 14px;
    border: 1px solid {CARD_BORDER};
}}
div[data-testid="metric-container"] > label > div {{
    font-size: 0.75rem;
    font-weight: 500;
}}
div[data-testid="metric-container"] > div {{
    font-size: 0.95rem;
    font-weight: 600;
    overflow-wrap: anywhere;
}}

/* ── Section titles and labels ── */
.section-title {{
    font-size: 1.2rem;
    font-weight: 600;
    margin-top: 0.75rem;
    margin-bottom: 0.25rem;
}}
.muted-label {{
    font-size: 0.8rem;
    opacity: 0.7;
}}
</style>
"""


def apply_base_css() -> None:
    """Inject shared CSS for the hero header, metric cards, section titles, etc.

    Safe to call multiple times per page — Streamlit de-duplicates identical
    markdown injections within a single render.
    """
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


def page_header(
    title: str,
    icon: str = "",
    subtitle: str = "",
    pills: list | None = None,
) -> None:
    """Render the gradient hero header used on every page.

    Automatically injects the shared base CSS so callers don't need a
    separate apply_base_css() call.

    Args:
        title:    Page title text (without icon).
        icon:     Optional emoji prefix shown before the title (e.g. "📈").
        subtitle: Optional second line of smaller descriptive text.
        pills:    Optional list of short strings rendered as pill badges above
                  the title — useful for status labels on the home dashboard.
    """
    apply_base_css()

    title_text = f"{icon}&nbsp;{title}" if icon else title

    pills_html = ""
    if pills:
        pills_html = (
            "<div style='margin-bottom:0.4rem;'>"
            + "".join(f"<span class='hero-pill'>{p}</span>&nbsp;" for p in pills)
            + "</div>"
        )

    subtitle_html = (
        f"<div class='hero-subtitle'>{subtitle}</div>" if subtitle else ""
    )

    st.markdown(
        f"""
        <div class='hero-container'>
            {pills_html}
            <div class='hero-title'>{title_text}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

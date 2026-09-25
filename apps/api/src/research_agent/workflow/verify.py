import re
import unicodedata

from research_agent.schemas.agents import Report

_CITATION_RE = re.compile(r"\[(\d+)\]")


def normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    t = " ".join(t.split())
    return t.casefold()


def quote_found_in_source(
    quote: str,
    source_text: str,
    *,
    fuzzy: bool = False,
    fuzzy_threshold: int = 97,
) -> bool:
    nq = normalize_text(quote)
    ns = normalize_text(source_text)
    if nq in ns:
        return True
    if fuzzy:
        try:
            from rapidfuzz.fuzz import partial_ratio
        except ImportError:
            return False
        return partial_ratio(nq, ns) >= fuzzy_threshold
    return False


def validate_report_citations(report: Report, accepted_finding_ids: set[str]) -> list[str]:
    errors: list[str] = []
    citation_ns = {c.n for c in report.citations}
    texts = [report.executive_summary] + [s.body_markdown for s in report.sections]
    markers: list[int] = []
    for text in texts:
        markers.extend(int(m) for m in _CITATION_RE.findall(text))
    if not markers:
        errors.append("no citation markers found")
        return errors
    for n in markers:
        if n not in citation_ns:
            errors.append(f"citation marker [{n}] has no Citation entry")
    expected = list(range(1, max(markers) + 1))
    seen_order = []
    for n in markers:
        if n not in seen_order:
            seen_order.append(n)
    if seen_order != expected[: len(seen_order)]:
        errors.append("citation numbering is not sequential from first use")
    for c in report.citations:
        for fid in c.finding_ids:
            if fid not in accepted_finding_ids:
                errors.append(f"citation references unknown finding {fid}")
    for section in report.sections:
        for fid in section.finding_ids:
            if fid not in accepted_finding_ids:
                errors.append(f"section references unknown finding {fid}")
        if not _CITATION_RE.search(section.body_markdown):
            errors.append(f"section {section.heading!r} has no citation markers")
    if not _CITATION_RE.search(report.executive_summary):
        errors.append("executive_summary has no citation markers")
    return errors

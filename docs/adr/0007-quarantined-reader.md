# ADR-0007: Quarantined Reader with verbatim-quote verification

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
Web pages are untrusted and may contain prompt-injection payloads. Reports must be trustworthy and auditable.

## Decision
- Only the Reader agent receives raw page text. It has no tools and returns a strictly typed `ReaderOutput`.
- Every finding must include a verbatim `evidence_quote`; code verifies the quote exists in the stored source text (after normalization) before the finding is accepted.
- Critic, Writer, and Curator see only accepted findings, never raw pages.
- The Writer may cite only accepted findings from the same run.

## Rationale
- Limits the blast radius of injection: a compromised Reader can only emit data that is then verified and treated as untrusted content downstream.
- Makes hallucinated citations structurally impossible to reach the report.
- Gives the UI a concrete, auditable artifact (the quote) for every claim.

## Consequences
- Some true but loosely paraphrased claims will be rejected; the Reader prompt and an optional fuzzy-match setting tune this trade-off, measured by the eval suite.
- Extra cost from chunked Reader calls; mitigated by chunk relevance filtering and a cheaper Reader model.
- Downstream agents still treat findings as data, not instructions.

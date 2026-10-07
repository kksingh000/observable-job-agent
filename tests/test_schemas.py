"""Schema invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from job_scout.graph.schemas import CVContent, JobPosting, Profile, RankedJob, TailoredBullet, TailoringPack
from tests.conftest import make_job


def test_ranked_job_score_bounds():
    job = make_job("j1", "Data Scientist", "Acme")
    RankedJob(job=job, fit_score=0, fit_explanation="x")
    RankedJob(job=job, fit_score=100, fit_explanation="x")
    with pytest.raises(ValidationError):
        RankedJob(job=job, fit_score=101, fit_explanation="x")
    with pytest.raises(ValidationError):
        RankedJob(job=job, fit_score=-1, fit_explanation="x")


def test_job_posting_source_literal():
    JobPosting(job_id="1", title="t", company="c", location="l", source="adzuna")
    with pytest.raises(ValidationError):
        JobPosting(job_id="1", title="t", company="c", location="l", source="linkedin")


def test_tailored_bullet_requires_corpus_ref():
    TailoredBullet(text="Built a model", corpus_ref="cv-bullet-001")
    with pytest.raises(ValidationError):
        TailoredBullet(text="Built a model")


def test_tailoring_pack_v2_shape():
    pack = TailoringPack(
        cv=CVContent(headline="ML Engineer", summary="Builds models."),
        cover_letter="Dear team,",
    )
    assert pack.cv.experience == []
    assert pack.honesty_note == ""


def test_profile_list_fields_accept_null_and_normalize_to_empty_list():
    """Regression test for a live 400 from Groq's tool-call schema validation.

    When a CV has nothing for a given field (e.g. no languages listed), some
    models emit `null` for that field instead of `[]`. Groq enforces the tool
    schema server-side, so a plain `list[str]` type rejects the whole call
    before it ever reaches this code. These fields must accept `null` and
    normalize it to `[]` so every other call site can keep treating them as
    plain lists.
    """
    profile = Profile(
        name="Krishna",
        primary_roles=None,
        skills=None,
        locations=None,
        languages=None,
    )
    assert profile.primary_roles == []
    assert profile.skills == []
    assert profile.locations == []
    assert profile.languages == []


def test_profile_list_fields_json_schema_allows_null():
    """The JSON schema handed to the LLM as a tool must mark these nullable."""
    schema = Profile.model_json_schema()
    for field in ("primary_roles", "skills", "locations", "languages"):
        types_offered = {branch.get("type") for branch in schema["properties"][field]["anyOf"]}
        assert "null" in types_offered
        assert "array" in types_offered

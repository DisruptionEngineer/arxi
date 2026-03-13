import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from arxi.modules.intake.models import Prescription, RxStatus
from arxi.modules.patient.matcher import MatchResult, PatientMatcher
from arxi.modules.patient.models import Patient
from arxi.modules.patient.service import PatientService
from arxi.events import Event


async def _make_rx(db, first="John", last="Doe", dob="1990-01-15") -> Prescription:
    rx = Prescription(
        source="e-prescribe",
        status=RxStatus.PARSED,
        patient_first_name=first,
        patient_last_name=last,
        patient_dob=dob,
        drug_description="Test Drug 10mg",
    )
    db.add(rx)
    await db.flush()
    await db.commit()
    return rx


async def _make_patient(db, first="John", last="Doe", dob="1990-01-15") -> Patient:
    svc = PatientService(db)
    return await svc.create({
        "first_name": first,
        "last_name": last,
        "gender": "M",
        "date_of_birth": dob,
    })


# --- Tier 1 ---

async def test_tier1_exact_match_links_patient(db):
    patient = await _make_patient(db)
    rx = await _make_rx(db)
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        result = await matcher.match_and_link(rx)
    assert result.outcome == "linked"
    assert result.patient_id == patient.id
    assert result.tier == 1
    assert result.confidence == "high"
    assert rx.patient_id == patient.id


async def test_tier1_nickname_match(db):
    patient = await _make_patient(db, first="Robert")
    rx = await _make_rx(db, first="Bob")
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        result = await matcher.match_and_link(rx)
    assert result.outcome == "linked"
    assert result.patient_id == patient.id
    assert result.tier == 1


async def test_tier1_suffix_ignored(db):
    patient = await _make_patient(db, last="Smith")
    rx = await _make_rx(db, last="Smith Jr")
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        result = await matcher.match_and_link(rx)
    assert result.outcome == "linked"
    assert result.patient_id == patient.id
    assert result.tier == 1


# --- Tier 1 -> Tier 2 fallthrough ---

async def test_tier1_multiple_matches_falls_to_tier2(db):
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    rx = await _make_rx(db)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": '{"match": null, "reason": "ambiguous"}'}

    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch("pharmagent.modules.patient.matcher.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            matcher = PatientMatcher(db)
            result = await matcher.match_and_link(rx)

    assert result.outcome == "created"
    assert result.tier == 3


# --- Tier 2 ---

async def test_tier2_llm_returns_match(db):
    p1 = await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    p2 = await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    rx = await _make_rx(db)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": json.dumps({"match": p1.id, "confidence": "high", "reason": "same address"})
    }

    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch("pharmagent.modules.patient.matcher.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            matcher = PatientMatcher(db)
            result = await matcher.match_and_link(rx)

    assert result.outcome == "linked"
    assert result.patient_id == p1.id
    assert result.tier == 2


async def test_tier2_llm_returns_null(db):
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    rx = await _make_rx(db)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": json.dumps({"match": None, "reason": "no confident match"})
    }

    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch("pharmagent.modules.patient.matcher.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            matcher = PatientMatcher(db)
            result = await matcher.match_and_link(rx)

    assert result.outcome == "created"
    assert result.tier == 3


async def test_tier2_llm_timeout_falls_to_tier3(db):
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    await _make_patient(db, first="John", last="Doe", dob="1990-01-15")
    rx = await _make_rx(db)

    import httpx as real_httpx

    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        with patch("pharmagent.modules.patient.matcher.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=real_httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client
            matcher = PatientMatcher(db)
            result = await matcher.match_and_link(rx)

    assert result.outcome == "created"
    assert result.tier == 3


# --- Tier 3 ---

async def test_tier3_no_candidates_creates_patient(db):
    rx = await _make_rx(db, first="Brand", last="New", dob="2000-01-01")
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        result = await matcher.match_and_link(rx)
    assert result.outcome == "created"
    assert result.patient_id is not None
    assert result.tier == 3
    assert result.confidence == "low"
    svc = PatientService(db)
    patient = await svc.get(result.patient_id)
    assert patient is not None
    assert patient.first_name == "Brand"
    assert patient.last_name == "New"
    assert rx.patient_id == result.patient_id


# --- Event publishing ---

async def test_tier1_publishes_patient_linked_event(db):
    patient = await _make_patient(db)
    rx = await _make_rx(db)
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        await matcher.match_and_link(rx)
        mock_bus.publish.assert_called_once()
        evt = mock_bus.publish.call_args[0][0]
        assert isinstance(evt, Event)
        assert evt.type == "patient.linked"
        assert evt.data["patient_id"] == patient.id
        assert evt.data["match_tier"] == 1


async def test_tier3_publishes_patient_created_event(db):
    rx = await _make_rx(db, first="NewPerson", last="Test", dob="1999-01-01")
    with patch("pharmagent.modules.patient.matcher.event_bus") as mock_bus:
        mock_bus.publish = AsyncMock()
        matcher = PatientMatcher(db)
        await matcher.match_and_link(rx)
        mock_bus.publish.assert_called_once()
        evt = mock_bus.publish.call_args[0][0]
        assert isinstance(evt, Event)
        assert evt.type == "patient.created"
        assert evt.data["patient_name"] == "NewPerson Test"

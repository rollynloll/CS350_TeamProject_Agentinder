"""
test_domain_events.py — DomainEvent 서브클래스 생성 및 필드 단위 테스트.

테스트 대상: backend/app/pubsub/domain_events.py
호출 위치: pytest 수집 시 자동 실행.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.pubsub.domain_events import (
    DateEnded,
    DateProposed,
    DateStarted,
    DomainEvent,
    MatchCreated,
    MessageCreated,
)


class TestDomainEventBase:
    """DomainEvent 베이스 클래스 공통 필드 테스트."""

    def test_event_id_is_uuid(self) -> None:
        event = DomainEvent()
        assert isinstance(event.event_id, UUID)

    def test_event_id_is_unique_per_instance(self) -> None:
        e1 = DomainEvent()
        e2 = DomainEvent()
        assert e1.event_id != e2.event_id

    def test_occurred_at_is_utc_aware(self) -> None:
        event = DomainEvent()
        assert event.occurred_at.tzinfo is not None
        assert event.occurred_at.tzinfo == timezone.utc

    def test_occurred_at_is_recent(self) -> None:
        before = datetime.now(timezone.utc)
        event = DomainEvent()
        after = datetime.now(timezone.utc)
        assert before <= event.occurred_at <= after

    def test_custom_event_id_accepted(self) -> None:
        eid = uuid4()
        event = DomainEvent(event_id=eid)
        assert event.event_id == eid


class TestMatchCreated:
    """MatchCreated 이벤트 필드 테스트."""

    def test_match_created_has_match_id(self) -> None:
        ev = MatchCreated()
        assert isinstance(ev.match_id, UUID)

    def test_match_created_has_agent_a_id(self) -> None:
        ev = MatchCreated()
        assert isinstance(ev.agent_a_id, UUID)

    def test_match_created_has_agent_b_id(self) -> None:
        ev = MatchCreated()
        assert isinstance(ev.agent_b_id, UUID)

    def test_match_created_principal_ids_default_to_none(self) -> None:
        ev = MatchCreated()
        assert ev.principal_a_id is None
        assert ev.principal_b_id is None

    def test_match_created_all_fields_set(self) -> None:
        mid = uuid4()
        a_id = uuid4()
        b_id = uuid4()
        pa_id = uuid4()
        pb_id = uuid4()
        ev = MatchCreated(
            match_id=mid,
            agent_a_id=a_id,
            agent_b_id=b_id,
            principal_a_id=pa_id,
            principal_b_id=pb_id,
        )
        assert ev.match_id == mid
        assert ev.agent_a_id == a_id
        assert ev.agent_b_id == b_id
        assert ev.principal_a_id == pa_id
        assert ev.principal_b_id == pb_id

    def test_match_created_inherits_domain_event(self) -> None:
        ev = MatchCreated()
        assert isinstance(ev, DomainEvent)

    def test_match_created_instances_have_unique_event_ids(self) -> None:
        ev1 = MatchCreated()
        ev2 = MatchCreated()
        assert ev1.event_id != ev2.event_id


class TestDateProposed:
    """DateProposed 이벤트 필드 테스트."""

    def test_date_proposed_has_date_id(self) -> None:
        ev = DateProposed()
        assert isinstance(ev.date_id, UUID)

    def test_date_proposed_has_match_id(self) -> None:
        ev = DateProposed()
        assert isinstance(ev.match_id, UUID)

    def test_date_proposed_principal_ids_default_to_none(self) -> None:
        ev = DateProposed()
        assert ev.proposer_principal_id is None
        assert ev.target_principal_id is None

    def test_date_proposed_all_fields_set(self) -> None:
        did = uuid4()
        mid = uuid4()
        proposer = uuid4()
        target = uuid4()
        ev = DateProposed(
            date_id=did,
            match_id=mid,
            proposer_principal_id=proposer,
            target_principal_id=target,
        )
        assert ev.date_id == did
        assert ev.match_id == mid
        assert ev.proposer_principal_id == proposer
        assert ev.target_principal_id == target

    def test_date_proposed_inherits_domain_event(self) -> None:
        ev = DateProposed()
        assert isinstance(ev, DomainEvent)


class TestDateStarted:
    """DateStarted 이벤트 필드 테스트."""

    def test_date_started_has_date_id(self) -> None:
        ev = DateStarted()
        assert isinstance(ev.date_id, UUID)

    def test_date_started_has_match_id(self) -> None:
        ev = DateStarted()
        assert isinstance(ev.match_id, UUID)

    def test_date_started_all_fields_set(self) -> None:
        did = uuid4()
        mid = uuid4()
        ev = DateStarted(date_id=did, match_id=mid)
        assert ev.date_id == did
        assert ev.match_id == mid

    def test_date_started_inherits_domain_event(self) -> None:
        ev = DateStarted()
        assert isinstance(ev, DomainEvent)


class TestDateEnded:
    """DateEnded 이벤트 필드 테스트."""

    def test_date_ended_has_date_id(self) -> None:
        ev = DateEnded()
        assert isinstance(ev.date_id, UUID)

    def test_date_ended_outcome_defaults_to_none(self) -> None:
        ev = DateEnded()
        assert ev.outcome is None

    def test_date_ended_outcome_set(self) -> None:
        ev = DateEnded(outcome="success")
        assert ev.outcome == "success"

    def test_date_ended_all_fields_set(self) -> None:
        did = uuid4()
        mid = uuid4()
        ev = DateEnded(date_id=did, match_id=mid, outcome="no_show")
        assert ev.date_id == did
        assert ev.match_id == mid
        assert ev.outcome == "no_show"

    def test_date_ended_inherits_domain_event(self) -> None:
        ev = DateEnded()
        assert isinstance(ev, DomainEvent)


class TestMessageCreated:
    """MessageCreated 이벤트 필드 테스트."""

    def test_message_created_has_message_id(self) -> None:
        ev = MessageCreated()
        assert isinstance(ev.message_id, UUID)

    def test_message_created_has_match_id(self) -> None:
        ev = MessageCreated()
        assert isinstance(ev.match_id, UUID)

    def test_message_created_has_sender_agent_id(self) -> None:
        ev = MessageCreated()
        assert isinstance(ev.sender_agent_id, UUID)

    def test_message_created_content_defaults_to_empty_string(self) -> None:
        ev = MessageCreated()
        assert ev.content == ""

    def test_message_created_all_fields_set(self) -> None:
        msg_id = uuid4()
        mid = uuid4()
        sender = uuid4()
        ev = MessageCreated(
            message_id=msg_id,
            match_id=mid,
            sender_agent_id=sender,
            content="hello",
        )
        assert ev.message_id == msg_id
        assert ev.match_id == mid
        assert ev.sender_agent_id == sender
        assert ev.content == "hello"

    def test_message_created_empty_content_allowed(self) -> None:
        ev = MessageCreated(content="")
        assert ev.content == ""

    def test_message_created_unicode_content(self) -> None:
        ev = MessageCreated(content="안녕하세요 ")
        assert ev.content == "안녕하세요 "

    def test_message_created_inherits_domain_event(self) -> None:
        ev = MessageCreated()
        assert isinstance(ev, DomainEvent)

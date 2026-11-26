"""Persistence, tenant-boundary and audit-event regression tests."""
import unittest
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from enterprise_core.database import initialize_schema
from enterprise_core.models import AuditEvent, InvestigationCase
from enterprise_core.cases import create_case, get_case, list_cases, list_case_events, transition_case


class EnterpriseCaseStoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        initialize_schema(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.tenant_a = str(uuid4())
        self.tenant_b = str(uuid4())
        self.actor = "analyst-01"

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_case_persists_with_creation_audit(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            title="Suspicious transfer", description="Synthetic test case",
        )
        self.session.commit()
        loaded = get_case(self.session, tenant_id=self.tenant_a, case_id=case.id)
        self.assertEqual(loaded.title, "Suspicious transfer")
        events = list(self.session.scalars(select(AuditEvent)))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "case.created")

    def test_tenant_scope_denies_other_tenant_lookup_and_list(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            title="Tenant A case",
        )
        self.session.commit()
        self.assertIsNone(get_case(self.session, tenant_id=self.tenant_b, case_id=case.id))
        self.assertEqual(list_cases(self.session, tenant_id=self.tenant_b), [])

    def test_case_transition_creates_audit_event(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            title="Case lifecycle",
        )
        transition_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            case_id=case.id, new_status="in_review",
        )
        self.session.commit()
        self.assertEqual(case.status, "in_review")
        events = list(self.session.scalars(
            select(AuditEvent).order_by(AuditEvent.event_type)
        ))
        self.assertEqual({event.event_type for event in events},
                         {"case.created", "case.status_changed"})

    def test_closed_case_cannot_be_reopened(self):
        case = create_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            title="Closed case",
        )
        transition_case(self.session, tenant_id=self.tenant_a, actor_id=self.actor,
                        case_id=case.id, new_status="closed")
        with self.assertRaises(ValueError):
            transition_case(self.session, tenant_id=self.tenant_a, actor_id=self.actor,
                            case_id=case.id, new_status="open")

    def test_audit_event_rejects_orm_mutation_and_delete(self):
        create_case(self.session, tenant_id=self.tenant_a, actor_id=self.actor,
                    title="Audit immutability")
        self.session.commit()
        audit = self.session.scalar(select(AuditEvent))
        audit.event_type = "forged"
        with self.assertRaises(ValueError):
            self.session.flush()
        self.session.rollback()

        audit = self.session.scalar(select(AuditEvent))
        self.session.delete(audit)
        with self.assertRaises(ValueError):
            self.session.flush()

    def test_validation_and_bounded_pagination(self):
        with self.assertRaises(ValueError):
            create_case(self.session, tenant_id="not-a-uuid", actor_id=self.actor,
                        title="Invalid tenant")
        with self.assertRaises(ValueError):
            list_cases(self.session, tenant_id=self.tenant_a, limit=1000)
        with self.assertRaises(ValueError):
            create_case(self.session, tenant_id=self.tenant_a, actor_id=self.actor,
                        title=" ")

    def test_case_timeline_is_tenant_scoped_and_ordered(self):
        case = create_case(self.session, tenant_id=self.tenant_a,
                           actor_id=self.actor, title="Timeline")
        transition_case(self.session, tenant_id=self.tenant_a,
                        actor_id=self.actor, case_id=case.id,
                        new_status="in_review")
        self.session.commit()
        events = list_case_events(self.session, tenant_id=self.tenant_a,
                                  case_id=case.id)
        self.assertEqual([e.event_type for e in events],
                         ["case.created", "case.status_changed"])
        self.assertEqual(list_case_events(self.session, tenant_id=self.tenant_b,
                                          case_id=case.id), [])

    def test_timeline_limit_is_bounded(self):
        case = create_case(self.session, tenant_id=self.tenant_a,
                           actor_id=self.actor, title="Bounded timeline")
        with self.assertRaises(ValueError):
            list_case_events(self.session, tenant_id=self.tenant_a,
                             case_id=case.id, limit=500)

    def test_unknown_case_transition_returns_none(self):
        self.assertIsNone(transition_case(
            self.session, tenant_id=self.tenant_a, actor_id=self.actor,
            case_id=str(uuid4()), new_status="closed",
        ))


if __name__ == "__main__":
    unittest.main()

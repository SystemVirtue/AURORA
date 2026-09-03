"""End-to-end proof that authoritative cognitive state survives a fresh Supabase reset."""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from aurora.continuity import export_workspace
from aurora.continuity_restore import restore_workspace

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
USER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
WORKSPACE_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
SOURCE_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
SESSION_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
EVENT_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
MESSAGE_ID = uuid.UUID("60000000-0000-0000-0000-000000000001")
DOCUMENT_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
CLAIM_ID = uuid.UUID("80000000-0000-0000-0000-000000000001")
EVIDENCE_ID = uuid.UUID("90000000-0000-0000-0000-000000000001")
ENTITY_A = uuid.UUID("a0000000-0000-0000-0000-000000000001")
ENTITY_B = uuid.UUID("a0000000-0000-0000-0000-000000000002")
RELATIONSHIP_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
BELIEF_ID = uuid.UUID("c0000000-0000-0000-0000-000000000001")
MEMORY_ID = uuid.UUID("d0000000-0000-0000-0000-000000000001")
GOAL_ID = uuid.UUID("e0000000-0000-0000-0000-000000000001")
DECISION_ID = uuid.UUID("f0000000-0000-0000-0000-000000000001")
RUN_ID = uuid.UUID("11000000-0000-0000-0000-000000000001")
GAP_ID = uuid.UUID("12000000-0000-0000-0000-000000000001")


def create_test_user(conn: psycopg.Connection) -> None:
    conn.execute(
        """insert into auth.users
           (id, aud, role, email, encrypted_password, raw_app_meta_data,
            raw_user_meta_data, created_at, updated_at)
           values (%s, 'authenticated', 'authenticated', %s, '', %s, %s, now(), now())
           on conflict (id) do nothing""",
        (
            USER_ID,
            "aurora-reincarnation@example.invalid",
            Jsonb({"provider": "email", "providers": ["email"]}),
            Jsonb({}),
        ),
    )


def seed_authoritative_state(conn: psycopg.Connection) -> None:
    create_test_user(conn)
    conn.execute(
        "insert into public.workspaces (id,name,slug,created_by) values (%s,%s,%s,%s)",
        (WORKSPACE_ID, "Reincarnation Test", "reincarnation-test", USER_ID),
    )
    conn.execute(
        "insert into public.workspace_members (workspace_id,user_id,role) values (%s,%s,'owner')",
        (WORKSPACE_ID, USER_ID),
    )
    conn.execute(
        "insert into public.sources (id,workspace_id,source_type,name,metadata) values (%s,%s,'document','test-source',%s)",
        (SOURCE_ID, WORKSPACE_ID, Jsonb({"test": True})),
    )
    conn.execute(
        "insert into public.sessions (id,workspace_id,user_id,title) values (%s,%s,%s,'reincarnation session')",
        (SESSION_ID, WORKSPACE_ID, USER_ID),
    )
    conn.execute(
        """insert into public.events
           (id,workspace_id,session_id,event_type,producer_type,producer_id,payload)
           values (%s,%s,%s,'test.created','human',%s,%s)""",
        (EVENT_ID, WORKSPACE_ID, SESSION_ID, USER_ID, Jsonb({"fixture": "reincarnation"})),
    )
    conn.execute(
        """insert into public.messages
           (id,workspace_id,session_id,event_id,role,content,sequence_no,source_id)
           values (%s,%s,%s,%s,'user','The durable state must survive a reset.',1,%s)""",
        (MESSAGE_ID, WORKSPACE_ID, SESSION_ID, EVENT_ID, SOURCE_ID),
    )
    conn.execute(
        """insert into public.documents
           (id,workspace_id,source_id,name,mime_type,content,metadata)
           values (%s,%s,%s,'test.txt','text/plain',%s,%s)""",
        (
            DOCUMENT_ID,
            WORKSPACE_ID,
            SOURCE_ID,
            "AURORA preserves authoritative cognitive state across infrastructure changes.",
            Jsonb({"fixture": True}),
        ),
    )
    conn.execute(
        """insert into public.claims
           (id,workspace_id,source_id,event_id,subject,predicate,object,assertion_status,confidence,metadata)
           values (%s,%s,%s,%s,'AURORA','preserves','authoritative state','supported',0.9,%s)""",
        (CLAIM_ID, WORKSPACE_ID, SOURCE_ID, EVENT_ID, Jsonb({"fixture": True})),
    )
    conn.execute(
        """insert into public.evidence
           (id,workspace_id,claim_id,source_id,event_id,relation,strength,excerpt,metadata)
           values (%s,%s,%s,%s,%s,'supports',0.9,'authoritative state survives',%s)""",
        (EVIDENCE_ID, WORKSPACE_ID, CLAIM_ID, SOURCE_ID, EVENT_ID, Jsonb({"fixture": True})),
    )
    conn.execute(
        "insert into public.entities (id,workspace_id,entity_type,canonical_name) values (%s,%s,'system','AURORA'),(%s,%s,'concept','continuity')",
        (ENTITY_A, WORKSPACE_ID, ENTITY_B, WORKSPACE_ID),
    )
    conn.execute(
        """insert into public.relationships
           (id,workspace_id,source_entity_id,target_entity_id,rel_type,metadata)
           values (%s,%s,%s,%s,'demonstrates',%s)""",
        (RELATIONSHIP_ID, WORKSPACE_ID, ENTITY_A, ENTITY_B, Jsonb({"fixture": True})),
    )
    conn.execute(
        """insert into public.beliefs
           (id,workspace_id,claim_id,state_type,confidence)
           values (%s,%s,%s,'fact',0.9)""",
        (BELIEF_ID, WORKSPACE_ID, CLAIM_ID),
    )
    conn.execute(
        """insert into public.memories
           (id,workspace_id,claim_id,memory_type,status,confidence,rationale)
           values (%s,%s,%s,'semantic','active',0.9,'reincarnation fixture')""",
        (MEMORY_ID, WORKSPACE_ID, CLAIM_ID),
    )
    conn.execute(
        "insert into public.goals (id,workspace_id,title,description) values (%s,%s,'Prove continuity','Survive a clean database reset')",
        (GOAL_ID, WORKSPACE_ID),
    )
    conn.execute(
        """insert into public.reasoning_runs
           (id,workspace_id,session_id,question,mode,status,answer,confidence)
           values (%s,%s,%s,'Can state survive reset?','balanced','completed','Yes.',0.9)""",
        (RUN_ID, WORKSPACE_ID, SESSION_ID),
    )
    conn.execute(
        """insert into public.model_contributions
           (reasoning_run_id,model_id,provider,role,response,confidence,evidence_ids)
           values (%s,'fixture-model','test','reasoner','Yes.',0.9,%s)""",
        (RUN_ID, [EVIDENCE_ID]),
    )
    conn.execute(
        """insert into public.decisions
           (id,workspace_id,event_id,title,decision,rationale,confidence)
           values (%s,%s,%s,'Continuity decision','Treat authoritative state as portable','Fixture',0.9)""",
        (DECISION_ID, WORKSPACE_ID, EVENT_ID),
    )
    conn.execute(
        """insert into public.epistemic_gaps
           (id,workspace_id,reasoning_run_id,claim_id,description,gap_type,severity,status)
           values (%s,%s,%s,%s,'Fresh-machine verification is required','verification_required',0.2,'open')""",
        (GAP_ID, WORKSPACE_ID, RUN_ID, CLAIM_ID),
    )
    conn.commit()


def counts(conn: psycopg.Connection) -> dict[str, int]:
    tables = (
        "workspace_members", "sources", "sessions", "events", "messages", "documents",
        "claims", "evidence", "entities", "relationships", "beliefs", "memories",
        "goals", "decisions", "reasoning_runs", "model_contributions", "epistemic_gaps",
        "document_chunks",
    )
    return {
        table: conn.execute(
            f"select count(*) from public.{table} where workspace_id=%s",
            (WORKSPACE_ID,),
        ).fetchone()[0]
        if table != "model_contributions"
        else conn.execute(
            "select count(*) from public.model_contributions mc join public.reasoning_runs rr on rr.id=mc.reasoning_run_id where rr.workspace_id=%s",
            (WORKSPACE_ID,),
        ).fetchone()[0]
        for table in tables
    }


def verify_belief_revision(conn: psycopg.Connection) -> None:
    new_belief_id = conn.execute(
        "select public.revise_claim(%s, 'contested', %s, %s, %s)",
        (CLAIM_ID, USER_ID, 0.55, "Contradictory evidence requires a contested state."),
    ).fetchone()[0]
    current = conn.execute(
        """select id, state_type, confidence, upper_inf(valid_during)
             from public.beliefs
            where claim_id=%s and workspace_id=%s and upper_inf(valid_during)
            order by created_at desc limit 1""",
        (CLAIM_ID, WORKSPACE_ID),
    ).fetchone()
    previous = conn.execute(
        """select id, state_type, superseded_by, upper_inf(valid_during)
             from public.beliefs
            where id=%s""",
        (BELIEF_ID,),
    ).fetchone()
    claim_status = conn.execute(
        "select assertion_status, confidence from public.claims where id=%s",
        (CLAIM_ID,),
    ).fetchone()
    review_event = conn.execute(
        "select count(*) from public.events where workspace_id=%s and event_type='claim.reviewed' and producer_id=%s",
        (WORKSPACE_ID, USER_ID),
    ).fetchone()[0]
    assert new_belief_id == current[0]
    assert current[1] == "belief"
    assert current[2] == 0.55
    assert current[3] is True
    assert previous[0] == BELIEF_ID
    assert previous[1] == "fact"
    assert previous[2] == new_belief_id
    assert previous[3] is False
    assert claim_status == ("contested", 0.55)
    assert review_event == 1
    conn.rollback()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aurora-reincarnation-") as temp_dir:
        bundle = Path(temp_dir) / "bundle"
        with psycopg.connect(DB_URL) as conn:
            seed_authoritative_state(conn)
            before = counts(conn)
            export_workspace(conn, str(WORKSPACE_ID), bundle)

        subprocess.run(["npx", "supabase", "db", "reset"], check=True)

        with psycopg.connect(DB_URL) as conn:
            create_test_user(conn)
            conn.commit()
            result = restore_workspace(
                conn,
                bundle,
                str(WORKSPACE_ID),
                user_id_map={str(USER_ID): str(USER_ID)},
            )
            after = counts(conn)
            assert result["restored"] is True
            assert result["rebuilt"]["document_chunks"] > 0
            assert before["document_chunks"] == 0
            assert after["document_chunks"] == result["rebuilt"]["document_chunks"]
            authoritative_before = {key: value for key, value in before.items() if key != "document_chunks"}
            authoritative_after = {key: value for key, value in after.items() if key != "document_chunks"}
            assert authoritative_after == authoritative_before, (
                f"authoritative state mismatch before={authoritative_before} after={authoritative_after}"
            )
            assert conn.execute(
                "select content from public.document_chunks where document_id=%s order by chunk_index",
                (DOCUMENT_ID,),
            ).fetchone()[0].startswith("AURORA preserves")
            verify_belief_revision(conn)

    print("AURORA reincarnation + belief-revision proof: PASS")
    print(f"authoritative + derived row counts: {after}")


if __name__ == "__main__":
    main()

"""
Unit Tests — Memory Subsystem and Dynamic Relationship Matrix
"""
import pytest
import asyncio
from pathlib import Path
from laptop.memory.db import MemoryDB
from laptop.memory.consolidate import MemoryConsolidator

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_memory.db"
    return MemoryDB({"memory": {"db_path": str(db_file)}})

def test_relationship_matrix_evolution(test_db):
    async def _test():
        # Interaction 1 & 2 -> STRANGER
        await test_db.log_interaction("Victor", "Hello", "Greetings", mood="calm")
        rel1 = await test_db.get_relationship("Victor")
        assert rel1["relationship_mode"] == "STRANGER"

        # 3 interactions -> OBSERVED
        await test_db.log_interaction("Victor", "Status", "Nominal")
        await test_db.log_interaction("Victor", "Check", "Acknowledged")
        rel2 = await test_db.get_relationship("Victor")
        assert rel2["relationship_mode"] == "OBSERVED"
        assert rel2["interaction_count"] == 3

        # 10 interactions -> ASSOCIATE
        for _ in range(7):
            await test_db.log_interaction("Victor", "Query", "Answer")
        rel3 = await test_db.get_relationship("Victor")
        assert rel3["relationship_mode"] == "ASSOCIATE"
        assert rel3["interaction_count"] == 10

    asyncio.run(_test())

def test_remember_and_get_facts(test_db):
    async def _test():
        await test_db.remember_fact("Bruce", "preference", "dark mode")
        await test_db.remember_fact("Bruce", "affiliation", "Batcave")

        facts = await test_db.get_facts("Bruce")
        assert facts["preference"] == "dark mode"
        assert facts["affiliation"] == "Batcave"

    asyncio.run(_test())

def test_search_memory(test_db):
    async def _test():
        await test_db.log_interaction("Tony", "Deploy the Mark 42 armor", "Armor deployed")
        await test_db.remember_fact("Tony", "project", "Mark 42 nanotech")

        # Search conversations
        results = await test_db.search_memory("Mark 42", user="Tony")
        assert len(results) >= 1
        assert any("Mark 42" in r.get("user_said", "") or "Mark 42" in r.get("value", "") for r in results)

    asyncio.run(_test())

def test_cascading_forget_user(test_db):
    async def _test():
        await test_db.log_interaction("Clark", "Up and away", "Acknowledged")
        await test_db.remember_fact("Clark", "weakness", "kryptonite")

        # Confirm data exists
        assert len(await test_db.get_facts("Clark")) > 0

        # Purge
        await test_db.forget_user("Clark")

        # Verify cascade
        assert len(await test_db.get_facts("Clark")) == 0
        assert (await test_db.get_relationship("Clark"))["interaction_count"] == 0

    asyncio.run(_test())

def test_memory_consolidator(test_db):
    async def _test():
        for i in range(12):
            await test_db.log_interaction("Natasha", f"Inquiry about protocol telemetry {i}", f"Status {i}")

        consolidator = MemoryConsolidator(test_db)
        res = await consolidator.consolidate("Natasha")
        assert res["status"] == "SUCCESS"
        facts = await test_db.get_facts("Natasha")
        assert "frequent_inquiry_topics" in facts

    asyncio.run(_test())

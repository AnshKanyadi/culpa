"""
Tests for team management — create, invite, join, membership.
"""

from __future__ import annotations

import pytest
from server.storage.database import init_db, get_db
from server.storage.team_repository import TeamRepository, InviteRepository
from server.storage.user_repository import UserRepository
from server.services.auth import hash_password
import server.storage.database as db_mod


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_mod._connection = None
    conn = init_db(str(tmp_path / "test.db"))
    # Create two test users
    pw = hash_password("password123")
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, plan) VALUES (?, ?, ?, ?, ?)",
        ("user1", "alice@example.com", pw, "Alice", "pro"),
    )
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, plan) VALUES (?, ?, ?, ?, ?)",
        ("user2", "bob@example.com", pw, "Bob", "pro"),
    )
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, plan) VALUES (?, ?, ?, ?, ?)",
        ("user3", "carol@example.com", pw, "Carol", "free"),
    )
    conn.commit()
    yield
    db_mod._connection = None


team_repo = TeamRepository()
invite_repo = InviteRepository()


def test_create_team():
    team = team_repo.create("team1", "Engineering", "user1")
    assert team["name"] == "Engineering"
    assert team["owner_id"] == "user1"


def test_owner_is_member():
    team_repo.create("team1", "Engineering", "user1")
    assert team_repo.is_member("team1", "user1")
    assert not team_repo.is_member("team1", "user2")


def test_owner_role():
    team_repo.create("team1", "Engineering", "user1")
    assert team_repo.get_role("team1", "user1") == "owner"


def test_add_member():
    team_repo.create("team1", "Engineering", "user1")
    team_repo.add_member("team1", "user2")
    assert team_repo.is_member("team1", "user2")
    assert team_repo.get_role("team1", "user2") == "member"


def test_list_members():
    team_repo.create("team1", "Engineering", "user1")
    team_repo.add_member("team1", "user2")
    members = team_repo.get_members("team1")
    assert len(members) == 2
    emails = {m["email"] for m in members}
    assert emails == {"alice@example.com", "bob@example.com"}


def test_remove_member():
    team_repo.create("team1", "Engineering", "user1")
    team_repo.add_member("team1", "user2")
    assert team_repo.remove_member("team1", "user2")
    assert not team_repo.is_member("team1", "user2")


def test_cannot_remove_owner():
    team_repo.create("team1", "Engineering", "user1")
    assert not team_repo.remove_member("team1", "user1")
    assert team_repo.is_member("team1", "user1")


def test_list_teams_for_user():
    team_repo.create("team1", "Engineering", "user1")
    team_repo.create("team2", "Design", "user2")
    team_repo.add_member("team2", "user1")
    teams = team_repo.list_for_user("user1")
    assert len(teams) == 2
    names = {t["name"] for t in teams}
    assert names == {"Engineering", "Design"}


def test_get_teammate_ids():
    team_repo.create("team1", "Engineering", "user1")
    team_repo.add_member("team1", "user2")
    teammates = team_repo.get_teammate_ids("user1")
    assert teammates == {"user2"}


def test_invite_create_and_accept():
    team_repo.create("team1", "Engineering", "user1")
    invite = invite_repo.create("inv1", "team1", "bob@example.com", "user1")
    assert invite["email"] == "bob@example.com"
    assert invite["accepted_at"] is None

    pending = invite_repo.list_pending_for_email("bob@example.com")
    assert len(pending) == 1

    assert invite_repo.accept("inv1")
    pending = invite_repo.list_pending_for_email("bob@example.com")
    assert len(pending) == 0


def test_invite_pending_for_team():
    team_repo.create("team1", "Engineering", "user1")
    invite_repo.create("inv1", "team1", "bob@example.com", "user1")
    invite_repo.create("inv2", "team1", "carol@example.com", "user1")
    pending = invite_repo.list_pending_for_team("team1")
    assert len(pending) == 2

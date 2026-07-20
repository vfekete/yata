"""Checks on tests/fixtures/mock_tasks.json, the 3-day mock dataset used to
visually spot-check day-grouping, status-sort and long-text word-wrap (see
BUILD.md for how to load it into a real run of the app)."""
import json
import os
import shutil
from collections import Counter

import pytest

from models import TaskListModel
from storage import STATUS_ACTIVE, STATUS_CANCELLED, STATUS_DONE, TaskStore

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "mock_tasks.json")


@pytest.fixture
def loaded_model(tmp_path):
    dest = tmp_path / "tasks.json"
    shutil.copy(FIXTURE_PATH, dest)
    return TaskListModel(TaskStore(path=str(dest)))


def test_fixture_has_21_tasks_across_3_days(loaded_model):
    days = Counter(t.created_at[:10] for t in loaded_model._tasks)
    assert len(loaded_model._tasks) == 21
    assert len(days) == 3


def test_fixture_day_status_breakdown_matches_spec(loaded_model):
    by_day = {}
    for t in loaded_model._tasks:
        by_day.setdefault(t.created_at[:10], Counter())[t.status] += 1

    day1, day2, day3 = sorted(by_day)
    assert by_day[day1] == Counter({STATUS_ACTIVE: 6, STATUS_DONE: 6, STATUS_CANCELLED: 3})
    assert by_day[day2] == Counter({STATUS_DONE: 5})
    assert by_day[day3] == Counter({STATUS_CANCELLED: 1})


def test_fixture_includes_a_512_char_markdown_task(loaded_model):
    longest = max(loaded_model._tasks, key=lambda t: len(t.text))
    assert len(longest.text) >= 512
    # Uses several of the markdown styles Text.MarkdownText renders.
    assert "**" in longest.text  # bold
    assert "*" in longest.text.replace("**", "")  # italic
    assert "`" in longest.text  # inline code
    assert "~~" in longest.text  # strikethrough
    assert "[actually done](" in longest.text  # link


def test_fixture_is_valid_task_json():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    assert {frozenset(item) for item in raw} == {frozenset({"text", "status", "created_at", "id"})}

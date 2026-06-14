"""Tests for Phase 1 — Analyzer (analyzer.py)."""

from __future__ import annotations

import pytest

from scripts.agent.orchestration.spec import WorkSpec, FileGroup
from scripts.agent.orchestration.analyzer import analyze, estimate_parallelism


class TestAnalyze:
    def test_single_file_group(self):
        ws = WorkSpec(
            description="Refactor UI",
            file_groups=[
                FileGroup(domain_path="domains/math/", files=["index.html", "main.js"]),
            ],
            success_criteria=["Layout matches design"],
        )
        tasks = analyze(ws)
        assert len(tasks) == 1
        assert tasks[0].task_id == "T1"
        assert "domains/math/" in tasks[0].description
        assert "index.html" in tasks[0].target_paths

    def test_multiple_file_groups(self):
        ws = WorkSpec(
            description="Refactor UI",
            file_groups=[
                FileGroup(domain_path="domains/math/", files=["domains/math/index.html"]),
                FileGroup(domain_path="domains/english/", files=["domains/english/index.html"]),
                FileGroup(domain_path="domains/korean/", files=["domains/korean/index.html"]),
            ],
        )
        tasks = analyze(ws)
        assert len(tasks) == 3
        assert [t.task_id for t in tasks] == ["T1", "T2", "T3"]

    def test_task_scopes_are_domain_isolated(self):
        ws = WorkSpec(
            description="Refactor",
            file_groups=[
                FileGroup(domain_path="domains/math/", files=["domains/math/index.html"]),
                FileGroup(domain_path="domains/english/", files=["domains/english/index.html"]),
            ],
        )
        tasks = analyze(ws)
        assert "domains/math/" in tasks[0].scope
        assert "domains/english/" in tasks[1].scope
        assert "other domain" in tasks[0].scope.lower()

    def test_empty_file_groups_raises(self):
        ws = WorkSpec(description="test", file_groups=[])
        with pytest.raises(ValueError, match="zero file groups"):
            analyze(ws)

    def test_tasks_have_no_circular_dependencies(self):
        ws = WorkSpec(
            description="test",
            file_groups=[
                FileGroup(domain_path="domains/math/", files=["a.html"]),
                FileGroup(domain_path="domains/english/", files=["b.html"]),
            ],
        )
        tasks = analyze(ws)
        for t in tasks:
            assert t.dependencies == []

    def test_goal_uses_first_success_criteria(self):
        ws = WorkSpec(
            description="test",
            file_groups=[FileGroup(domain_path="domains/math/", files=["a.html"])],
            success_criteria=["Criterion A", "Criterion B"],
        )
        tasks = analyze(ws)
        assert "Criterion A" in tasks[0].goal


class TestEstimateParallelism:
    def test_empty_tasks_defaults_to_cap(self):
        # Edge case: 0 files → defaults to max cap
        n = estimate_parallelism([])
        assert n == 3

    def test_five_files_or_less(self):
        TaskMock = type('T', (), {'target_paths': None})
        tasks = [
            TaskMock(target_paths=['a', 'b']),
            TaskMock(target_paths=['c', 'd']),
            TaskMock(target_paths=['e']),
        ]
        # 5 files total, 3 tasks → N=2~3
        n = estimate_parallelism(tasks)
        assert 2 <= n <= 3

    def test_more_than_five_files(self):
        TaskMock = type('T', (), {'target_paths': None})
        tasks = [
            TaskMock(target_paths=['a', 'b', 'c']),
            TaskMock(target_paths=['d', 'e', 'f']),
            TaskMock(target_paths=['g', 'h']),
        ]
        # 8 files total → N=4~5, capped by task count (3)
        n = estimate_parallelism(tasks)
        assert 3 <= n <= 5

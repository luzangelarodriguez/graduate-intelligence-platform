import pytest

from crawlers.queues.postgres_queue import QUEUE_SCHEMA_SQL, QueueItem, PostgresCrawlerQueue


def test_queue_schema_contains_required_tables() -> None:
    assert "crawler_jobs_queue" in QUEUE_SCHEMA_SQL
    assert "crawler_job_results" in QUEUE_SCHEMA_SQL
    assert "crawler_failures" in QUEUE_SCHEMA_SQL
    assert "crawler_execution_logs" in QUEUE_SCHEMA_SQL
    assert "crawler_metrics" in QUEUE_SCHEMA_SQL
    assert "crawler_dead_letter_queue" in QUEUE_SCHEMA_SQL
    assert "priority INTEGER" in QUEUE_SCHEMA_SQL


def test_queue_rejects_invalid_status_before_db_call() -> None:
    queue = PostgresCrawlerQueue()

    with pytest.raises(ValueError):
        queue.enqueue(QueueItem(source_name="test", status="bad"))

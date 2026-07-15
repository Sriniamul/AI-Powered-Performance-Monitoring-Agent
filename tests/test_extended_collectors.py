from agent.collectors.disk_collector import DiskCollector
from agent.collectors.network_collector import NetworkCollector


def test_disk_collector_reports_capacity():
    metrics = DiskCollector().collect()
    assert 0 <= metrics["disk_percent"] <= 100
    assert metrics["disk_total_gb"] > 0


def test_network_collector_reports_activity_fields():
    metrics = NetworkCollector().collect()
    assert "network_sent_mb_s" in metrics
    assert "network_received_mb_s" in metrics


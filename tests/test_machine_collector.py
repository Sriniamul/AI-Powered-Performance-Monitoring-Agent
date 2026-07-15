from agent.collectors.machine_collector import MachineCollector


def test_machine_collector_identifies_deployment_machine():
    details = MachineCollector().collect()

    assert details["machine_name"]
    assert details["operating_system"]
    assert details["os_environment"]
    assert details["architecture"]

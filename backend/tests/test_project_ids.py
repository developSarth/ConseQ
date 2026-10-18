from app.services.project_ids import is_project_graph_id


def test_accepts_current_and_legacy_project_graph_ids():
    assert is_project_graph_id("proj_1234abcd")
    assert is_project_graph_id("proj_" + "a" * 32)


def test_rejects_non_generated_graph_names():
    assert not is_project_graph_id("echo_software")
    assert not is_project_graph_id("proj_echo_software")
    assert not is_project_graph_id("proj_1234abcg")
    assert not is_project_graph_id("proj_" + "a" * 31)

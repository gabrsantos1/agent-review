from pathlib import Path

from qualitybridge.adapters import factory_for
from qualitybridge.models import ProjectConfig, SuiteConfig


def test_playwright_uses_project_install_and_report_environment():
    config = ProjectConfig(project="Web", runner="playwright")
    adapter = factory_for("playwright").create_adapter()
    report = Path("some path") / "raw.xml"
    args = adapter.command(config, SuiteConfig(paths=["tests"], filter="@smoke"), Path("."), report)
    assert args == [
        "node",
        "node_modules/@playwright/test/cli.js",
        "test",
        "--reporter=junit",
        "--grep",
        "@smoke",
        "tests",
    ]
    assert adapter.environment(report)["PLAYWRIGHT_JUNIT_OUTPUT_FILE"] == str(report)

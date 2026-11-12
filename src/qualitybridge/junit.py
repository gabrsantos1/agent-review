from pathlib import Path
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import parse

from qualitybridge.models import RunResult, TestCase


def read_junit(path: Path) -> list[TestCase]:
    root = parse(path).getroot()
    if root.tag not in ("testsuites", "testsuite"):
        raise ValueError("O arquivo não contém um relatório JUnit válido.")
    cases = []
    for node in root.iter("testcase"):
        status, message = "passed", ""
        for tag, mapped in (("error", "error"), ("failure", "failed"), ("skipped", "skipped")):
            child = node.find(tag)
            if child is not None:
                status = mapped
                message = "\n".join(filter(None, [child.get("message"), child.text]))
                break
        cases.append(
            TestCase(
                name=node.get("name", "sem nome"),
                classname=node.get("classname", ""),
                status=status,
                duration_seconds=float(node.get("time", "0")),
                message=message,
            )
        )
    # Some tools report collection/global errors at suite level, without a testcase.
    for suite in root.iter("testsuite"):
        for tag in ("error", "failure"):
            for child in suite.findall(tag):
                cases.append(
                    TestCase(
                        name="Erro da suíte",
                        classname=suite.get("name", ""),
                        status="error",
                        message=child.get("message", "") + "\n" + (child.text or ""),
                    )
                )
        if int(suite.get("errors", "0")) + int(suite.get("failures", "0")) > 0 and not any(
            c.status in ("error", "failed") for c in cases
        ):
            cases.append(
                TestCase(
                    name="Erro informado pelo executor",
                    status="error",
                    message="O executor informou erros sem detalhar os casos.",
                )
            )
    return cases


def write_junit(result: RunResult, path: Path) -> None:
    counts = result.counts
    infrastructure = result.status in ("error", "timeout", "cancelled", "no_tests")
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root,
        "testsuite",
        name=result.project,
        tests=str(len(result.cases) + int(infrastructure)),
        failures=str(counts["failed"]),
        errors=str(counts["error"] + int(infrastructure)),
        skipped=str(counts["skipped"]),
        time=f"{result.duration_seconds:.6f}",
    )
    for case in result.cases:
        node = ET.SubElement(
            suite,
            "testcase",
            name=case.name,
            classname=case.classname,
            time=str(case.duration_seconds),
        )
        if case.status != "passed":
            tag = {"failed": "failure", "error": "error", "skipped": "skipped"}[case.status]
            ET.SubElement(node, tag, message=case.message.split("\n")[0]).text = case.message
    if infrastructure:
        node = ET.SubElement(
            suite,
            "testcase",
            name="QualityBridge: " + result.status,
            classname="qualitybridge.execution",
            time="0",
        )
        ET.SubElement(node, "error", message=result.status).text = "\n".join(result.diagnostics)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

from pathlib import Path

from portproject_rag.tender_workflow import TenderWorkflowService


def _service(tmp_path: Path) -> TenderWorkflowService:
    service = TenderWorkflowService()
    service.storage_path = tmp_path / "tender_workflows.json"
    return service


def test_tender_sources_expose_only_eligible_vacant_plots(tmp_path: Path) -> None:
    service = _service(tmp_path)

    plots = service.list_plots()
    assert len(plots) > 0
    assert all(plot["id"] and plot["area_sqm"] for plot in plots)
    assert service.config_payload()["checklists"]


def test_tender_calculation_requires_approved_inputs_and_is_deterministic(tmp_path: Path) -> None:
    service = _service(tmp_path)

    pending = service.calculate({"area_sqm": "100"})
    ready = service.calculate(
        {
            "area_sqm": "100",
            "lease_years": "10",
            "fsi": "2",
            "approved_monthly_sor_rate": "20",
            "annual_escalation_percent": "5",
            "discount_rate_percent": "8",
            "gst_percent": "18",
        }
    )
    assert pending["ready"] is False
    assert ready["ready"] is True
    assert round(ready["upfront_premium_including_gst"], 2) == 500597.81


def test_tender_workflow_state_and_pdf_are_source_backed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    plot = service.list_plots()[0]
    checklist = service.checklist("embarkation")
    workflow = service.create_workflow(
        {
            "plot_id": plot["id"],
            "checklist_key": "embarkation",
            "fields": {"proposed_use": "approved use", "tender_method": "E-tender"},
            "checklist_answers": {},
        }
    )

    workflow = service.apply_action(
        workflow["id"],
        {
            "action": "submit_lac",
            "fields": {"proposed_use": "approved use", "tender_method": "E-tender"},
            "checklist_answers": {item["key"]: item.get("source_answer", "") for item in checklist["items"]},
        },
    )
    pdf = service.document_pdf(workflow["id"], "lac")

    assert workflow["status"] == "LAC_SUBMITTED"
    assert workflow["lac_submission_pending"]["fields"] == []
    assert pdf.startswith(b"%PDF")

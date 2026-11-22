import json
from pathlib import Path
from app.main import app
from app.schemas.medication import MedicationDetailDTO, MedicationInformationResponse
from integration.server import app as integration_app

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_b19_openapi_contract_generation():
    schema = app.openapi()
    assert schema["info"]["title"] == "AmbatuFit STB Microservice"
    for path in (
        "/health",
        "/api/v1/health",
        "/api/v1/assessments",
        "/api/v1/profile",
        "/api/v1/guidance",
        "/api/v1/medications",
        "/api/v1/medications/{id}",
        "/api/v1/assessments/{id}/medication-information",
        "/api/v1/bookings",
        "/api/v1/partner/professionals",
        "/api/v1/partner/bookings",
        "/api/v1/partner/recommendations/physical-activity",
        "/api/v1/partner/injury-check",
    ):
        assert path in schema["paths"]

    committed = json.loads((BACKEND_DIR / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    assert committed == schema, "Regenerate contracts/openapi.json after changing API schemas."

    int_committed = json.loads(
        (BACKEND_DIR / "contracts" / "integration-openapi.json").read_text(encoding="utf-8")
    )
    assert int_committed == integration_app.openapi()


def test_b19_fixtures_validity():
    examples_dir = BACKEND_DIR / "contracts" / "examples"
    for path in examples_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    MedicationInformationResponse.model_validate(
        json.loads((examples_dir / "medications-list-unavailable.json").read_text(encoding="utf-8"))
    )
    MedicationInformationResponse.model_validate(
        json.loads((examples_dir / "assessment-medication-restricted.json").read_text(encoding="utf-8"))
    )
    MedicationDetailDTO.model_validate(
        json.loads((examples_dir / "medication-detail-reviewed-example.json").read_text(encoding="utf-8"))
    )

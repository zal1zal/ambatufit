import json
import os
import pytest
from app.main import app


def test_b19_openapi_contract_generation():
    schema = app.openapi()
    assert schema["info"]["title"] == "AmbatuFit STB Microservice"
    assert "/health" in schema["paths"]
    assert "/api/v1/assessments" in schema["paths"]
    assert "/api/v1/profile" in schema["paths"]
    assert "/api/v1/guidance" in schema["paths"]
    assert "/api/v1/bookings" in schema["paths"]
    assert "/api/v1/partner/professionals" in schema["paths"]


def test_b19_fixtures_validity():
    examples_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "contracts",
        "examples",
    )
    for fname in os.listdir(examples_dir):
        if fname.endswith(".json"):
            with open(os.path.join(examples_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                assert isinstance(data, dict)


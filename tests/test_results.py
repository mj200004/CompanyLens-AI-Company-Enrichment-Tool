from __future__ import annotations

from app import db
from app.models import EnrichmentResult


def test_create_read_and_delete_result(app, client):
    with app.app_context():
        result = EnrichmentResult(
            source_url="https://example.com/",
            normalized_domain="example.com",
            website_name="Example",
            company_name="Example Inc",
            address="1 Market Street",
            primary_phone="+1 555 123 4567",
            emails=["hello@example.com"],
            phones=["+1 555 123 4567"],
            services_summary="Revenue automation platform",
            target_customers="B2B sales teams",
            pain_points="Manual pipeline management",
            value_proposition="Structured company research with better data quality",
            outreach_opener="Saw your positioning around revenue operations and thought this would be relevant.",
            source_pages=["https://example.com/", "https://example.com/about"],
            extraction_method="heuristic",
            confidence=0.72,
        )
        db.session.add(result)
        db.session.commit()
        result_id = result.id

    list_response = client.get("/api/results")
    assert list_response.status_code == 200
    rows = list_response.get_json()
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Example Inc"
    assert rows[0]["domain"] == "example.com"

    detail_response = client.get(f"/api/results/{result_id}")
    assert detail_response.status_code == 200
    detail = detail_response.get_json()
    assert detail["website_name"] == "Example"
    assert detail["emails"] == ["hello@example.com"]

    clear_response = client.post("/api/results/clear")
    assert clear_response.status_code == 200
    assert clear_response.get_json()["deleted"] == 1

    empty_response = client.get("/api/results")
    assert empty_response.status_code == 200
    assert empty_response.get_json() == []

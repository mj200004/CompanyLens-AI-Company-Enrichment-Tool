from __future__ import annotations

from app import db
from app.utils import utc_now


class EnrichmentResult(db.Model):
    __tablename__ = "enrichment_results"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    source_url = db.Column(db.String(2048), nullable=False, index=True)
    normalized_domain = db.Column(db.String(255), nullable=False, index=True)

    website_name = db.Column(db.String(255), nullable=True)
    company_name = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=True)
    primary_phone = db.Column(db.String(128), nullable=True)

    emails = db.Column(db.JSON, nullable=False, default=list)
    phones = db.Column(db.JSON, nullable=False, default=list)

    services_summary = db.Column(db.Text, nullable=True)
    target_customers = db.Column(db.Text, nullable=True)
    pain_points = db.Column(db.Text, nullable=True)
    value_proposition = db.Column(db.Text, nullable=True)
    outreach_opener = db.Column(db.Text, nullable=True)

    source_pages = db.Column(db.JSON, nullable=False, default=list)
    extraction_method = db.Column(db.String(32), nullable=False, default="heuristic")
    confidence = db.Column(db.Float, nullable=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "url": self.source_url,
            "domain": self.normalized_domain,
            "website_name": self.website_name,
            "company_name": self.company_name,
            "address": self.address,
            "primary_phone": self.primary_phone,
            "emails": self.emails or [],
            "phones": self.phones or [],
            "services_summary": self.services_summary,
            "target_customers": self.target_customers,
            "pain_points": self.pain_points,
            "value_proposition": self.value_proposition,
            "outreach_opener": self.outreach_opener,
            "source_pages": self.source_pages or [],
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
        }

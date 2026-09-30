from foundry_cosmos_demo.synthetic_data import (
    build_embedding_inputs,
    build_synthetic_guidance_documents,
)


def test_documents_are_synthetic_and_customer_agnostic() -> None:
    documents = build_synthetic_guidance_documents(8)

    assert len(documents) == 8
    assert len({document["id"] for document in documents}) == 8
    assert all(document["sourceType"] == "synthetic" for document in documents)
    assert all("real patient data" in document["content"] for document in documents)


def test_embedding_inputs_capture_searchable_fields() -> None:
    documents = build_synthetic_guidance_documents(2)
    payloads = build_embedding_inputs(documents)

    assert len(payloads) == 2
    assert documents[0]["title"] in payloads[0]
    assert documents[0]["summary"] in payloads[0]
    assert "tags:" in payloads[0]


def test_default_matrix_is_diverse_before_repeating() -> None:
    documents = build_synthetic_guidance_documents(960)

    assert {document["conditionGroup"] for document in documents} == {
        "cardiometabolic",
        "respiratory",
        "musculoskeletal",
        "behavioral-health",
        "preventive-care",
    }
    assert {document["careSetting"] for document in documents} == {
        "primary-care",
        "virtual-visit",
        "urgent-care-triage",
        "care-management",
    }
    assert {document["population"] for document in documents} == {
        "adult",
        "older-adult",
        "working-parent",
        "college-student",
    }
    assert {document["intent"] for document in documents} == {
        "self-management",
        "medication-education",
        "follow-up-planning",
        "escalation-triage",
    }
    assert {document["riskLevel"] for document in documents} == {
        "routine",
        "watchful",
        "priority",
    }

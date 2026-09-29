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

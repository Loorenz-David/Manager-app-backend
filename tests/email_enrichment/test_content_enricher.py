from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext
from beyo_manager.services.infra.email_enrichment.enricher import ContentEnricher


def test_content_enricher_replaces_known_vars_and_keeps_unknown_vars() -> None:
    enricher = ContentEnricher(
        {
            "customer_name": lambda _ctx: "Alice",
            "task_state": lambda _ctx: "Ready",
        }
    )

    result = enricher.enrich(
        "Hej {{customer_name}}, task is {{task_state}} and {{unknown_var}} stays.",
        EnrichmentContext(),
    )

    assert result == "Hej Alice, task is Ready and {{unknown_var}} stays."


def test_content_enricher_returns_empty_string_for_empty_input() -> None:
    enricher = ContentEnricher({})

    assert enricher.enrich("", EnrichmentContext()) == ""


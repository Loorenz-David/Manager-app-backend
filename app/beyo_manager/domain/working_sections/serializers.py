from beyo_manager.models.tables.working_sections.working_section import WorkingSection


def serialize_working_section_id_only(section: WorkingSection) -> dict:
    return {"client_id": section.client_id}


def serialize_working_section_full(
    section: WorkingSection,
    dependencies: list[tuple[str, str]],
    categories: list[tuple[str, str]],
    issue_types: list[tuple[str, str]],
) -> dict:
    return {
        "client_id": section.client_id,
        "name": section.name,
        "image": section.image,
        "dependencies": [
            {"client_id": dep_id, "name": dep_name} for dep_id, dep_name in dependencies
        ],
        "item_categories": [
            {"client_id": cat_id, "name": cat_name} for cat_id, cat_name in categories
        ],
        "supported_issue_types": [
            {"client_id": it_id, "name": it_name} for it_id, it_name in issue_types
        ],
    }

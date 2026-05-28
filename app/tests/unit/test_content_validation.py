import pytest

from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.infra.content import validate_content


@pytest.mark.unit
def test_validate_content_accepts_marks_object():
    blocks = validate_content([
        {
            "type": "text",
            "text": "hello",
            "marks": {"bold": True, "color": "#ff0000"},
        }
    ])

    assert len(blocks) == 1
    assert blocks[0].marks == {"bold": True, "color": "#ff0000"}


@pytest.mark.unit
def test_validate_content_rejects_marks_non_object():
    with pytest.raises(ValidationError, match="Content block 'marks' must be an object"):
        validate_content([
            {
                "type": "text",
                "text": "hello",
                "marks": ["bold"],
            }
        ])

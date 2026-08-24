from typing import Any

from pydantic import RootModel


def root_model_openapi_extension(model: type[RootModel]) -> dict[str, Any]:
    json_schema: dict[str, Any] = model.model_json_schema()
    document_name = model.document_name  # type: ignore[attr-defined]
    examples = ""
    root_field = model.model_fields.get("root")
    body_required = root_field.is_required() if root_field else True
    if root_field and root_field.examples:
        if isinstance(root_field.examples, list):
            examples = root_field.examples[0]
        else:
            examples = root_field.examples
    content: dict[str, Any] = {}
    for media_type in model.supported_types:  # type: ignore[attr-defined]
        content[media_type] = {
            "schema": json_schema,
            "example": examples[media_type] if isinstance(examples, dict) and media_type in examples else examples,
        }
    content["application/octet-stream"] = {
        "title": "File upload",
        "schema": {"type": "string", "format": "binary"},
        "description": f"Upload {document_name} as a file",
        "example": examples[media_type] if isinstance(examples, dict) and media_type in examples else examples,
    }
    return {
        "requestBody": {
            "required": body_required,
            "content": content,
            "description": (
                "Document as raw body: pick a text Content-Type to paste, or application/octet-stream to upload a file"
            ),
        },
    }

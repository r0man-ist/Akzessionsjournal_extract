# utils/llm.py
from __future__ import annotations
import os
from dotenv import load_dotenv
from openai import OpenAI


def build_client(base_url: str, timeout: int) -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing.")
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def simplify_schema(schema: dict) -> dict:
    """Rewrite a Pydantic-generated JSON schema into the flatter shape
    strict structured-output providers expect: no anyOf/null unions,
    additionalProperties=false, every field required."""
    defs = schema.pop("$defs", {})

    def resolve_refs(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve_refs(defs[node["$ref"].split("/")[-1]])
            return {k: resolve_refs(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve_refs(v) for v in node]
        return node

    schema = resolve_refs(schema)

    def simplify(node):
        if not isinstance(node, dict):
            return node
        if "anyOf" in node:
            types, item_schema = [], None
            for sub in node["anyOf"]:
                sub = simplify(sub)
                t = sub.get("type")
                if t == "null":
                    types.append("null")
                elif t:
                    types.append(t)
                    if t == "array":
                        item_schema = sub.get("items")
                elif "items" in sub:
                    item_schema = sub["items"]
            node = {"type": types if len(types) > 1 else types[0]}
            if item_schema is not None:
                node["items"] = item_schema
        if node.get("type") == "object" or "properties" in node:
            props = node.get("properties", {})
            node["properties"] = {k: simplify(v) for k, v in props.items()}
            node["required"] = list(node["properties"].keys())
            node["additionalProperties"] = False
        if node.get("type") == "array" and "items" in node:
            node["items"] = simplify(node["items"])
        node.pop("title", None)
        node.pop("default", None)
        return node

    return simplify(schema)


def response_format(model_cls, name: str) -> dict:
    schema = simplify_schema(model_cls.model_json_schema())
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}}
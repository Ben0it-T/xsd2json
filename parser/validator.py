# -*- coding: utf-8 -*-

import copy
import json
from jsonschema import (
    Draft4Validator, Draft6Validator, Draft7Validator,
    Draft201909Validator, Draft202012Validator
)

def validate_json_schema(schema_path):
    """
    Validates that a JSON file is a valid JSON schema according to the specification

    Args:
        schema_path (str): JSON schema to validate
    """

    # Open the schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_to_validate = json.load(f)

    # Get schema version and validator class
    version = schema_to_validate.get('$schema')
    if "draft-04" in version:
        ValidatorClass = Draft4Validator
        schema_version = "draft-04"
    elif "draft-06" in version:
        ValidatorClass = Draft6Validator
        schema_version = "draft-06"
    elif "draft-07" in version:
        ValidatorClass = Draft7Validator
        schema_version = "draft-07"
    elif "2019-09" in version:
        ValidatorClass = Draft201909Validator
        schema_version = "draft-2019-09"
    elif "2020-12" in version:
        ValidatorClass = Draft202012Validator
        schema_version = "draft-2020-12"
    else:
         ValidatorClass = Draft7Validator
         schema_version = "draft-07"

    # Create a validator and traverse subschemas
    try:
        with open(f"./json-schema/{schema_version}.json", "r", encoding="utf-8") as f:
            meta_schema = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Metaschema file not found for '{schema_version}', skipping validation")
        return

    validator = ValidatorClass(meta_schema)
    errors = sorted(validator.iter_errors(schema_to_validate), key=lambda e: e.path)

    if errors:
        print("❌ Errors found in JSON Schema:")
        for err in errors:
            path = ".".join(str(x) for x in err.path) if err.path else "(racine)"
            print(f"- Path '{path}': {err.message}")

    else:
        print("✅ Valid JSON Schema.")

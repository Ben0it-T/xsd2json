# xsd2json

**_For development and test environment._**

Python script to transform an XML Schema (XSD) files into equivalent JSON Schemas.


## Requirements

- Python `3.10+`
- [lxml](https://pypi.org/project/lxml/)
- [jsonschema](https://pypi.org/project/jsonschema/)
- [pyyaml](https://pypi.org/project/PyYAML/)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python xsd2json.py path/to/schema.xsd
```

Outputs will be saved under the ./output directory:
- JSON Definitions:
  - elements_defs.json
  - simple_type_defs.json
  - complex_type_defs.json
- JSON Schema:
  - with_defs.json — contains $defs
  - resolved.json — fully flattened schema
- YAML file - contains properties

## Limitations

XSD is a rich and complex standard, and many XSDs will not be supported and cannot be converted by this script.

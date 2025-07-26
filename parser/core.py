# -*- coding: utf-8 -*-

import os
import sys
import datetime
import json
import yaml
import copy
from pathlib import Path
from os.path import exists as path_exists
from lxml import etree

from .transform import Transformer
from .validator import validate_json_schema

class XSDParser:

    def __init__(self, xsd_file_path, json_schema):
        # Check if xsd_file_path in an XSD Schema
        if not self.is_xsd_file(xsd_file_path):
            print(f'❌ <inputfile> is not a valid XSD file')
            sys.exit()

        # Create output directory
        output_path = './output'
        os.makedirs(output_path, exist_ok=True)

        # Vars
        xsd_filename = os.path.basename(xsd_file_path)
        self.xsd_path = os.path.dirname(xsd_file_path) or "."

        json_schema_versions = {
            'draft-04': "https://json-schema.org/draft-04/schema",
            'draft-06': "https://json-schema.org/draft-06/schema",
            'draft-07': "https://json-schema.org/draft-07/schema",
            'draft-2019-09': "https://json-schema.org/draft/2019-09/schema",
            'draft-2020-123': "https://json-schema.org/draft/2020-12/schema"
        }
        if json_schema in json_schema_versions:
            json_schema_uri = json_schema_versions[json_schema]
        else:
            json_schema = 'draft-07'
            json_schema_uri = json_schema_versions['draft-07']

        self.xsd_schema_included = []
        self.xsd_elements_defs = {}
        self.xsd_simple_type_defs = {}
        self.xsd_complex_type_defs = {}
        self.xsd_flatten = {}

        print(f"\nXSD schema\n  - path: {self.xsd_path}\n  - filename: {xsd_filename}")
        print(f"\nJSON schema\n  - version: {json_schema}\n  - metaschema: {json_schema_uri}")

        # Parse & flatten XSD
        xsd_tree = self.parse_xsd_file(xsd_file_path)

        # Create a flattened version of the XSD schema
        # Create a root element with nsmap
        print(f"\nCreate flattened XSD schema")
        print(f"Add namespaces:")
        for ns, val in xsd_tree.nsmap.items():
            print(f"  - {ns}: {val}")
        nsmap = xsd_tree.nsmap
        self.xsd_flatten = etree.Element("{http://www.w3.org/2001/XMLSchema}schema", nsmap=nsmap)

        # Add attributes
        print(f"Add attributes:")
        for attr, val in xsd_tree.attrib.items():
            if not attr.startswith("xmlns"):
                print(f"  - {attr}: {val}")
                self.xsd_flatten.set(f"{attr}", f"{val}")

        # Flatten the XSD schema
        print(f"Flattening the XSD schema")
        for elem in list(xsd_tree):
            if self.is_include_node(elem):
                schema_location = elem.get("schemaLocation")
                if schema_location not in self.xsd_schema_included:
                    self.xsd_schema_included.append(schema_location)
                    self.flatten_xsd_schema(self.xsd_path + '/' + schema_location)
                    print(f"  - {schema_location}")
                else:
                    print(f"  - {schema_location} has already been imported")
            else:
                self.xsd_flatten.append(copy.deepcopy(elem))

        if not self.xsd_schema_included:
            print(f"  > Nothing to flatten")

        # Save flattened version of the XSD schema to file
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        xsd_flattened_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_flattened.xsd"
        self.xsd_to_file(xsd_flattened_filename, self.xsd_flatten)

        # Transform (convert) XSD to JSON Schema
        self.transform = Transformer(json_schema)

        # Extract top-level elements
        print(f"\nExtract top-level elements")
        self.xsd_elements_defs = self.transform.extract_elements(self.xsd_flatten)
        print(f"  > elements: {len(self.xsd_elements_defs.get('properties'))}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_elements_defs.json"
        self.json_to_file(json_filename, self.xsd_elements_defs)

        # Extract top-level simpleType
        print(f"\nExtract simpleType")
        self.xsd_simple_type_defs = self.transform.extract_simple_types(self.xsd_flatten)
        print(f"  > simpleType: {len(self.xsd_simple_type_defs)}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_simple_type_defs.json"
        self.json_to_file(json_filename, self.xsd_simple_type_defs)

        # Extract top-level complexType
        print(f"\nExtract complexType")
        self.xsd_complex_type_defs = self.transform.extract_complex_types(self.xsd_flatten)
        print(f"  > complexType: {len(self.xsd_complex_type_defs)}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_complex_type_defs.json"
        self.json_to_file(json_filename, self.xsd_complex_type_defs)

        # Build full JSON Schema with defs
        print(f"\nCreate JSON schema with defs")
        json_schema_with_defs = {
            '$schema': json_schema_uri,
            'version': "0.0.1",
            'title': xsd_filename.split('.')[0],
            'type': "object",
        }

        # Add elements_defs
        json_schema_with_defs.update(self.xsd_elements_defs)

        # Add full defs
        full_defs = {}
        full_defs.update(self.xsd_simple_type_defs)
        full_defs.update(self.xsd_complex_type_defs)
        json_schema_with_defs["$defs"] =  full_defs

        # Write JSON Schema to file
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_with_defs.json"
        self.json_to_file(json_filename, json_schema_with_defs)

        # Validate schema
        validate_json_schema(json_filename)

        # Resolved $defs schema
        print(f"\nResolve $defs")
        resolved =  self.flatten_json_schema(json_schema_with_defs, full_defs)
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_resolved.json"
        self.json_to_file(json_filename, resolved)

        # Validate schema
        validate_json_schema(json_filename)

        # Dump properties into yaml and save to file
        yaml_string = yaml.dump(resolved)
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        yaml_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_properties.yaml"
        self.yaml_to_file(yaml_filename, resolved["properties"])


    def is_xsd_file(self, file_path):
        """
        Checks if the given file is a valid XSD file.
        Checks if:
        - the file can be opened and parsed as XML.
        - the root element is an <xsd:schema>.
        - the namespace matches the standard XML Schema namespace.

        Args:
            file_path (str): Full path to the file to check.

        Returns:
            bool: True if the file is a valid XSD, False otherwise.
        """
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            return etree.QName(root.tag).localname == "schema" and \
                   etree.QName(root.tag).namespace == "http://www.w3.org/2001/XMLSchema"
        except Exception:
            return False

    def parse_xsd_file(self, file_path):
        """
        Open and parse the XSD Schema

        Args:
            file_path (str): Full path to XSD Schema

        Returns:
            tree
        """
        with open(file_path, 'rb') as file:
            xsd_content = file.read()
        parser = etree.XMLParser(remove_blank_text=True)
        return etree.XML(xsd_content, parser)

    def is_include_node(self, element):
        """
        Checks if the XML element is an <xsd:include> or <xsd:import> tag.
        Checks:
        - that the element belongs to the XML Schema namespace (`http://www.w3.org/2001/XMLSchema`),
        - and that its local name is 'include' or 'import'.

        Args:
            element (etree.Element): An XML element to test.

        Returns:
            bool: True if the element is an <xsd:include> or <xsd:import>, False otherwise.
        """

        if element.tag is etree.Comment:
           return False

        qname = etree.QName(element.tag)
        return True if qname.namespace == "http://www.w3.org/2001/XMLSchema" and (qname.localname == 'include' or qname.localname == 'import') else False


    def flatten_xsd_schema(self, schema_location):
        """
        Flatten XSD Schema

        Args:
            schema_location (str): a schemaLocation
        """
        schema = self.parse_xsd_file(schema_location)
        for elem in list(schema):
            if self.is_include_node(elem):
                schema_location = elem.get("schemaLocation")
                if schema_location not in self.xsd_schema_included:
                    self.xsd_schema_included.append(schema_location)
                    self.flatten_xsd_schema(self.xsd_path + '/' + schema_location)
                    print(f"  - {schema_location}")
                else:
                    print(f"  - {schema_location} has already been imported")
            else:
                # copy elem
                clone = copy.deepcopy(elem)
                self.xsd_flatten.append(clone)


    def flatten_json_schema(self, schema, defs):
        """
        Flatten JSON schema
        """
        resolved = self.resolve_schema(schema, defs)
        if "$defs" in resolved:
            del resolved["$defs"]  # remove unnecessary definitions
        return resolved

    def resolve_schema(self, obj, defs):
        """
        Recursively resolves $refs in a JSON schema.
        """
        if isinstance(obj, dict):
            if "$ref" in obj:
                resolved = self.resolve_ref(obj["$ref"], defs)
                # Recursively resolves what the $ref contains
                return self.resolve_schema(resolved, defs)
            else:
                return {k: self.resolve_schema(v, defs) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.resolve_schema(item, defs) for item in obj]
        else:
            return obj  # Primitive value

    def resolve_ref(self, ref, defs):
        """
        Resolves a #/$defs/xyz reference by returning a deep copy of the contents.
        """
        if not ref.startswith("#/$defs/"):
            print(f"  - ❌ Reference not supported: {ref}")
            return
        key = ref.split("/")[-1]
        if key not in defs:
            print(f"  - ❌ Ref not found in $defs: {key}")
            return
        return copy.deepcopy(defs[key])


    def xsd_to_file(self, filename, tree):
        """
        Write XSD Schema to file

        Args:
            filename (str): filename
            tree (etree.Element): XML tree
        """
        xml_string = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        with open(filename, "wb") as f:
            f.write(xml_string)
        print(f"✅ XSD file written in '{filename}'")

    def json_to_file(self, filename, json_data):
        """
        Write JSON data to file

        Args:
            filename (str): filename
            json_data (dict): JSON data
        """
        with open(filename, "w") as f:
            json.dump(json_data, f, indent=4)
        print(f"✅ JSON representation written in '{filename}'")

    def yaml_to_file(self, filename, json_data):
        """
        Dump JSON data into yaml and save to file

        Args:
            filename (str): filename
            json_data (dict): JSON data
        """
        with open(filename, "w") as f:
            yaml.dump(json_data, f, default_flow_style=False, indent=2, sort_keys=False)
        print(f"✅ JSON representation converted to YAML and written in '{filename}'")

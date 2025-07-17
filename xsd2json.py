# -*- coding: utf-8 -*-

"""
xsd2json.py <inputfile>


Requirements:
- Python 3.10
- jsonschema (https://pypi.org/project/jsonschema/)
- lxml (https://pypi.org/project/lxml/)
"""

import copy
import datetime
import json
import os
import shutil
import sys
import urllib.request

from jsonschema import Draft4Validator, Draft6Validator, Draft7Validator, Draft201909Validator, Draft202012Validator, ValidationError, exceptions
from lxml import etree
from os.path import exists as path_exists
from pathlib import Path



class XSDParser:

    def __init__(self, xsd_file_path, json_schema):

        # Check if xsd_file_path in an XSD Schema
        if not self.is_xsd_file(xsd_file_path):
            print(f'❌ <inputfile> is not a valid XSD file')
            sys.exit()

        # Create output directory
        output_path = './output'
        if not path_exists(output_path):
            os.makedirs(output_path)

        # Vars
        xsd_filename = os.path.basename(xsd_file_path)
        self.xsd_path = os.path.dirname(xsd_file_path)
        if not self.xsd_path:
            self.xsd_path = "."

        self.json_schema = json_schema
        self.json_schema_version = {
            'draft-04': "https://json-schema.org/draft-04/schema",
            'draft-06': "https://json-schema.org/draft-06/schema",
            'draft-07': "https://json-schema.org/draft-07/schema",
            'draft-2019-09': "https://json-schema.org/draft/2019-09/schema",
            'draft-2020-12': "https://json-schema.org/draft/2020-12/schema"
        }

        if json_schema in self.json_schema_version:
            self.json_schema_uri = self.json_schema_version[json_schema]
        else:
            self.json_schema = 'draft-07'
            self.json_schema_uri = self.json_schema_version['draft-07']

        self.xsd_schema_included = []
        self.xsd_data_types = [
            'string', 'normalizedString', 'token', 'language', 'Name', 'NCName', 'QName', 'ENTITY', 'ENTITIES', 'ID', 'IDREF', 'IDREFS', 'NMTOKEN', 'NMTOKENS',
            'byte', 'unsignedByte', 'decimal', 'int', 'unsignedInt', 'integer', 'long', 'unsignedLong', 'negativeInteger', 'nonNegativeInteger', 'nonPositiveInteger', 'positiveInteger', 'short', 'unsignedShort',
            'date', 'dateTime', 'time', 'duration', 'gDay', 'gMonth', 'gMonthDay', 'gYear', 'gYearMonth',
            'anyURI', 'base64Binary', 'boolean', 'double', 'float', 'hexBinary', 'NOTATION'
        ]
        self.xsd_elements_defs = {}
        self.xsd_simple_type_defs = {}
        self.xsd_complex_type_defs = {}

        print(f"\nXSD schema")
        print(f"  - path: {self.xsd_path}")
        print(f"  - filename: {xsd_filename}")

        print(f"\nJSON schema")
        print(f"  - version: {self.json_schema}")
        print(f"  - metaschema: {self.json_schema_uri}")

        # Parse XSD schema
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
                clone = copy.deepcopy(elem)
                self.xsd_flatten.append(clone)
        if not self.xsd_schema_included:
            print(f"  > Nothing to flatten")

        # Save flattened version of the XSD schema to file
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        xsd_flattened_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_flattened.xsd"
        self.xsd_to_file(xsd_flattened_filename, self.xsd_flatten)

        # Extract top-level elements
        print(f"\nExtract top-level elements")
        self.xsd_elements_defs = self.xsd_extract_elements(self.xsd_flatten)
        print(f"  > elements: {len(self.xsd_elements_defs.get('properties'))}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_elements_defs.json"
        self.json_to_file(json_filename, self.xsd_elements_defs)

        # Extract top-level simpleType
        print(f"\nExtract simpleType")
        self.xsd_simple_type_defs = self.extract_simple_types(self.xsd_flatten)
        print(f"  > simpleType: {len(self.xsd_simple_type_defs)}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_simple_type_defs.json"
        self.json_to_file(json_filename, self.xsd_simple_type_defs)

        # Extract top-level complexType
        print(f"\nExtract complexType")
        self.xsd_complex_type_defs = self.extract_complex_types(self.xsd_flatten)
        print(f"  > complexType: {len(self.xsd_complex_type_defs)}")
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_complex_type_defs.json"
        self.json_to_file(json_filename, self.xsd_complex_type_defs)

        # Create JSON Schema with defs
        print(f"\nCreate JSON schema with defs")
        json_schema_with_defs = {
            '$schema': self.json_schema_uri,
            'version': "0.0.1",
            'title': "title",
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
        self.validate_json_schema(json_filename)

        # Resolved $defs schema
        print(f"\nResolve $defs")
        resolved =  self.flatten_json_schema(json_schema_with_defs, full_defs)
        prefix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f")
        json_filename = f"{output_path}/{prefix}_{xsd_filename.split('.')[0]}_resolved.json"
        self.json_to_file(json_filename, resolved)

        # Validate schema
        self.validate_json_schema(json_filename)


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



    def xsd_extract_elements(self, tree):
        """
        Extract top-level elements

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of elements
        """
        elements_defs = {}
        properties = {}
        required = []

        for element in tree.xpath('./xsd:element', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
            name = element.attrib.get('name')
            min_occurs = int(element.attrib.get('minOccurs', '1'))

            if not name:
                continue

            print(f"  - {name}")

            properties[name] = self.xsd_element_to_json(element)
            if min_occurs > 0:
                    required.append(name)

        if properties:
            elements_defs['properties'] = properties

        if required:
            elements_defs['required'] = required

        return elements_defs


    def extract_simple_types(self, tree):
        """
        Extract top-level simpleTypes

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of simpleType
        """

        # xsd:simpleType attributes
        # @name : Specifies a name for the element. This attribute is required if the simpleType element is a child of the schema element, otherwise it is not allowed
        # @id   : optionnal
        # any attributes : Optional. Specifies any other attributes with non-schema namespace

        # xsd:simpleType content (annotation?,(restriction|list|union))
        simple_types_defs = {}

        for simple_type in tree.xpath('./xsd:simpleType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
            description = {}
            name = simple_type.attrib.get('name')
            print(f"  - {name}")

            annotation = simple_type.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if annotation is not None:
                description = self.xsd_annotation_to_json(annotation)

            restriction = simple_type.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if restriction is not None:
                simple_types_defs[name] = self.xsd_restriction_to_json(restriction, "simpleType")

            list_ = simple_type.find('./xsd:list', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if list_ is not None:
                self.xsd_not_supported('list')

            union = simple_type.find('./xsd:union', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if union is not None:
                self.xsd_not_supported('union')

            if description:
                simple_types_defs[name].update(description)

        return simple_types_defs


    def extract_complex_types(self, tree):
        """
        Extract top-level complexTypes

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of complexType
        """

        # xsd:complexType attributes
        # @name : Specifies a name for the element.
        # @id   : Optional. Specifies a unique ID for the element
        # any attributes : Optional. Specifies any other attributes with non-schema namespace

        # xsd:complexType content (annotation?,(simpleContent|complexContent|((group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?))))
        complex_types_defs = {}
        description = {}

        for complex_type in tree.xpath('./xsd:complexType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
            name = complex_type.attrib.get('name')
            if not name:
                continue

            properties = {}
            required = []

            print(f"  - {name}")

            annotation = complex_type.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if annotation is not None:
                description = self.xsd_annotation_to_json(annotation)

            simpleContent = complex_type.find('./xsd:simpleContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if simpleContent is not None:
                complex_types_defs[name] = self.xsd_simple_content_to_json(simpleContent)

            complexContent = complex_type.find('./xsd:complexContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if complexContent is not None:
                complex_types_defs[name] = self.xsd_complex_content_to_json(complexContent)

            choice = complex_type.find('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if choice is not None:
                complex_types_defs[name] = self.xsd_choice_tp_json(choice)

            sequence = complex_type.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if sequence is not None:
                complex_types_defs[name] = self.xsd_sequence_to_json(sequence)

            if description:
                complex_types_defs[name].update(description)


            for element in complex_type:
                tag = etree.QName(element).localname
                if tag not in ["annotation", "simpleContent", "complexContent", "choice", "sequence"]:
                    self.xsd_not_supported(tag)

        return complex_types_defs



    def xsd_not_supported(self, element_name):
        """
        Print message onto the screen

        Args:
            element_name (str): XML element name
        """
        print(f"    ❌ xsd:{element_name} not supported")



    def xsd_data_type_to_json(self, data_type):
        """
        Returns the JSON Schema equivalent for the XML Schema data type

        Args:
            data_type (str): Name of the XSD type (e.g., 'string', 'date', 'positiveInteger', etc.)

        Returns:
            dict: JSON Schema representation of the type
        """

        # String Data Types
        if data_type == "string":
            schema = {'type': "string"}
        elif data_type == "normalizedString":
            schema = {'type': "string"}
        elif data_type == "token":
            schema = {'type': "string"}
        elif data_type == "language":
            schema = {'type': "string", 'pattern': "^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$"}
        elif data_type == "Name":
            schema = {'type': "string"}
        elif data_type == "NCName":
            schema = {'type': "string"}
        elif data_type == "QName":
            schema = {'type': "string"}
        elif data_type == "ENTITY":
            schema = {'type': "string"}
        elif data_type == "ENTITIES":
            schema = {
                'type': "array",
                'items' : {
                    'type' : "string"
                }
            }
        elif data_type == "ID":
            schema = {'type': "string"}
        elif data_type == "IDREF":
            schema = {'type': "string"}
        elif data_type == "IDREFS":
            schema = {
                'type': "array",
                'items' : {
                    'type' : "string"
                }
            }
        elif data_type == "NMTOKEN":
            schema = {'type': "string"}
        elif data_type == "NMTOKENS":
            schema = {
                'type': "array",
                'items' : {
                    'type' : "string"
                }
            }

        # Numeric Data Types
        elif data_type == "byte":
            schema = {'type': "integer"}
        elif data_type == "unsignedByte":
            schema = {'type': "integer", 'minimum': 0}
        elif data_type == "decimal":
            schema = {'type': "number"}
        elif data_type == "int":
            schema = {'type': "integer"}
        elif data_type == "unsignedInt":
            schema = {'type': "integer", 'minimum': 0}
        elif data_type == "integer":
            schema = {'type': "integer"}
        elif data_type == "long":
            schema = {'type': "integer"}
        elif data_type == "unsignedLong":
            schema = {'type': "integer", 'minimum': 0}
        elif data_type == "negativeInteger":
            if self.json_schema == "draft-04":
                schema = {
                    'type': "integer",
                    'maximum': 0,
                    'exclusiveMaximum': True
                }
            else:
                schema = {
                    'type': "integer",
                    'exclusiveMaximum': 0
                }
        elif data_type == "nonNegativeInteger":
            schema = {'type': "integer", 'minimum': 0}
        elif data_type == "nonPositiveInteger":
            schema = {'type': "integer", 'maximum': 0}
        elif data_type == "positiveInteger":
            if self.json_schema == "draft-04":
                schema = {
                    'type': "integer",
                    'minimum': 0,
                    'exclusiveMinimum': True
                }
            else:
                schema = {
                    'type': "integer",
                    'exclusiveMinimum': 0
                }
        elif data_type == "short":
            schema = {'type': "integer"}
        elif data_type == "unsignedShort":
            schema = {'type': "integer", 'minimum': 0}

        # Date and Time Data Types
        elif data_type == "date":
            schema = {'type': "string", 'format': "date"}
        elif data_type == "dateTime":
            schema = {'type': "string", 'format': "date-time"}
        elif data_type == "time":
            schema = {'type': "string", 'format': "time"}
        elif data_type == "duration":
            schema = {'type': "string"}
        elif data_type == "gDay":
            schema = {'type': "integer"}
            # TODO: Need review: type 'string'
        elif data_type == "gMonth":
            schema = {'type': "integer"}
            # TODO: Need review: type 'string'
        elif data_type == "gMonthDay":
            schema = {'type': "string"}
        elif data_type == "gYear":
            schema = {'type': "integer"}
            # TODO: Need review: type 'string'
        elif data_type == "gYearMonth":
            schema = {'type': "string"}

        # Miscellaneous Data Types
        elif data_type == "anyURI":
            schema = {'type': "string", 'format': "uri"}
        elif data_type == "base64Binary":
            schema = {'type': "string", 'pattern': "^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"}
        elif data_type == "boolean":
            schema = {'type': "boolean"}
        elif data_type == "double":
            schema = {'type': "number"}
        elif data_type == "float":
            schema = {'type': "number"}
        elif data_type == "hexBinary":
            schema = {'type': "string", 'pattern': "^([0-9a-fA-F]{2})*$"}
        elif data_type == "NOTATION":
            schema = {'type': "string"}

        else:
            schema = {'type': data_type}

        return schema


    def xsd_annotation_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML Schema annotation

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:annotation content: (appinfo|documentation)*
        description = ""
        for documentation in tree.xpath('./xsd:documentation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
            description += ' '.join(documentation.text.split()) + ' '

        return {'description': description.strip()}


    def xsd_choice_tp_json(self, tree, export_as_properties = False):
        """
        Return the JSON Schema equivalent for the XML Schema choice

        Args:
            tree (etree.Element): XML element to processed
            export_as_properties (bool): True to export as properties, False to export as 'oneOf'

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:choice attributes
        # @id        : Optional. Specifies a unique ID for the element
        # @maxOccurs : Optional. Specifies the maximum number of times the choice element can occur in the parent element. Default value is 1
        # @minOccurs : Optional. Specifies the minimum number of times the choice element can occur in the parent element. Default value is 1

        # (annotation?,(element|group|choice|sequence|any)*)
        choice = {}
        properties = {}
        required = []
        options = []
        one_of = []

        for element in tree:
            tag = etree.QName(element).localname
            if tag == 'element':
                name = element.attrib.get('name')
                min_occurs = int(element.attrib.get('minOccurs', '1'))

                if not name:
                    continue

                if export_as_properties:
                    properties[name] = self.xsd_element_to_json(element)
                    if min_occurs > 0:
                        required.append(name)
                else:
                    options.append({
                        'type': 'object',
                        'properties': {name: self.xsd_element_to_json(element)},
                        'required': [name],
                    })
            else:
                self.xsd_not_supported(tag)

        if options:
            one_of.append({'oneOf': options})

        choice['type'] = "object"

        if properties:
            choice['properties'] = properties

        if one_of:
            choice['oneOf'] = [option for block in one_of for option in block['oneOf']]

        return choice


    def xsd_complex_content_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML Schema complexContent

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd: content: (annotation?,(restriction|extension))
        complex_content_schema = {}
        description = {}

        annotation = tree.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = tree.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            complex_content_schema = self.xsd_restriction_to_json(restriction, "complexContent")

        extension = tree.find('./xsd:extension', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if extension is not None:
            complex_content_schema = self.xsd_extension_to_json(extension)

        return complex_content_schema


    def xsd_complex_type_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML Schema complexType

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:complexType attributes
        # @id   :Optional. Specifies a unique ID for the element
        # @name : Optional. Specifies a name for the element
        # @any attributes: Optional. Specifies any other attributes with non-schema namespace

        # xsd:complexType (annotation?,(simpleContent|complexContent|((group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?))))
        complex_type_schema = {}
        description = {}

        annotation = tree.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        simpleContent = tree.find('./xsd:simpleContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if simpleContent is not None:
            complex_type_schema = self.xsd_simple_content_to_json(simpleContent)

        complexContent = tree.find('./xsd:complexContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if complexContent is not None:
            complex_type_schema = self.xsd_complex_content_to_json(complexContent)

        choice = tree.find('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if choice is not None:
            complex_type_schema = self.xsd_choice_tp_json(choice)

        sequence = tree.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if sequence is not None:
            complex_type_schema = self.xsd_sequence_to_json(sequence)

        attribute = tree.find('./xsd:attribute', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if attribute is not None:
            self.xsd_not_supported('attribute')


        if description:
            complex_type_schema.update(description)

        return complex_type_schema


    def xsd_element_to_json(self, element):
        """
        Return the JSON Schema equivalent for the XML Schema element

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:element attributes
        # @name      : Optional. Specifies a name for the element. This attribute is required if the parent element is the schema element
        # @type      : Optional. Specifies either the name of a built-in data type, or the name of a simpleType or complexType element
        # @maxOccurs : Optional. Default value is 1
        # @minOccurs : Optional. Default value is 1
        type_ = element.attrib.get('type', '').split(':')[-1] or None
        min_occurs = int(element.attrib.get('minOccurs', '1'))
        max_occurs = element.attrib.get('maxOccurs', '1')
        max_occurs = int(99999) if max_occurs == "unbounded" else int(max_occurs)

        # xsd:element content: annotation?,(simpleType|complexType)?,(unique|key|keyref)*
        element_schema = {}
        description = {}
        if type_ is not None:
            if type_ in self.xsd_data_types:
                # built-in data type
                element_schema = self.xsd_data_type_to_json(type_)
            else:
                # simpleType or complexType element
                element_schema = {'$ref': f"#/$defs/{type_}"}
        else:
            annotation = element.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if annotation is not None:
                description = self.xsd_annotation_to_json(annotation)

            simple_type = element.find('./xsd:simpleType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if simple_type is not None:
                element_schema = self.xsd_simple_type_to_json(simple_type)

            complex_type = element.find('./xsd:complexType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if complex_type is not None:
                element_schema = self.xsd_complex_type_to_json(complex_type)


        if not element_schema:
            element_schema = {'type': "string"}

        if description:
            element_schema.update(description)

        if max_occurs > 1:
            element_schema = {
                'type' : "array",
                'minItems' : int(min_occurs),
                'maxItems' : int(max_occurs),
                'items' : element_schema
            }

        return element_schema


    def xsd_extension_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML Schema extension

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:extension attributes
        # base: Required. Specifies the name of a built-in data type, a simpleType element, or a complexType element
        base = tree.attrib.get('base').split(":")[-1]

        # xsd:extension content:
        # (annotation?,((group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?)))

        options = []
        combinations = "allOf"

        if base in self.xsd_data_types:
            # built-in data type
            options.append(self.xsd_data_type_to_json(base))
        else:
            # simpleType or complexType element
            options.append({'$ref': f"#/$defs/{base}"})


        for element in tree:
            tag = etree.QName(element).localname

            if tag == "sequence":
                combinations = "allOf"
                options.append(self.xsd_sequence_to_json(element))

            elif tag == "choice":
                combinations = "anyOf"
                options.append(self.xsd_choice_tp_json(element, True))

            else:
                self.xsd_not_supported(tag)

        extension = {
            'type': "object",
            combinations: options
        }

        return extension


    def xsd_restriction_to_json(self, element, parent_tag):
        """
        Return the JSON Schema equivalent for the XML Restrictions/Facets

        Args:
            element (etree.Element): XML element to processed
            parent_tag (str): parent element tag

        Returns:
            dict: JSON Schema representation of the XML Restrictions/Facets
        """

        # xsd:restriction attributes
        # @id   : Optional. Specifies a unique ID for the element
        # @base : Required. Specifies the name of a built-in data type, simpleType element, or complexType element defined in this schema or another schema
        # @any attributes  : Optional. Specifies any other attributes with non-schema namespace
        type_ = element.attrib.get('base', '').split(':')[-1] or None

        if type_ in self.xsd_data_types:
            # built-in data type
            restriction = self.xsd_data_type_to_json(type_)
        else:
            restriction = {'type': "string"}

        # xsd:restriction content
        # simpleType:     (annotation?,(simpleType?,(minExclusive|minInclusive|maxExclusive|maxInclusive|totalDigits|fractionDigits|length|minLength|maxLength|enumeration|whiteSpace|pattern)*))
        # simpleContent:  (annotation?,(simpleType?,(minExclusive|minInclusive|maxExclusive|maxInclusive|totalDigits|fractionDigits|length|minLength|maxLength|enumeration|whiteSpace|pattern)*)?,((attribute|attributeGroup)*,anyAttribute?))
        # complexContent: (annotation?,(group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?))

        if parent_tag == "simpleType" or parent_tag == "simpleContent":
            enums = []
            for elem in list(element):
                localname = etree.QName(elem.tag).localname
                value = f"{elem.attrib['value']}"

                if localname == "enumeration":
                    enums.append(value)
                elif localname == "length":
                    restriction["minLength"] = int(value)
                    restriction["maxLength"] = int(value)
                elif localname == "maxExclusive":
                    if self.json_schema == "draft-04":
                        restriction["maximum"] = int(value)
                        restriction["exclusiveMaximum"] = True
                    else:
                        restriction["exclusiveMaximum"] = int(value)
                elif localname == "maxInclusive":
                    restriction["maximum"] = int(value)
                elif localname == "maxLength":
                        restriction["maxLength"] = int(value)
                elif localname == "minExclusive":
                    if self.json_schema == "draft-04":
                        restriction["minimum"] = int(value)
                        restriction["exclusiveMinimum"] = True
                    else:
                        restriction["exclusiveMinimum"] = int(value)
                elif localname == "minInclusive":
                    restriction["minimum"] = int(value)
                elif localname == "minLength":
                    restriction["minLength"] = int(value)
                elif localname ==  "pattern":
                    # TODO: id pattern already has "^...$"
                    restriction["pattern"] = f"^{value}$"
                elif localname in ["totalDigits", "fractionDigits", "whiteSpace"]:
                    print(f"    ❌ Restrictions/facets '{localname}' not supported")

            if enums:
                restriction["enum"] = enums

        if parent_tag == "complexContent":
            choice = element.find('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if choice is not None:
                restriction = self.xsd_choice_tp_json(choice)

            sequence = element.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if sequence is not None:
                restriction = self.xsd_sequence_to_json(sequence)

        return restriction


    def xsd_sequence_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML sequence

        Args:
            tree (etree.Element): XML sequence to processed

        Returns:
            dict: JSON Schema representation of sequence
        """

        # xsd:sequence attributes
        # @id        : Optional. Specifies a unique ID for the element
        # @maxOccurs : Optional. Default value is 1
        # @minOccurs : Optional. Default value is 1
        # @any attributes : Optional. Specifies any other attributes with non-schema namespace

        # xsd:sequence content: (annotation?,(element|group|choice|sequence|any)*)
        sequence_schema = {}
        description = {}
        properties = {}
        required = []
        one_of = []

        elements_count = len(tree.xpath('./xsd:element[@name]', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}))
        chouices_count = len(tree.xpath('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}))
        export_choice_as_properties = True if elements_count > 0 else False;

        for element in tree:
            tag = etree.QName(element).localname
            if tag == 'element':
                name = element.attrib.get('name')
                min_occurs = int(element.attrib.get('minOccurs', '1'))

                if not name:
                    continue

                properties[name] = self.xsd_element_to_json(element)
                if min_occurs > 0:
                    required.append(name)

            elif tag == 'choice':
                choice = self.xsd_choice_tp_json(element, export_choice_as_properties)
                if choice.get('properties'):
                    for key, val in choice.get('properties').items():
                        properties[key] = val

                if choice.get('oneOf'):
                    for option in choice.get('oneOf'):
                        one_of.append(option)

            else:
                self.xsd_not_supported(tag)

        sequence_schema = {'type' : "object"}

        if properties:
            sequence_schema['properties'] = properties

        if one_of:
            sequence_schema['oneOf'] = one_of

        if required:
            sequence_schema['required'] = required

        return sequence_schema


    def xsd_simple_content_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML simpleContent

        Args:
            tree (etree.Element): XML sequence to processed

        Returns:
            dict: JSON Schema representation of simpleContent
        """

        # xsd:simpleContent content: (annotation?,(restriction|extension))

        simple_content_schema = {}
        description = {}

        annotation = tree.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = tree.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            simple_content_schema = self.xsd_restriction_to_json(restriction, "simpleContent")

        extension = tree.find('./xsd:extension', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if extension is not None:
            simple_content_schema = self.xsd_extension_to_json(extension)

        return simple_content_schema


    def xsd_simple_type_to_json(self, tree):
        """
        Return the JSON Schema equivalent for the XML Schema simpleType

        Args:
            tree (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation for the XML element
        """

        # xsd:simpleType attributes
        # @id   : Optional. Specifies a unique ID for the element
        # @name : Specifies a name for the element. This attribute is required if the simpleType element is a child of the schema element, otherwise it is not allowed
        # @any attributes: Optional. Specifies any other attributes with non-schema namespace

        # xsd:simpleType content: (annotation?,(restriction|list|union))
        simple_type_schema = {}
        description = {}

        annotation = tree.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = tree.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            simple_type_schema = self.xsd_restriction_to_json(restriction, "simpleType")

        list_ = tree.find('./xsd:list', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if list_ is not None:
            self.xsd_not_supported('list')

        union = tree.find('./xsd:union', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if union is not None:
            self.xsd_not_supported('union')


        if description:
            simple_type_schema.update(description)

        return simple_type_schema



    def validate_json_schema(self, schema_path):
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
        with open(f"./json-schema/{schema_version}.json", "r", encoding="utf-8") as f:
            meta_schema = json.load(f)

        validator = ValidatorClass(meta_schema)
        errors = sorted(validator.iter_errors(schema_to_validate), key=lambda e: e.path)

        if errors:
            print("❌ Errors found in JSON Schema:")
            for err in errors:
                path = ".".join(str(x) for x in err.path) if err.path else "(racine)"
                print(f"- Path '{path}': {err.message}")

        else:
            print("✅ Valid JSON Schema.")


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



# Vars
json_schema_version = ["draft-04", "draft-06", "draft-07", "draft-2019-09", "draft-2020-12"]

# Get XSD Schema from command-line argument
if len(sys.argv) < 2:
    print("usage:", sys.argv[0], "<inputfile>\n")
    sys.exit()
xsd_file_path = sys.argv[1]

# Get Json schema version
print("------------------------------")
for i in range(len(json_schema_version)):
    print( f'{i:4}: {json_schema_version[i]}')
print("------------------------------")

while True:
    try:
        num = int(input("Select JSON schema: "))
        if num < 0 or num >= len(json_schema_version):
            raise ValueError()
    except ValueError:
        print("This is not a valid JSON schema.")
        continue
    else:
        break

xsd = XSDParser(xsd_file_path, json_schema_version[num])

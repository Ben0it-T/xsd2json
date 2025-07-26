# -*- coding: utf-8 -*-

from lxml import etree


class Transformer:

    def __init__(self, json_schema):
        self.json_schema = json_schema
        self.xsd_data_types = [
            'string', 'normalizedString', 'token', 'language', 'Name', 'NCName', 'QName', 'ENTITY', 'ENTITIES', 'ID', 'IDREF', 'IDREFS', 'NMTOKEN', 'NMTOKENS',
            'byte', 'unsignedByte', 'decimal', 'int', 'unsignedInt', 'integer', 'long', 'unsignedLong', 'negativeInteger', 'nonNegativeInteger', 'nonPositiveInteger', 'positiveInteger', 'short', 'unsignedShort',
            'date', 'dateTime', 'time', 'duration', 'gDay', 'gMonth', 'gMonthDay', 'gYear', 'gYearMonth',
            'anyURI', 'base64Binary', 'boolean', 'double', 'float', 'hexBinary', 'NOTATION',
            'anyType', 'anySimpleType'
        ]

    def extract_elements(self, node):
        """
        Extracts top-level elements

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of elements
        """
        elements_defs = {}
        properties = {}
        required = []

        for element in node.xpath('./xsd:element', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
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

    def extract_simple_types(self, node):
        """
        Extracts top-level simpleTypes

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of simpleTypes
        """

        # xsd:simpleType attributes
        # @name : Specifies a name for the element. This attribute is required if the simpleType element is a child of the schema element, otherwise it is not allowed
        # @id   : optionnal
        # any attributes : Optional. Specifies any other attributes with non-schema namespace

        # xsd:simpleType content (annotation?,(restriction|list|union))
        simple_types_defs = {}

        for simple_type in node.xpath('./xsd:simpleType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
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

    def extract_complex_types(self, node):
        """
        Extracts top-level complexTypes

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation of complexTypes
        """

        # xsd:complexType attributes
        # @name : Specifies a name for the element.
        # @id   : Optional. Specifies a unique ID for the element
        # any attributes : Optional. Specifies any other attributes with non-schema namespace

        # xsd:complexType content (annotation?,(simpleContent|complexContent|((group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?))))
        complex_types_defs = {}
        description = {}

        for complex_type in node.xpath('./xsd:complexType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
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
                export_as_properties = False
                attr = complex_type.find('./xsd:attribute', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
                if attr is not None:
                    export_as_properties = True
                complex_types_defs[name] = self.xsd_choice_tp_json(choice, export_as_properties)

            sequence = complex_type.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if sequence is not None:
                complex_types_defs[name] = self.xsd_sequence_to_json(sequence)

            attributes = complex_type.xpath('./xsd:attribute', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if attributes is not None:
                if name not in complex_types_defs:
                    complex_types_defs[name] = {'type': "object", 'properties':{}}

                for attribute in attributes:
                    attribute_def = self.xsd_attribute_to_json(attribute)
                    if attribute_def:
                        complex_types_defs[name]['properties'].update(attribute_def)

            if description:
                complex_types_defs[name].update(description)


            for element in complex_type:
                tag = etree.QName(element).localname
                if tag not in ["annotation", "simpleContent", "complexContent", "choice", "sequence", "attribute"]:
                    self.xsd_not_supported(tag)

        return complex_types_defs


    def xsd_not_supported(self, name):
        """
        Prints message onto the screen

        Args:
            name (str): XML element name
        """
        print(f"    ❌ xsd:{name} not supported")

    def xsd_annotation_to_json(self, node):
        """
        Converts xsd:annotation to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:annotation content (appinfo|documentation)*
        description = ""
        for documentation in node.xpath('./xsd:documentation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}):
            description += ' '.join(documentation.text.split()) + ' '

        return {'description': description.strip()}

    def xsd_data_type_to_json(self, data_type):
        """
        Converts XSD data type to JSON Schema type

        Args:
            data_type (str): Name of the XSD data type (e.g., 'string', 'date', 'positiveInteger', etc.)

        Returns:
            dict: JSON Schema type
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
        elif data_type == "anyType":
            schema = {'type': ["string", "integer", "number", "boolean", "null"]}
        elif data_type == "anySimpleType":
            schema = {'type': ["string", "integer", "number", "boolean", "null"]}


        else:
            schema = {'type': data_type}

        return schema

    def xsd_attribute_to_json(self, node):
        """
        Converts xsd:attribute to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:attribute attributes
        # @name: Optional. Specifies the name of the attribute. Name and ref attributes cannot both be present
        # @type: Optional. Specifies a built-in data type or a simple type. The type attribute can only be present when the content does not contain a simpleType element
        # @use: Optional. Specifies how the attribute is used. Values: optional, prohibited, required
        type_ = node.attrib.get('type', '').split(':')[-1] or None
        name = node.attrib.get('name')
        use = node.attrib.get('use')

        attribute_defs = {}

        if use == "prohibited" or not name:
            return attribute_defs

        if type_ is not None:
            if type_ in self.xsd_data_types:
                # built-in data type
                attribute_defs[name] = self.xsd_data_type_to_json(type_)

            else:
                # simpleType or complexType element
                attribute_defs[name] = {'$ref': f"#/$defs/{type_}"}

        return attribute_defs

    def xsd_choice_tp_json(self, node, export_as_properties = False):
        """
        Converts xsd:choice to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed
            export_as_properties (bool): True to export as properties, False to export as 'oneOf'

        Returns:
            dict: JSON Schema representation
        """

        # xsd:choice attributes
        # @id        : Optional. Specifies a unique ID for the element
        # @maxOccurs : Optional. Specifies the maximum number of times the choice element can occur in the parent element. Default value is 1
        # @minOccurs : Optional. Specifies the minimum number of times the choice element can occur in the parent element. Default value is 1

        # xsd:choice content (annotation?,(element|group|choice|sequence|any)*)
        choice = {}
        properties = {}
        required = []
        options = []
        one_of = []

        for element in node:
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

    def xsd_complex_content_to_json(self, node):
        """
        Converts xsd:complexContent to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:complexContent content (annotation?,(restriction|extension))
        complex_content_schema = {}
        description = {}

        annotation = node.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = node.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            complex_content_schema = self.xsd_restriction_to_json(restriction, "complexContent")

        extension = node.find('./xsd:extension', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if extension is not None:
            complex_content_schema = self.xsd_extension_to_json(extension)

        return complex_content_schema

    def xsd_complex_type_to_json(self, node):
        """
        Converts xsd:complexType to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:complexType attributes
        # @id   :Optional. Specifies a unique ID for the element
        # @name : Optional. Specifies a name for the element
        # @any attributes: Optional. Specifies any other attributes with non-schema namespace

        # xsd:complexType content (annotation?,(simpleContent|complexContent|((group|all|choice|sequence)?,((attribute|attributeGroup)*,anyAttribute?))))
        complex_type_schema = {}
        description = {}

        annotation = node.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        simpleContent = node.find('./xsd:simpleContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if simpleContent is not None:
            complex_type_schema = self.xsd_simple_content_to_json(simpleContent)

        complexContent = node.find('./xsd:complexContent', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if complexContent is not None:
            complex_type_schema = self.xsd_complex_content_to_json(complexContent)

        choice = node.find('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if choice is not None:
            export_as_properties = False
            attr = node.find('./xsd:attribute', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if attr is not None:
                export_as_properties = True
            complex_type_schema = self.xsd_choice_tp_json(choice, export_as_properties)

        sequence = node.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if sequence is not None:
            complex_type_schema = self.xsd_sequence_to_json(sequence)

        attributes = node.xpath('./xsd:attribute', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if attributes is not None:
            if complex_type_schema:
                for attribute in attributes:
                    attribute_def = self.xsd_attribute_to_json(attribute)
                    if attribute_def:
                        complex_type_schema['properties'].update(attribute_def)

        if description:
            complex_type_schema.update(description)

        return complex_type_schema

    def xsd_element_to_json(self, node):
        """
        Converts xsd:element to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:element attributes
        # @name      : Optional. Specifies a name for the element. This attribute is required if the parent element is the schema element
        # @type      : Optional. Specifies either the name of a built-in data type, or the name of a simpleType or complexType element
        # @maxOccurs : Optional. Default value is 1
        # @minOccurs : Optional. Default value is 1
        type_ = node.attrib.get('type', '').split(':')[-1] or None
        min_occurs = int(node.attrib.get('minOccurs', '1'))
        max_occurs = node.attrib.get('maxOccurs', '1')
        max_occurs = int(99999) if max_occurs == "unbounded" else int(max_occurs)

        # xsd:element content (annotation?,(simpleType|complexType)?,(unique|key|keyref)*)
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
            annotation = node.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if annotation is not None:
                description = self.xsd_annotation_to_json(annotation)

            simple_type = node.find('./xsd:simpleType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if simple_type is not None:
                element_schema = self.xsd_simple_type_to_json(simple_type)

            complex_type = node.find('./xsd:complexType', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
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

    def xsd_extension_to_json(self, node):
        """
        Converts xsd:extension to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:extension attributes
        # base: Required. Specifies the name of a built-in data type, a simpleType element, or a complexType element
        base = node.attrib.get('base').split(":")[-1]

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


        for element in node:
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

    def xsd_restriction_to_json(self, node, parent_tag):
        """
        Converts xsd:restriction to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed
            parent_tag (str): parent element tag

        Returns:
            dict: JSON Schema representation
        """

        # xsd:restriction attributes
        # @id   : Optional. Specifies a unique ID for the element
        # @base : Required. Specifies the name of a built-in data type, simpleType element, or complexType element defined in this schema or another schema
        # @any attributes  : Optional. Specifies any other attributes with non-schema namespace
        type_ = node.attrib.get('base', '').split(':')[-1] or None

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
            for elem in list(node):
                localname = etree.QName(elem.tag).localname
                value = f"{elem.attrib['value']}"

                if localname == "enumeration":
                    if type_ in ["integer", "number"]:
                        enums.append(int(value))
                    else:
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
            choice = node.find('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if choice is not None:
                restriction = self.xsd_choice_tp_json(choice)

            sequence = node.find('./xsd:sequence', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
            if sequence is not None:
                restriction = self.xsd_sequence_to_json(sequence)

        return restriction

    def xsd_sequence_to_json(self, node):
        """
        Converts xsd:sequence to JSON Schema equivalent

        Args:
            node (etree.Element): XML sequence to processed

        Returns:
            dict: JSON Schema representation
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

        elements_count = len(node.xpath('./xsd:element[@name]', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}))
        choices_count = len(node.xpath('./xsd:choice', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'}))
        export_choice_as_properties = True if elements_count > 0 else False;

        for element in node:
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

    def xsd_simple_content_to_json(self, node):
        """
        Converts xsd:simpleContent to JSON Schema equivalent

        Args:
            node (etree.Element): XML sequence to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:simpleContent content (annotation?,(restriction|extension))

        simple_content_schema = {}
        description = {}

        annotation = node.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = node.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            simple_content_schema = self.xsd_restriction_to_json(restriction, "simpleContent")

        extension = node.find('./xsd:extension', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if extension is not None:
            simple_content_schema = self.xsd_extension_to_json(extension)

        return simple_content_schema

    def xsd_simple_type_to_json(self, node):
        """
        Converts xsd:simpleType to JSON Schema equivalent

        Args:
            node (etree.Element): XML element to processed

        Returns:
            dict: JSON Schema representation
        """

        # xsd:simpleType attributes
        # @id   : Optional. Specifies a unique ID for the element
        # @name : Specifies a name for the element. This attribute is required if the simpleType element is a child of the schema element, otherwise it is not allowed
        # @any attributes: Optional. Specifies any other attributes with non-schema namespace

        # xsd:simpleType content (annotation?,(restriction|list|union))
        simple_type_schema = {}
        description = {}

        annotation = node.find('./xsd:annotation', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if annotation is not None:
            description = self.xsd_annotation_to_json(annotation)

        restriction = node.find('./xsd:restriction', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if restriction is not None:
            simple_type_schema = self.xsd_restriction_to_json(restriction, "simpleType")

        list_ = node.find('./xsd:list', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if list_ is not None:
            self.xsd_not_supported('list')

        union = node.find('./xsd:union', namespaces={'xsd': 'http://www.w3.org/2001/XMLSchema'})
        if union is not None:
            self.xsd_not_supported('union')


        if description:
            simple_type_schema.update(description)

        return simple_type_schema

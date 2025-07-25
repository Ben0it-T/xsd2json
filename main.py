# -*- coding: utf-8 -*-
import sys
from parser.core import XSDParser

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
    print(f'{i:4}: {json_schema_version[i]}')
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

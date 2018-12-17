import xmltodict
import argparse
import json
parser = argparse.ArgumentParser()
parser.add_argument("in_file", help="Path to in-file (XML)")
parser.add_argument("out_file", help="Path to out-file (JSON)")
args = parser.parse_args()

with open(args.out_file, 'w+') as outfile:
    xml_file = open(args.in_file, 'r').read()
    o = xmltodict.parse(xml_file)
    json.dump(o, outfile, indent=4)

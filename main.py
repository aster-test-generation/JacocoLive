import subprocess
import time
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse
import yaml
from flask import Flask, jsonify

app = Flask(__name__)

# === Args ===
parser = argparse.ArgumentParser(description="Track JaCoCo coverage changes over time")
parser.add_argument('--classfiles', default="/home/rkh/fall2022/api-analysis/services/src/ohsome-api/target/classes", help='Path to .class files')
parser.add_argument('--sourcefiles', default="/home/rkh/fall2022/api-analysis/services/src/ohsome-api/src/main", help='Path to source files')
parser.add_argument('--cli', default='/home/rkh/Downloads/share/lib/jacococli.jar', help='Path to jacococli.jar')
parser.add_argument('--address', default='localhost', help='JaCoCo agent address')
parser.add_argument('--port', default='6300', help='JaCoCo agent port')
parser.add_argument('--output', default='coverage_log.yaml', help='YAML file to write')
# parser.add_argument('--interval', default=10, type=int, help='Interval in seconds between coverage dumps')
parser.add_argument('--host', default='0.0.0.0', help='Flask server host')
parser.add_argument('--flask-port', type=int, default=5000, help='Flask server port')
args = parser.parse_args()

# === Files ===
EXEC_FILE = "jacoco.exec"
XML_FILE = "jacoco_report.xml"

# === State ===
previous_lines_covered = {}
previous_coverage_summary = None

# === Step 1: Trigger dump ===
def dump_coverage():
    # remove old file
    if os.path.exists(EXEC_FILE):
        os.remove(EXEC_FILE)

    subprocess.run([
        "java", "-jar", args.cli, "dump",
        "--address", args.address,
        "--port", args.port,
        "--destfile", EXEC_FILE,
        # "--reset"
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# === Step 2: Generate XML ===
def generate_xml():
    # remove old file
    if os.path.exists(XML_FILE):
        os.remove(XML_FILE)
    subprocess.run([
        "java", "-jar", args.cli, "report", EXEC_FILE,
        "--classfiles", args.classfiles,
        "--xml", XML_FILE
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# === Step 3: Parse XML ===
def parse_coverage_summary(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    summary = dict()
    for counter in root.findall('counter'):
        if counter.get('type') == 'INSTRUCTION':
            missed = int(counter.get('missed'))
            covered = int(counter.get('covered'))
            summary['instruction'] = {
                'missed': missed,
                'covered': covered
            }
        if counter.get('type') == 'LINE':
            missed = int(counter.get('missed'))
            covered = int(counter.get('covered'))
            summary['line'] = {
                'missed': missed,
                'covered': covered
            }
        if counter.get('type') == 'BRANCH':
            missed = int(counter.get('missed'))
            covered = int(counter.get('covered'))
            summary['branch'] = {
                'missed': missed,
                'covered': covered
            }
        if counter.get('type') == 'METHOD':
            missed = int(counter.get('missed'))
            covered = int(counter.get('covered'))
            summary['method'] = {
                'missed': missed,
                'covered': covered
            }
        if counter.get('type') == 'CLASS':
            missed = int(counter.get('missed'))
            covered = int(counter.get('covered'))
            summary['class'] = {
                'missed': missed,
                'covered': covered
            }
    return summary

def parse_covered_lines(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    covered = {}
    for package in root.findall('package'):
        package_name = package.get('name')
        for clazz in package.findall('sourcefile'):
            src = clazz.get('name')
            file_path = f"{package_name}/{src}"
            for line in clazz.findall("line"):
                nr = int(line.get('nr'))
                ci = int(line.get('ci'))
                if ci > 0:
                    covered.setdefault(file_path, set()).add(nr)
    return covered

# === Step 4: Diff ===
def get_newly_covered_lines(current, previous):
    newly_covered = {}
    for file, lines in current.items():
        new_lines = lines - previous.get(file, set())
        if new_lines:
            newly_covered[file] = sorted(new_lines)
    return newly_covered

def diff_summary(curr, prev):
    diff = dict()
    if not prev:
        return diff
    else:
        for key in curr.keys():
            if key not in prev:
                diff[key] = curr[key]
            else:
                if curr[key]['covered'] - prev[key]['covered'] > 0:
                    diff[key] = {
                        'covered': curr[key]['covered'] - prev[key]['covered'],
                        'total': curr[key]['missed'] + curr[key]['covered'],
                        'percent': ((curr[key]['covered'] - prev[key]['covered']) / (curr[key]['missed'] + curr[key]['covered'])) * 100
                    }
        return diff
        


first_run = True

# === Step 5: YAML Write ===
def output_to_yaml_file(entry):
    global first_run

    # data = []
    # if os.path.exists(args.output):
    #     with open(args.output, 'r') as f:
    #         try:
    #             data = yaml.safe_load(f) or []
    #         except Exception:
    #             data = []
    # data.append(entry)
    if first_run:
        open(args.output, 'w').close()
        first_run = False
    
    with open(args.output, 'a') as f:
        yaml.dump([entry], f, sort_keys=False, default_flow_style=False, indent=2)

@app.route('/refresh', methods=['GET'])
def refresh_coverage():
    global previous_coverage_summary, previous_lines_covered

    
    try:
        dump_coverage()
        generate_xml()

        summary = parse_coverage_summary(XML_FILE)
        current_lines = parse_covered_lines(XML_FILE)
        new_lines = get_newly_covered_lines(current_lines, previous_lines_covered)
        diff = diff_summary(summary, previous_coverage_summary)

        yaml_entry = {
            'timestamp': datetime.now().isoformat(),
            'overall_coverage': {
            },
            'coverage_change': diff,
            'newly_covered_lines': new_lines or {},
        }

        if summary:
            if 'instruction' in summary:
                yaml_entry['overall_coverage']['instruction'] = {
                    'covered': summary['instruction']['covered'],
                    'total': summary['instruction']['missed'] + summary['instruction']['covered'],
                    'percent': (summary['instruction']['covered'] / (summary['instruction']['missed'] + summary['instruction']['covered'])) * 100
                }
            if 'line' in summary:
                yaml_entry['overall_coverage']['line'] = {
                    'covered': summary['line']['covered'],
                    'total': summary['line']['missed'] + summary['line']['covered'],
                    'percent': (summary['line']['covered'] / (summary['line']['missed'] + summary['line']['covered'])) * 100
                }
            if 'branch' in summary:
                yaml_entry['overall_coverage']['branch'] = {
                    'covered': summary['branch']['covered'],
                    'total': summary['branch']['missed'] + summary['branch']['covered'],
                    'percent': (summary['branch']['covered'] / (summary['branch']['missed'] + summary['branch']['covered'])) * 100
                }
            if 'method' in summary:
                yaml_entry['overall_coverage']['method'] = {
                    'covered': summary['method']['covered'],
                    'total': summary['method']['missed'] + summary['method']['covered'],
                    'percent': (summary['method']['covered'] / (summary['method']['missed'] + summary['method']['covered'])) * 100
                }
            if 'class' in summary:
                yaml_entry['overall_coverage']['class'] = {
                    'covered': summary['class']['covered'],
                    'total': summary['class']['missed'] + summary['class']['covered'],
                    'percent': (summary['class']['covered'] / (summary['class']['missed'] + summary['class']['covered'])) * 100
                }

        output_to_yaml_file(yaml_entry)
        previous_lines_covered = current_lines
        previous_coverage_summary = summary
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Use /refresh to trigger coverage update.'})

# === Run ===
if __name__ == '__main__':
    print(f"Starting JaCoCo API server on {args.host}:{args.flask_port}")
    app.run(host=args.host, port=args.flask_port)
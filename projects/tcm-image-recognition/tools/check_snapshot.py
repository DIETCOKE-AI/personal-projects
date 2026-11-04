"""Validate the public text snapshot without importing or executing project code."""
from pathlib import Path
import ast
import csv
import ipaddress
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'.git', 'node_modules', '__pycache__', 'venv', 'venv311',
                   'checkpoints', 'ckpts', 'openckpts', 'weights', 'onnx_models',
                   'python-dist', 'uploads', 'release', 'dist'}
FORBIDDEN_EXTENSIONS = {'.pth', '.pt', '.onnx', '.key', '.pem', '.p12', '.pfx',
                        '.zip', '.exe', '.dll', '.jar', '.pyc', '.jpg', '.jpeg',
                        '.png', '.bmp', '.pdf', '.docx', '.xlsx'}


def jsonc_text(text):
    """Remove JSONC comments/trailing commas while respecting quoted strings."""
    out, position, quoted, escaped = [], 0, False, False
    while position < len(text):
        char = text[position]
        if quoted:
            out.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            out.append(char)
        elif text.startswith('//', position):
            end = text.find('\n', position)
            position = len(text) if end < 0 else end
            continue
        elif text.startswith('/*', position):
            end = text.find('*/', position + 2)
            if end < 0:
                raise ValueError('Unclosed JSONC comment')
            out.append('\n' * text[position:end + 2].count('\n'))
            position = end + 2
            continue
        else:
            out.append(char)
        position += 1
    cleaned = ''.join(out)
    out, quoted, escaped = [], False, False
    for position, char in enumerate(cleaned):
        if not quoted and char == ',':
            following = cleaned[position + 1:].lstrip()
            if following.startswith(('}', ']')):
                continue
        out.append(char)
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
    return ''.join(out)


def inspect_snapshot():
    issues = []
    counts = {'files': 0, 'python_ast': 0, 'json': 0, 'jsonc': 0, 'markdown_links': 0}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        name = path.relative_to(ROOT).as_posix()
        counts['files'] += 1
        if any(part in FORBIDDEN_PARTS for part in path.relative_to(ROOT).parts):
            issues.append({'path': name, 'kind': 'excluded-directory'})
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            issues.append({'path': name, 'kind': 'excluded-binary-asset'})
            continue
        if path.name.startswith('.env') and not path.name.endswith('.example'):
            issues.append({'path': name, 'kind': 'non-example-environment-file'})
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            issues.append({'path': name, 'kind': 'non-utf8-text'})
            continue
        try:
            if path.suffix == '.py':
                ast.parse(text, filename=name)
                counts['python_ast'] += 1
            elif path.suffix == '.json':
                is_jsonc = path.name.startswith('tsconfig')
                json.loads(jsonc_text(text) if is_jsonc else text)
                counts['jsonc' if is_jsonc else 'json'] += 1
        except (SyntaxError, ValueError) as error:
            issues.append({'path': name, 'kind': 'parse-error',
                           'line': getattr(error, 'lineno', None)})
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|'
                     r'\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}', text):
            issues.append({'path': name, 'kind': 'credential-token-pattern'})
        # Search content, not filenames. Report only locations, never matched values.
        for line_number, line in enumerate(text.splitlines(), 1):
            if re.search(r'(?i)(?:[a-z]:[\\/](?:Users|项目|workspace|work|Program Files)|'
                         r'/home/[A-Za-z0-9_-]+/|/Users/[A-Za-z0-9_-]+/)', line):
                issues.append({'path': name, 'kind': 'machine-specific-path', 'line': line_number})
            pinned_requirement = path.name.startswith('requirements') and re.fullmatch(
                r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+', line.strip())
            candidates = [] if pinned_requirement else re.findall(
                r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])', line)
            for candidate in candidates:
                try:
                    address = ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if address.is_private and not (address.is_loopback or address.is_unspecified):
                    issues.append({'path': name, 'kind': 'private-ip-pattern', 'line': line_number})
            if re.search(r'''(?i)["']?(?:password|passwd|secret_key|jwt_secret_key|api_key|access_token)["']?\s*[:=]\s*["'][^"'\s]+["']''', line):
                issues.append({'path': name, 'kind': 'literal-credential-review', 'line': line_number})
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', text):
                target = target.strip('<>').split('#', 1)[0]
                if not target or re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I):
                    continue
                counts['markdown_links'] += 1
                if not (path.parent / target).exists():
                    issues.append({'path': name, 'kind': 'broken-relative-link', 'target': target})
    with (ROOT / 'results/evaluation-summary.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 23 or any(row['total_samples'] != '5974' for row in rows):
        issues.append({'path': 'results/evaluation-summary.csv', 'kind': 'unexpected-evaluation-summary'})
    counts['historical_evaluation_records'] = len(rows)
    return {'checks': counts, 'issues': issues, 'project_code_executed': False}


if __name__ == '__main__':
    report = inspect_snapshot()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(bool(report['issues']))

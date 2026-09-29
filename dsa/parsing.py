"""Reading input.txt / expected.txt."""
import ast
import json
import os


def parse_value(text):
    """One line -> value. JSON first (null/true/false), then Python literals, else a bare string."""
    text = text.strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def read_cases(path):
    """input.txt -> list of cases, each a list of non-blank lines. Cases are separated by blank lines.
    A missing or empty file is one case with no arguments."""
    cases, current = [], []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip():
                    current.append(line.strip())
                elif current:
                    cases.append(current)
                    current = []
    if current:
        cases.append(current)
    return cases or [[]]


def read_expected(path):
    """expected.txt -> one parsed value per non-blank line, or None if there is nothing to check."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        values = [parse_value(line) for line in f if line.strip()]
    return values or None

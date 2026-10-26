"""Execute the restricted, explicitly marked numerical subset of our Pine file.

This is not a Pine compiler. It translates only this kernel's scalar expressions,
UDT fields, arrays, if/for blocks and final-value function returns. Thus tests run
the production arithmetic and state transitions instead of a duplicated oracle.
Unsupported constructs fail closed; chart execution and TradingView typing are
not validated here.
"""
from __future__ import annotations

import ast
import builtins
from dataclasses import field, make_dataclass
import math
from pathlib import Path
import re
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "pine" / "fibonacci_memory_v1.pine"


class PineArray(list):
    def size(self):
        return len(self)

    def push(self, value):
        self.append(value)

    def get(self, index):
        return self[index]

    def set(self, index, value):
        self[index] = value


def pine_range(start, end):
    step = 1 if end >= start else -1
    return range(start, end + step, step)


def _top_ternary(expression):
    """Find an outer ternary without splitting strings or grouped expressions."""
    depth = 0
    quote = None
    escaped = False
    question = None
    nested = 0
    for i, char in enumerate(expression):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif depth == 0 and char == "?":
            if question is None:
                question = i
            else:
                nested += 1
        elif depth == 0 and char == ":" and question is not None:
            if nested:
                nested -= 1
            else:
                return question, i
    return None


def _groups(expression):
    """Recursively translate ternaries inside function/array argument groups."""
    out = []
    i = 0
    while i < len(expression):
        char = expression[i]
        if char in ("'", '"'):
            end = i + 1
            while end < len(expression):
                if expression[end] == "\\":
                    end += 2
                elif expression[end] == char:
                    end += 1
                    break
                else:
                    end += 1
            out.append(expression[i:end])
            i = end
        elif char in "([":
            closing = ")" if char == "(" else "]"
            depth = 1
            end = i + 1
            quote = None
            while end < len(expression) and depth:
                token = expression[end]
                if quote:
                    if token == "\\":
                        end += 2
                        continue
                    if token == quote:
                        quote = None
                elif token in ("'", '"'):
                    quote = token
                elif token == char:
                    depth += 1
                elif token == closing:
                    depth -= 1
                end += 1
            if depth:
                raise ValueError("Unclosed expression group")
            out.append(char + _arguments(expression[i + 1:end - 1]) + closing)
            i = end
        else:
            out.append(char)
            i += 1
    return "".join(out)


def _arguments(expression):
    parts = []
    start = 0
    depth = 0
    quote = None
    escaped = False
    for i, char in enumerate(expression):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(_expression(expression[start:i]))
            start = i + 1
    parts.append(_expression(expression[start:]))
    return ", ".join(parts)


def _expression(expression):
    expression = expression.strip()
    match = _top_ternary(expression)
    if match:
        question, colon = match
        condition = _expression(expression[:question])
        yes = _expression(expression[question + 1:colon])
        no = _expression(expression[colon + 1:])
        return f"({yes} if {condition} else {no})"
    expression = _groups(expression)
    expression = re.sub(r"array\.new<\w+>\(\)", "PineArray()", expression)
    expression = expression.replace("array.copy(", "pine_copy(")
    expression = expression.replace("array.from(", "pine_from(")
    expression = re.sub(r"\b(Event|Cohort|Summary)\.new\(", r"\1(", expression)
    expression = re.sub(r"\bna\(", "is_na(", expression)
    expression = re.sub(r"\bna\b", "None", expression)
    expression = re.sub(r"\btrue\b", "True", expression)
    expression = re.sub(r"\bfalse\b", "False", expression)
    return expression


def _function(name, params, lines):
    lines = lines.splitlines()
    names = [part.strip().split()[-1] for part in params.split(",")] if params.strip() else []
    result = [f"def {name}({', '.join(names)}):"]
    usable = [(len(line) - len(line.lstrip()), line.strip()) for line in lines
              if line.strip() and not line.lstrip().startswith("//")]
    for position, (indent, content) in enumerate(usable):
        prefix = " " * indent
        content = re.sub(r"^(?:float|int|bool|string|Event|Cohort|Summary|array<\w+>)\s+", "", content)
        if content.startswith("else if "):
            translated = "elif " + _expression(content[8:]) + ":"
        elif content.startswith("if "):
            translated = "if " + _expression(content[3:]) + ":"
        elif content == "else":
            translated = "else:"
        elif content.startswith("for "):
            counted = re.fullmatch(r"for (\w+) = (.+) to (.+)", content)
            if counted:
                variable, first, last = counted.groups()
                translated = f"for {variable} in pine_range({_expression(first)}, {_expression(last)}):"
            else:
                each = re.fullmatch(r"for (\w+) in (.+)", content)
                if each is None:
                    raise ValueError("Unsupported loop: " + content)
                translated = f"for {each[1]} in {_expression(each[2])}:"
        else:
            assignment = re.fullmatch(r"(\w+(?:\.\w+)*|\[[\w ,]+\])\s*(:=|\+=|-=|=(?!=))\s*(.+)", content)
            if assignment:
                lhs, operator, rhs = assignment.groups()
                operator = "=" if operator == ":=" else operator
                translated = f"{lhs.strip()} {operator} {_expression(rhs)}"
            else:
                translated = _expression(content)
                if position == len(usable) - 1:
                    if indent != 4:
                        raise ValueError("Kernel function must return at base indentation")
                    translated = "return " + translated
        result.append(prefix + translated)
    return "\n".join(result)


def load_kernel():
    source = SOURCE.read_text()
    namespace = {
        "PineArray": PineArray,
        "pine_copy": lambda value: PineArray(value),
        "pine_from": lambda *values: PineArray(values),
        "pine_range": pine_range,
        "is_na": lambda value: value is None or isinstance(value, float) and math.isnan(value),
        "str": SimpleNamespace(tostring=builtins.str),
        "math": SimpleNamespace(abs=abs, min=min, max=max, floor=math.floor,
                                ceil=math.ceil, sqrt=math.sqrt),
    }
    def runtime_error(message):
        raise AssertionError(message)
    namespace["runtime"] = SimpleNamespace(error=runtime_error)
    for name, value in re.findall(r"^const int (\w+) = (\d+)$", source, re.M):
        namespace[name] = int(value)
    for name, body in re.findall(r"^type (\w+)\n((?:    [^\n]+\n)+)", source, re.M):
        fields = []
        for line in body.splitlines():
            match = re.fullmatch(r"    (\w+|array<\w+>) (\w+)(?: = (.+))?", line)
            if match is None:
                raise ValueError("Unsupported UDT field: " + line)
            kind, key, default = match.groups()
            pytype = {"float": float, "int": int, "bool": bool, "string": str}.get(kind, object)
            if default is None:
                fields.append((key, pytype))
            else:
                value = None if default == "na" else ast.literal_eval(default)
                fields.append((key, pytype, field(default=value)))
        namespace[name] = make_dataclass(name, fields)
    kernel = source.split("// BEGIN PORTABLE KERNEL\n", 1)[1].split("// END PORTABLE KERNEL", 1)[0]
    functions = re.findall(r"^(f_\w+)\(([^\n]*)\) =>\n((?:    [^\n]*\n|\n)+)", kernel, re.M)
    if len(functions) != 11:
        raise ValueError(f"Expected 11 production kernel functions, found {len(functions)}")
    self_checks = re.findall(r"^(f_expect|f_fixture|f_self_checks)\(([^\n]*)\) =>\n((?:    [^\n]*\n|\n)+)", source, re.M)
    if len(self_checks) != 3:
        raise ValueError("Expected 3 embedded validation functions")
    functions.extend(self_checks)
    python = "\n\n".join(_function(*function) for function in functions)
    compile(python, str(SOURCE), "exec")
    exec(compile(python, str(SOURCE), "exec"), namespace)
    return SimpleNamespace(**{key: value for key, value in namespace.items() if key.startswith("f_") or key in ("Event", "Cohort", "Summary", "OPEN", "TARGET", "STOP", "TIMEOUT", "AMBIGUOUS")})

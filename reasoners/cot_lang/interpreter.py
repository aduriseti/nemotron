"""cotl (Chain-of-Thought Language) interpreter.

Grammar:
    program      := instruction*
    instruction  := assignment | emit_stmt | answer_stmt | comment | blank
    assignment   := '$' name '=' expr  ('# ' comment)?
    emit_stmt    := 'EMIT' string_literal
    answer_stmt  := 'ANSWER' expr

    expr         := or_expr
    or_expr      := xor_expr ('|' xor_expr)*
    xor_expr     := and_expr ('^' and_expr)*
    and_expr     := eq_expr ('&' eq_expr)*
    eq_expr      := cmp_expr (('==' | '!=') cmp_expr)?
    cmp_expr     := add_expr (('<' | '>') add_expr)?
    add_expr     := mul_expr (('+' | '-') mul_expr)*
    mul_expr     := unary (('*' | '//' | '%') unary)*
    unary        := '~' primary | primary
    primary      := literal | var_index | call | '(' expr ')'
    var_index    := '$' name ('[' expr ']')?
    call         := name '(' (expr (',' expr)*)? ')'
    literal      := INT | STRING | 'true' | 'false'

Value types:
    str   — single char '0'/'1', 8-char bit string, or general string
    int   — integer
    bool  — True/False

Bit ops (&, |, ^, ~) on single '0'/'1' chars return single '0'/'1' chars.
str + str → string concatenation.
"""

from __future__ import annotations

import re
from typing import Union

Value = Union[int, str, bool]

# ── Tokeniser ─────────────────────────────────────────────────────────────────

_TOK = re.compile(
    r"(?P<FLOORDIV>//)"
    r"|(?P<EQ>==)"
    r"|(?P<NEQ>!=)"
    r"|(?P<INT>\d+)"
    r'|(?P<STRING>"(?:[^"\\]|\\.)*")'
    r"|(?P<BOOL>true|false)\b"
    r"|(?P<VAR>\$[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<OP>[+\-*%&|^~<>\[\](),])"
    r"|(?P<WS>\s+)"
    r"|(?P<COMMENT>#.*)"
)


def _tokenise(text: str) -> list[tuple[str, str]]:
    return [
        (m.lastgroup, m.group())
        for m in _TOK.finditer(text)
        if m.lastgroup not in ("WS", "COMMENT")
    ]


# ── Parser ────────────────────────────────────────────────────────────────────


class _P:
    def __init__(self, toks: list[tuple[str, str]]) -> None:
        self._t = toks
        self._i = 0

    def peek(self) -> tuple[str, str] | None:
        return self._t[self._i] if self._i < len(self._t) else None

    def eat(self, kind: str | None = None, val: str | None = None) -> tuple[str, str]:
        tok = self._t[self._i]
        if kind and tok[0] != kind:
            raise SyntaxError(f"expected {kind!r}, got {tok!r}")
        if val and tok[1] != val:
            raise SyntaxError(f"expected {val!r}, got {tok[1]!r}")
        self._i += 1
        return tok

    def done(self) -> bool:
        return self._i >= len(self._t)

    def expr(self) -> tuple:
        return self._or()

    def _or(self) -> tuple:
        n = self._xor()
        while self.peek() and self.peek()[1] == "|":
            self.eat()
            n = ("bin", "|", n, self._xor())
        return n

    def _xor(self) -> tuple:
        n = self._and()
        while self.peek() and self.peek()[1] == "^":
            self.eat()
            n = ("bin", "^", n, self._and())
        return n

    def _and(self) -> tuple:
        n = self._eq()
        while self.peek() and self.peek()[1] == "&":
            self.eat()
            n = ("bin", "&", n, self._eq())
        return n

    def _eq(self) -> tuple:
        n = self._cmp()
        if self.peek() and self.peek()[0] in ("EQ", "NEQ"):
            op = self.eat()[1]
            n = ("bin", op, n, self._cmp())
        return n

    def _cmp(self) -> tuple:
        n = self._add()
        if self.peek() and self.peek()[1] in ("<", ">"):
            op = self.eat()[1]
            n = ("bin", op, n, self._add())
        return n

    def _add(self) -> tuple:
        n = self._mul()
        while self.peek() and self.peek()[1] in ("+", "-"):
            op = self.eat()[1]
            n = ("bin", op, n, self._mul())
        return n

    def _mul(self) -> tuple:
        n = self._unary()
        while self.peek() and (
            self.peek()[1] in ("*", "%") or self.peek()[0] == "FLOORDIV"
        ):
            op = self.eat()[1]
            n = ("bin", op, n, self._unary())
        return n

    def _unary(self) -> tuple:
        if self.peek() and self.peek()[1] == "~":
            self.eat()
            return ("unary", "~", self._primary())
        return self._primary()

    def _primary(self) -> tuple:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("unexpected end of expression")
        kind, val = tok

        if kind == "INT":
            self.eat()
            return ("lit", int(val))

        if kind == "STRING":
            self.eat()
            return ("lit", val[1:-1].replace('\\"', '"').replace("\\\\", "\\"))

        if kind == "BOOL":
            self.eat()
            return ("lit", val == "true")

        if kind == "VAR":
            self.eat()
            name = val[1:]
            if self.peek() and self.peek()[1] == "[":
                self.eat()
                idx = self.expr()
                self.eat(val="]")
                return ("idx", name, idx)
            return ("var", name)

        if kind == "IDENT":
            self.eat()
            if self.peek() and self.peek()[1] == "(":
                self.eat()
                args: list[tuple] = []
                if self.peek() and self.peek()[1] != ")":
                    args.append(self.expr())
                    while self.peek() and self.peek()[1] == ",":
                        self.eat()
                        args.append(self.expr())
                self.eat(val=")")
                return ("call", val, args)
            raise SyntaxError(f"bare identifier: {val!r}")

        if kind == "OP" and val == "(":
            self.eat()
            n = self.expr()
            self.eat(val=")")
            return n

        raise SyntaxError(f"unexpected token: {tok!r}")


# ── Evaluator ─────────────────────────────────────────────────────────────────


def _ev(node: tuple, regs: dict[str, Value]) -> Value:
    k = node[0]

    if k == "lit":
        return node[1]

    if k == "var":
        name = node[1]
        if name not in regs:
            raise NameError(f"undefined variable: ${name}")
        return regs[name]

    if k == "idx":
        seq = regs[node[1]]
        i = _ev(node[2], regs)
        if isinstance(i, bool):
            i = int(i)
        if isinstance(i, str):
            i = int(i)
        return seq[i]  # type: ignore[index]

    if k == "unary":
        v = _ev(node[2], regs)
        if node[1] == "~":
            if v == "0":
                return "1"
            if v == "1":
                return "0"
            if isinstance(v, str) and len(v) == 8:
                return "".join("1" if c == "0" else "0" for c in v)
            if isinstance(v, int):
                return (~v) & 0xFF
        raise ValueError(f"unknown unary op {node[1]!r} on {v!r}")

    if k == "bin":
        op = node[1]
        lv = _ev(node[2], regs)
        rv = _ev(node[3], regs)

        # bit ops on single '0'/'1' chars
        if (
            op in ("&", "|", "^")
            and isinstance(lv, str)
            and isinstance(rv, str)
            and len(lv) == 1
            and len(rv) == 1
        ):
            lb, rb = int(lv), int(rv)
            if op == "&":
                return str(lb & rb)
            if op == "|":
                return str(lb | rb)
            if op == "^":
                return str(lb ^ rb)

        if op == "+":
            if isinstance(lv, str) and isinstance(rv, str):
                return lv + rv
            return lv + rv  # type: ignore[operator]
        if op == "-":
            return lv - rv  # type: ignore[operator]
        if op == "*":
            return lv * rv  # type: ignore[operator]
        if op == "//":
            return lv // rv  # type: ignore[operator]
        if op == "%":
            return lv % rv  # type: ignore[operator]
        if op == "==":
            return lv == rv
        if op == "!=":
            return lv != rv
        if op == "<":
            return lv < rv  # type: ignore[operator]
        if op == ">":
            return lv > rv  # type: ignore[operator]
        if op == "&":
            return lv & rv  # type: ignore[operator]
        if op == "|":
            return lv | rv  # type: ignore[operator]
        if op == "^":
            return lv ^ rv  # type: ignore[operator]
        raise ValueError(f"unknown operator: {op!r}")

    if k == "call":
        name, raw_args = node[1], node[2]
        args = [_ev(a, regs) for a in raw_args]

        if name == "ROT":
            s, k2 = args[0], int(args[1])
            return "".join(s[(i + k2) % 8] for i in range(8))  # type: ignore[index]

        if name == "SHL":
            s, k2 = args[0], int(args[1])
            return "".join(
                s[i + k2] if i + k2 < 8 else "0"
                for i in range(8)  # type: ignore[index]
            )

        if name == "SHR":
            s, k2 = args[0], int(args[1])
            return "".join(
                s[i - k2] if i - k2 >= 0 else "0"
                for i in range(8)  # type: ignore[index]
            )

        if name == "REVERSE":
            return args[0][::-1]  # type: ignore[index]

        if name == "EXTRACT":
            m = re.search(str(args[1]), str(args[0]))
            if m:
                return m.group(1) if m.lastindex else m.group(0)
            return ""

        if name == "INT":
            v = args[0]
            if isinstance(v, bool):
                return int(v)
            if isinstance(v, str):
                return int(v)
            return int(v)  # type: ignore[arg-type]

        if name == "CONCAT":
            return "".join(str(a) for a in args)

        raise NameError(f"unknown function: {name!r}")

    raise ValueError(f"unknown AST node: {node!r}")


# ── Interpreter ───────────────────────────────────────────────────────────────

_ASSIGN_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")


def _strip_inline_comment(line: str) -> str:
    in_str = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_str = not in_str
        elif ch == "#" and not in_str:
            return line[:i].rstrip()
    return line


def _repr(val: Value) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        return f'"{val}"'
    return str(val)


class Interpreter:
    def run(self, source: str) -> tuple[str, list[str]]:
        """Execute a cotl program.

        Returns (answer, trace) where trace is the executed lines with
        computed results interleaved as comments.
        """
        regs: dict[str, Value] = {}
        trace: list[str] = []
        answer: str | None = None

        for raw in source.splitlines():
            line = raw.strip()

            if not line or line.startswith("#"):
                trace.append(raw)
                continue

            expr_part = _strip_inline_comment(line)
            upper = expr_part.upper()

            if upper.startswith("ANSWER"):
                val_txt = expr_part[6:].strip()
                toks = _tokenise(val_txt)
                val = _ev(_P(toks).expr(), regs)
                answer = str(val)
                trace.append(f"ANSWER {val_txt}  # {_repr(val)}")
                break

            if upper.startswith("EMIT"):
                msg = expr_part[4:].strip().strip('"')

                def _sub(m: re.Match) -> str:
                    return str(regs.get(m.group(1), f"${m.group(1)}"))

                trace.append('EMIT "' + re.sub(r"\{\$(\w+)\}", _sub, msg) + '"')
                continue

            m = _ASSIGN_RE.match(expr_part)
            if m:
                vname, expr_txt = m.group(1), m.group(2).strip()
                toks = _tokenise(expr_txt)
                val = _ev(_P(toks).expr(), regs)
                regs[vname] = val
                trace.append(f"${vname} = {expr_txt}  # {_repr(val)}")
                continue

            raise SyntaxError(f"cannot parse line: {line!r}")

        return (answer or ""), trace

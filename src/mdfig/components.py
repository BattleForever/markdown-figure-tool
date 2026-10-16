"""Compile exported JSX-like layout syntax, keeping expressions as JavaScript."""
import re


COMPONENT_TAGS = r'box|row|grid|grid-item|badge|icon|divider|radio-group|radio|list|list-item|WritingBlock|AppBlock|button'


def brace_end(source, start):
    """Return the end of one balanced {...}, respecting JS strings/comments."""
    depth = 0
    quote = None
    comment = None
    index = start
    while index < len(source):
        char = source[index]
        following = source[index:index + 2]
        if comment:
            if comment == 'line' and char == '\n':
                comment = None
            elif comment == 'block' and following == '*/':
                comment = None
                index += 1
        elif quote:
            if char == '\\':
                index += 1
            elif char == quote:
                quote = None
        elif following in {'//', '/*'}:
            comment = 'line' if following == '//' else 'block'
            index += 1
        elif char in "\"'`":
            quote = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise ValueError('组件中的 JavaScript 花括号未闭合。')


def body_directives(source):
    position = 0
    while match := re.search(r'\{@body\b', source[position:]):
        start = position + match.start()
        end = brace_end(source, start)
        yield start, end, source[start + len('{@body'):end - 1].strip()
        position = end


def uses_components(source):
    if re.search(r'<script\b', source, re.I):
        return False  # Original DOM scripts continue through the native HTML path.
    return bool(re.search(r'<(?:' + COMPONENT_TAGS + r')\b|\{[#@]|\w+=\{', source, re.I))


def compile_component(source):
    """Lower body/each/if directives to JSX, then let Babel parse JS precisely."""
    if len(source) > 250000:
        raise ValueError('组件代码过长，超过本地编译上限。')
    declarations = []
    for start, end, code in reversed(list(body_directives(source))):
        declarations.insert(0, code)
        source = source[:start] + source[end:]
    # These names are layout components rather than missing global JS variables.
    names = {'WritingBlock': 'writing-block', 'AppBlock': 'app-block', 'Cite': 'mdfig-cite', 'MemoryCite': 'mdfig-memory-cite'}
    for old, new in names.items():
        source = re.sub(r'(<\/?)' + old + r'\b', lambda m: m[1] + new, source)
    position = 0
    parts = []
    stack = []
    directive = re.compile(r'\{(?:#each\b|/each\s*\}|#if\b|:else(?:\s+if\b)?|/if\s*\})')
    while match := directive.search(source, position):
        start = match.start()
        end = brace_end(source, start)
        code = source[start + 1:end - 1].strip()
        parts.append(source[position:start])
        if code.startswith('#each '):
            expression, separator, binding = code[6:].rpartition(' as ')
            if not separator or not re.fullmatch(r'\s*\w+(?:\s*,\s*\w+)?\s*', binding):
                raise ValueError('不支持的 each 语法，应为 {#each expression as item}。')
            parts.append('{(' + expression + ').map((' + binding + ')=>(<>')
            stack.append('each')
        elif code == '/each':
            if not stack or stack.pop() != 'each':
                raise ValueError('each 标签未配对。')
            parts.append('</>))}')
        elif code.startswith('#if '):
            parts.append('{(' + code[4:] + ')?(<>')
            stack.append('if')
        elif code.startswith(':else'):
            if not stack or stack[-1] != 'if':
                raise ValueError('else 前没有 if。')
            if code.startswith(':else if '):
                # Nested ternaries share the closing fragment below.
                parts.append('</>):(' + code[9:] + ')?(<>')
            else:
                parts.append('</>):(<>')
                stack[-1] = 'if-else'
        elif code == '/if':
            if not stack or stack[-1] not in {'if', 'if-else'}:
                raise ValueError('if 标签未配对。')
            kind = stack.pop()
            parts.append('</>):null}' if kind == 'if' else '</>)}')
        position = end
    parts.append(source[position:])
    if stack:
        raise ValueError('组件循环或条件标签未闭合。')
    source = ''.join(parts)
    # Exporters sometimes write numeric shorthand, which is HTML but not JSX.
    source = re.sub(r'(\s[\w-]+)=(-?\d+(?:\.\d+)?)(?=\s|/?>)', r'\1={\2}', source)
    return 'function MdfigComponent(){\n' + ';\n'.join(declarations) + ';\nreturn (<>' + source + '</>);\n}\npreact.render(DIL.h(MdfigComponent,{}),document.getElementById("mdfig-capture"));'

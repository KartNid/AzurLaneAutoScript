"""Apply reviewed, guarded changes to an upstream module's in-memory AST."""
import ast
import hashlib
import json


class CompatibilityError(ImportError):
    pass


def canonical(value):
    # Keep fingerprints stable between the supported Python 3.7+ runtimes.
    if isinstance(value, ast.AST):
        kind = type(value).__name__
        if kind in ('Constant', 'Num', 'Str', 'Bytes', 'NameConstant', 'Ellipsis'):
            literal = getattr(value, 'value', getattr(value, 'n', getattr(value, 's', None)))
            if kind == 'Ellipsis' or literal is Ellipsis:
                return ['literal', 'Ellipsis']
            if isinstance(literal, bytes):
                return ['literal', 'bytes', literal.hex()]
            return ['literal', type(literal).__name__, literal]
        if kind == 'Index':
            return canonical(value.value)
        fields = []
        for name, field in ast.iter_fields(value):
            if name in ('type_comment', 'type_ignores', 'type_params', 'posonlyargs', 'kind') and not field:
                continue
            fields.append([name, canonical(field)])
        return [kind, fields]
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    return value


def fingerprint(value):
    encoded = json.dumps(canonical(value), sort_keys=True, ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def keyed(body):
    counts = {}
    result = []
    for node in body:
        if isinstance(node, ast.ClassDef):
            key = 'class:' + node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            key = 'function:' + node.name
        elif isinstance(node, ast.Assign):
            key = 'assign:' + fingerprint(node.targets)
        elif isinstance(node, ast.AnnAssign):
            key = 'annotation:' + fingerprint(node.target)
        else:
            key = 'statement:' + fingerprint(node)
        index = counts.get(key, 0)
        counts[key] = index + 1
        result.append((key + ':' + str(index), node))
    return result


def _parent(tree, path):
    parent = tree
    for key in path:
        matches = dict(keyed(parent.body))
        if key not in matches or not isinstance(matches[key], ast.ClassDef):
            raise CompatibilityError('Upstream class changed: ' + '.'.join(path))
        parent = matches[key]
    return parent


def transform(source, operations, filename='<upstream>'):
    tree = ast.parse(source, filename=filename)
    for operation in operations:
        path = operation['path']
        parent = _parent(tree, path[:-1])
        nodes = dict(keyed(parent.body))
        key = path[-1]
        node = nodes.get(key)
        action = operation['action']
        description = filename + ':' + '.'.join(path)
        if action == 'add':
            if node is not None:
                raise CompatibilityError('Upstream already defines plugin member: ' + description)
            replacement = ast.parse(operation['source']).body[0]
            anchor = operation.get('after')
            if anchor is None:
                index = 0
            else:
                if anchor not in nodes:
                    raise CompatibilityError('Upstream insertion point changed: ' + description)
                index = parent.body.index(nodes[anchor]) + 1
            ast.increment_lineno(replacement, max(getattr(parent, 'lineno', 1) - 1, 0))
            parent.body.insert(index, replacement)
        elif action == 'header':
            if node is None or fingerprint([node.bases, node.keywords, node.decorator_list]) != operation['before']:
                raise CompatibilityError('Upstream class signature changed: ' + description)
            header = ast.parse(operation['source']).body[0]
            node.bases, node.keywords, node.decorator_list = header.bases, header.keywords, header.decorator_list
        elif action == 'replace':
            if node is None or fingerprint(node) != operation['before']:
                raise CompatibilityError('Upstream method changed; update the 1440P plugin: ' + description)
            replacement = ast.parse(operation['source']).body[0]
            first_line = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
            ast.increment_lineno(replacement, first_line - 1)
            parent.body[parent.body.index(node)] = replacement
        else:
            raise CompatibilityError('Unknown plugin operation: ' + action)
    return ast.fix_missing_locations(tree)

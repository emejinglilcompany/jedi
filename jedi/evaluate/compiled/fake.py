"""
Loads functions that are mixed in to the standard library. E.g. builtins are
written in C (binaries), but my autocompletion only understands Python code. By
mixing in Python code, the autocompletion should work much better for builtins.
"""

import os
from itertools import chain

from jedi._compatibility import is_py3, unicode

fake_modules = {}


def _get_path_dict():
    path = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(path, 'fake')
    dct = {}
    for file_name in os.listdir(base_path):
        if file_name.endswith('.pym'):
            dct[file_name[:-4]] = os.path.join(base_path, file_name)
    return dct


_path_dict = _get_path_dict()


class FakeDoesNotExist(Exception):
    pass


def _load_faked_module(grammar, module_name):
    if module_name == '__builtin__' and not is_py3:
        module_name = 'builtins'

    try:
        return fake_modules[module_name]
    except KeyError:
        pass

    try:
        path = _path_dict[module_name]
    except KeyError:
        fake_modules[module_name] = None
        return

    with open(path) as f:
        source = f.read()

    fake_modules[module_name] = m = grammar.parse(unicode(source))

    if module_name == 'builtins' and not is_py3:
        # There are two implementations of `open` for either python 2/3.
        # -> Rename the python2 version (`look at fake/builtins.pym`).
        open_func = _search_scope(m, 'open')
        open_func.children[1].value = 'open_python3'
        open_func = _search_scope(m, 'open_python2')
        open_func.children[1].value = 'open'
    return m


def _search_scope(scope, obj_name):
    for s in chain(scope.iter_classdefs(), scope.iter_funcdefs()):
        if s.name.value == obj_name:
            return s


def get_faked_with_parent_context(parent_context, name):
    if parent_context.tree_node is not None:
        # Try to search in already clearly defined stuff.
        found = _search_scope(parent_context.tree_node, name)
        if found is not None:
            return found
    raise FakeDoesNotExist


def get_faked_module(grammar, string_name):
    module = _load_faked_module(grammar, string_name)
    if module is None:
        raise FakeDoesNotExist
    return module


def get_faked_tree_nodes(grammar, string_names):
    module = base = get_faked_module(grammar, string_names[0])

    tree_nodes = [module]
    for name in string_names[1:]:
        base = _search_scope(base, name)
        if base is None:
            raise FakeDoesNotExist
        tree_nodes.append(base)
    return tree_nodes

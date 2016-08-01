"""
This is the module responsible for automatically generating an HTML index of
all documentation files generated by Pycco.
"""
import re
from os import path

from pycco.compat import compat_items
from pycco_resources import pycco_template


__all__ = ('generate_index',)


def build_tree(file_paths, outdir):
    tree = {}
    for file_path in file_paths:
        entry = {
            'path': file_path,
            'relpath': path.relpath(file_path, outdir)
        }
        path_steps = entry['relpath'].split(path.sep)
        add_file(entry, path_steps, tree)

    return tree


def add_file(entry, path_steps, tree):
    """
    :param entry: A dictionary containing a path to a documentation file, and a
    relative path to the same file.
    :param path_steps: A list of steps in a file path to look within.
    """
    node, subpath = path_steps[0], path_steps[1:]
    if node not in tree:
        tree[node] = {}

    if subpath:
        add_file(entry, subpath, tree[node])

    else:
        tree[node]['entry'] = entry


def generate_tree_html(tree):
    """
    Given a tree representing HTML file paths, return an HTML table plotting
    those paths.
    """
    items = []
    for node, subtree in sorted(compat_items(tree)):
        if 'entry' in subtree:
            node_text = node
            node_parts = node_text.split('.')
            if len(node_parts) == 3 and node_parts[-1] == 'html':
                node_text = '.'.join(node_parts)
            html = u'<li><a href="{}">{}</a></li>'.format(subtree['entry']['relpath'], node_text)
        else:
            html = u'<dl><dt>{}</dt><dd><ul>{}</ul></dd></dl>'.format(node, generate_tree_html(subtree))

        items.append(html)

    return ''.join(items)


def generate_index(files, outdir):
    """
    Given a list of generated documentation files, generate HTML to display
    index of all files.
    """
    tree = build_tree(files, outdir)

    rendered = pycco_template({
        "title": 'Index',
        "stylesheet": 'pycco.css',
        "sections": {'docs_html': generate_tree_html(tree)},
        "source": '',
    })

    return re.sub(r"__DOUBLE_OPEN_STACHE__", "{{", rendered).encode("utf-8")

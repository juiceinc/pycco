#!/usr/bin/env python
from __future__ import print_function

# This module contains all of our static resources.
from pycco_resources import pycco_template, css as pycco_css

"""
"**Pycco**" is a Python port of [Docco](http://jashkenas.github.com/docco/):
the original quick-and-dirty, hundred-line-long, literate-programming-style
documentation generator. It produces HTML that displays your comments
alongside your code. Comments are passed through
[Markdown](http://daringfireball.net/projects/markdown/syntax) and
[SmartyPants](http://daringfireball.net/projects/smartypants), while code is
passed through [Pygments](http://pygments.org/) for syntax highlighting.
This page is the result of running Pycco against its own source file.

If you install Pycco, you can run it from the command-line:

    pycco src/*.py

This will generate linked HTML documentation for the named source files,
saving it into a `docs` folder by default.

The [source for Pycco](https://github.com/pycco-docs/pycco) is available on GitHub,
and released under the MIT license.

To install Pycco, simply

    pip install pycco

Or, to install the latest source

    git clone git://github.com/pycco-docs/pycco.git
    cd pycco
    python setup.py install
"""

# === Main Documentation Generation Functions ===


def generate_documentation(source, outdir=None, preserve_paths=True,
                           language=None, encoding="utf8"):
    """
    Generate the documentation for a source file by reading it in, splitting it
    up into comment/code sections, highlighting them for the appropriate
    language, and merging them into an HTML template.
    """

    if not outdir:
        raise TypeError("Missing the required 'outdir' keyword argument.")
    code = open(source, "rb").read().decode(encoding)
    return _generate_documentation(source, code, outdir, preserve_paths, language)


def prehighlight(sections, language, preserve_paths, outdir):
    newsections = []
    for section in sections:
        match = re.match('^class (\w*Service)\(.*', section.code_text)
        if match:
            newsections.append({
                "docs_text": "=== {} ===".format(match.groups()[0]),
                "code_text": ""
            })
        newsections.append(section)
    sections = newsections

def _generate_documentation(file_path, code, outdir, preserve_paths, language):
    """
    Helper function to allow documentation generation without file handling.
    """
    language = get_language(file_path, code, language=language)
    sections = parse(code, language)
    prehighlight(sections, language, preserve_paths=preserve_paths, outdir=outdir)
    highlight(sections, language, preserve_paths=preserve_paths, outdir=outdir)
    return generate_html(file_path, sections, preserve_paths=preserve_paths, outdir=outdir)


def parse(code, language):
    """
    Given a string of source code, parse out each comment and the code that
    follows it, and create an individual **section** for it.
    Sections take the form:

        { "docs_text": ...,
          "docs_html": ...,
          "code_text": ...,
          "code_html": ...,
          "num":       ...
        }
    """

    lines = code.split("\n")
    sections = []
    has_code = docs_text = code_text = ""

    if lines[0].startswith("#!"):
        lines.pop(0)

    if language["name"] == "python":
        for linenum, line in enumerate(lines[:2]):
            if re.search(r'coding[:=]\s*([-\w.]+)', lines[linenum]):
                lines.pop(linenum)
                break

    def save(docs, code):
        if docs or code:
            sections.append({
                "docs_text": docs,
                "code_text": code
            })

    # Setup the variables to get ready to check for multiline comments
    multi_line = False
    multi_string = False
    multistart, multiend = language.get("multistart"), language.get("multiend")
    comment_matcher = language['comment_matcher']

    for line in lines:
        process_as_code = False
        # Only go into multiline comments section when one of the delimiters is
        # found to be at the start of a line
        if multistart and multiend \
           and any(line.lstrip().startswith(delim) or line.rstrip().endswith(delim)
                   for delim in (multistart, multiend)):
            multi_line = not multi_line

            if multi_line \
               and line.strip().endswith(multiend) \
               and len(line.strip()) > len(multiend):
                multi_line = False

            if not line.strip().startswith(multistart) and not multi_line \
               or multi_string:

                process_as_code = True

                if multi_string:
                    multi_line = False
                    multi_string = False
                else:
                    multi_string = True

            else:
                # Get rid of the delimiters so that they aren't in the final
                # docs
                line = line.replace(multistart, '')
                line = line.replace(multiend, '')
                docs_text += line.strip() + '\n'
                indent_level = re.match("\s*", line).group(0)

                if has_code and docs_text.strip():
                    save(docs_text, code_text[:-1])
                    code_text = code_text.split('\n')[-1]
                    has_code = docs_text = ''

        elif multi_line:
            # Remove leading spaces
            if re.match(r' {{{:d}}}'.format(len(indent_level)), line):
                docs_text += line[len(indent_level):] + '\n'
            else:
                docs_text += line + '\n'

        elif re.match(comment_matcher, line):
            if has_code:
                save(docs_text, code_text)
                has_code = docs_text = code_text = ''
            docs_text += re.sub(comment_matcher, "", line) + "\n"

        else:
            process_as_code = True

        if process_as_code:
            if code_text and any(line.lstrip().startswith(x)
                                 for x in ['class ', 'def ', '@']):
                if not code_text.lstrip().startswith("@"):
                    save(docs_text, code_text)
                    code_text = has_code = docs_text = ''

            has_code = True
            code_text += line + '\n'

    save(docs_text, code_text)

    return sections

# === Preprocessing the comments ===


def preprocess(comment, preserve_paths=True, outdir=None):
    """
    Add cross-references before having the text processed by markdown.  It's
    possible to reference another file, like this : `[[main.py]]` which renders
    [[main.py]]. You can also reference a specific section of another file, like
    this: `[[main.py#highlighting-the-source-code]]` which renders as
    [[main.py#highlighting-the-source-code]]. Sections have to be manually
    declared; they are written on a single line, and surrounded by equals signs:
    `=== like this ===`
    """

    if not outdir:
        raise TypeError("Missing the required 'outdir' keyword argument.")

    def sanitize_section_name(name):
        return "-".join(name.lower().strip().split(" "))

    def replace_crossref(match):
        # Check if the match contains an anchor
        if '#' in match.group(1):
            name, anchor = match.group(1).split('#')
            return " [{}]({}#{})".format(name,
                                         path.basename(destination(name,
                                                                   preserve_paths=preserve_paths,
                                                                   outdir=outdir)),
                                         anchor)

        else:
            return " [{}]({})".format(match.group(1),
                                      path.basename(destination(match.group(1),
                                                                preserve_paths=preserve_paths,
                                                                outdir=outdir)))

    def replace_section_name(match):
        """
        Replace equals-sign-formatted section names with anchor links.
        """
        return '{lvl} <span id="{id}" href="{id}">{name}</span>'.format(
            lvl=re.sub('=', '#', match.group(1)),
            id=sanitize_section_name(match.group(2)),
            name=match.group(2)
        )

    comment = re.sub('^([=]+)([^=]+)[=]*\s*$', replace_section_name, comment)
    comment = re.sub('(?<!`)\[\[(.+?)\]\]', replace_crossref, comment)

    return comment

# === Highlighting the source code ===

def highlight(sections, language, preserve_paths=True, outdir=None):
    """
    Highlights a single chunk of code using the **Pygments** module, and runs
    the text of its corresponding comment through **Markdown**.

    We process the entire file in a single call to Pygments by inserting little
    marker comments between each section and then splitting the result string
    wherever our markers occur.
    """

    if not outdir:
        raise TypeError("Missing the required 'outdir' keyword argument.")

    output = pygments.highlight(language["divider_text"].join(section["code_text"].rstrip() for section in sections),
                                language["lexer"],
                                formatters.get_formatter_by_name("html"))

    output = output.replace(highlight_start, "").replace(highlight_end, "")
    fragments = re.split(language["divider_html"], output)
    for i, section in enumerate(sections):
        section["code_html"] = highlight_start + \
            shift(fragments, "") + highlight_end
        try:
            docs_text = unicode(section["docs_text"])
        except UnicodeError:
            docs_text = unicode(section["docs_text"].decode('utf-8'))
        except NameError:
            docs_text = section['docs_text']
        section["docs_html"] = markdown(preprocess(docs_text,
                                                   preserve_paths=preserve_paths,
                                                   outdir=outdir))
        section["num"] = i

    return sections

# === HTML Code generation ===


def generate_html(source, sections, preserve_paths=True, outdir=None):
    """
    Once all of the code is finished highlighting, we can generate the HTML file
    and write out the documentation. Pass the completed sections into the
    template found in `resources/pycco.html`.

    Pystache will attempt to recursively render context variables, so we must
    replace any occurences of `{{`, which is valid in some languages, with a
    "unique enough" identifier before rendering, and then post-process the
    rendered template and change the identifier back to `{{`.
    """

    if not outdir:
        raise TypeError("Missing the required 'outdir' keyword argument")
    title = path.basename(source)
    dest = destination(source, preserve_paths=preserve_paths, outdir=outdir)
    csspath = path.relpath(path.join(outdir, "pycco.css"), path.split(dest)[0])

    for sect in sections:
        sect["code_html"] = re.sub(
            r"\{\{", r"__DOUBLE_OPEN_STACHE__", sect["code_html"])

    rendered = pycco_template({
        "title": title,
        "stylesheet": csspath,
        "sections": sections,
        "source": source,
    })

    return re.sub(r"__DOUBLE_OPEN_STACHE__", "{{", rendered).encode("utf-8")

# === Helpers & Setup ===

# Import our external dependencies.
import optparse
import os
import pygments
import re
import sys
import time
import pycco.generate_index as generate_index

from markdown import markdown
from os import path
from pygments import lexers, formatters

# A list of the languages that Pycco supports, mapping the file extension to
# the name of the Pygments lexer and the symbol that indicates a comment. To
# add another language to Pycco's repertoire, add it here.
languages = {
    ".coffee": {"name": "coffee-script", "symbol": "#",
                "multistart": '###', "multiend": '###'},

    ".pl":  {"name": "perl", "symbol": "#"},

    ".sql": {"name": "sql", "symbol": "--"},

    ".sh": {"name": "bash", "symbol": "#"},

    ".c":   {"name": "c", "symbol": "//",
             "multistart": "/*", "multiend": "*/"},

    ".h":   {"name": "c", "symbol": "//",
             "multistart": "/*", "multiend": "*/"},

    ".cpp": {"name": "cpp", "symbol": "//"},

    ".cl":   {"name": "c", "symbol": "//",
              "multistart": "/*", "multiend": "*/"},

    ".js": {"name": "javascript", "symbol": "//",
            "multistart": "/*", "multiend": "*/"},

    ".rb": {"name": "ruby", "symbol": "#",
            "multistart": "=begin", "multiend": "=end"},

    ".py": {"name": "python", "symbol": "#",
            "multistart": '"""', "multiend": '"""'},

    ".scm": {"name": "scheme", "symbol": ";;",
             "multistart": "#|", "multiend": "|#"},

    ".lua": {"name": "lua", "symbol": "--",
             "multistart": "--[[", "multiend": "--]]"},

    ".erl": {"name": "erlang", "symbol": "%%"},

    ".tcl":  {"name": "tcl", "symbol": "#"},

    ".hs": {"name": "haskell", "symbol": "--",
            "multistart": "{-", "multiend": "-}"},

    ".yaml": {"name": "yaml", "symbol": "#"},

    ".yml": {"name": "yaml", "symbol": "#"},
}

# Build out the appropriate matchers and delimiters for each language.
for ext, l in languages.items():
    # Does the line begin with a comment?
    l["comment_matcher"] = re.compile(r"^\s*" + l["symbol"] + "\s?")

    # The dividing token we feed into Pygments, to delimit the boundaries between
    # sections.
    l["divider_text"] = "\n" + l["symbol"] + "DIVIDER\n"

    # The mirror of `divider_text` that we expect Pygments to return. We can split
    # on this to recover the original sections.
    l["divider_html"] = re.compile(
        r'\n*<span class="c[1]?">' + l["symbol"] + 'DIVIDER</span>\n*')

    # Get the Pygments Lexer for this language.
    l["lexer"] = lexers.get_lexer_by_name(l["name"])


def get_language(source, code, language=None):
    """Get the current language we're documenting, based on the extension."""

    if language is not None:
        for l in languages.values():
            if l["name"] == language:
                return l
        else:
            raise ValueError("Unknown forced language: " + language)

    m = re.match(r'.*(\..+)', os.path.basename(source)) if source else None
    if m and m.group(1) in languages:
        return languages[m.group(1)]
    else:
        try:
            lang = lexers.guess_lexer(code).name.lower()
            for l in languages.values():
                if l["name"] == lang:
                    return l
            else:
                raise ValueError()
        except ValueError:
            # If pygments can't find any lexers, it will raise its own
            # subclass of ValueError. We will catch it and raise ours
            # for consistency.
            raise ValueError("Can't figure out the language!")


def destination(filepath, preserve_paths=True, outdir=None):
    """
    Compute the destination HTML path for an input source file path. If the
    source is `lib/example.py`, the HTML will be at `docs/example.html`
    """

    dirname, filename = path.split(filepath)
    if not outdir:
        raise TypeError("Missing the required 'outdir' keyword argument.")

    name = filename
    if preserve_paths:
        name = path.join(dirname, name)
    dest = path.join(outdir, u"{}.html".format(name))
    # If `join` is passed an absolute path, it will ignore any earlier path
    # elements. We will force outdir to the beginning of the path to avoid
    # writing outside our destination.
    if not dest.startswith(outdir):
        dest = outdir + os.sep + dest
    return dest


def shift(list, default):
    """
    Shift items off the front of the `list` until it is empty, then return
    `default`.
    """

    try:
        return list.pop(0)
    except IndexError:
        return default


def remove_control_chars(s):
    # Sanitization regexp copied from
    # http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
    from pycco.compat import pycco_unichr
    control_chars = ''.join(
        map(pycco_unichr, list(range(0, 32)) + list(range(127, 160))))
    control_char_re = re.compile(u'[{}]'.format(re.escape(control_chars)))
    return control_char_re.sub('', s)


def ensure_directory(directory):
    """
    Sanitize directory string and ensure that the destination directory exists.
    """
    directory = remove_control_chars(directory)
    if not os.path.isdir(directory):
        os.makedirs(directory)

    return directory


# The start of each Pygments highlight block.
highlight_start = "<div class=\"highlight\"><pre>"

# The end of each Pygments highlight block.
highlight_end = "</pre></div>"


def _flatten_sources(sources):
    """
    This function will iterate through the list of sources and if a directory
    is encountered it will walk the tree for any files
    """
    _sources = []

    for source in sources:
        if os.path.isdir(source):
            for dirpath, _, filenames in os.walk(source):
                _sources.extend([os.path.join(dirpath, f) for f in filenames])
        else:
            _sources.append(source)

    return _sources


def process(sources, preserve_paths=True, outdir=None, language=None, encoding="utf8", index=False, skip=False):
    """For each source file passed as argument, generate the documentation."""

    if not outdir:
        raise TypeError("Missing the required 'directory' keyword argument.")

    # Make a copy of sources given on the command line. `main()` needs the
    # original list when monitoring for changed files.
    sources = sorted(_flatten_sources(sources))

    # Proceed to generating the documentation.
    if sources:
        outdir = ensure_directory(outdir)
        css = open(path.join(outdir, "pycco.css"), "wb")
        css.write(pycco_css.encode(encoding))
        css.close()

        generated_files = []

        def next_file():
            s = sources.pop(0)
            dest = destination(s, preserve_paths=preserve_paths, outdir=outdir)

            try:
                os.makedirs(path.split(dest)[0])
            except OSError:
                pass

            try:
                with open(dest, "wb") as f:
                    f.write(generate_documentation(s, preserve_paths=preserve_paths,
                                                   outdir=outdir,
                                                   language=language,
                                                   encoding=encoding))

                print("pycco: {} -> {}".format(s, dest))
                generated_files.append(dest)
            except UnicodeDecodeError:
                if skip:
                    print("pycco [FAILURE]: {}".format(s))
                else:
                    raise

            if sources:
                next_file()
        next_file()

        if index:
            with open(path.join(outdir, "index.html"), "wb") as f:
                f.write(generate_index.generate_index(generated_files, outdir))

__all__ = ("process", "generate_documentation")


def monitor(sources, opts):
    """Monitor each source file and re-generate documentation on change."""

    # The watchdog modules are imported in `main()` but we need to re-import
    # here to bring them into the local namespace.
    import watchdog.events
    import watchdog.observers

    # Watchdog operates on absolute paths, so map those to original paths
    # as specified on the command line.
    absolute_sources = dict((os.path.abspath(source), source)
                            for source in sources)

    class RegenerateHandler(watchdog.events.FileSystemEventHandler):

        """A handler for recompiling files which triggered watchdog events"""

        def on_modified(self, event):
            """Regenerate documentation for a file which triggered an event"""
            # Re-generate documentation from a source file if it was listed on
            # the command line. Watchdog monitors whole directories, so other
            # files may cause notifications as well.
            if event.src_path in absolute_sources:
                process([absolute_sources[event.src_path]],
                        outdir=opts.outdir,
                        preserve_paths=opts.paths)

    # Set up an observer which monitors all directories for files given on
    # the command line and notifies the handler defined above.
    event_handler = RegenerateHandler()
    observer = watchdog.observers.Observer()
    directories = set(os.path.split(source)[0] for source in sources)
    for directory in directories:
        observer.schedule(event_handler, path=directory)

    # Run the file change monitoring loop until the user hits Ctrl-C.
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()


def main():
    """Hook spot for the console script."""

    parser = optparse.OptionParser()
    parser.add_option('-p', '--paths', action='store_true',
                      help='Preserve path structure of original files')

    parser.add_option('-d', '--directory', action='store', type='string',
                      dest='outdir', default='docs',
                      help='The output directory that the rendered files should go to.')

    parser.add_option('-w', '--watch', action='store_true',
                      help='Watch original files and re-generate documentation on changes')

    parser.add_option('-l', '--force-language', action='store', type='string',
                      dest='language', default=None,
                      help='Force the language for the given files')

    parser.add_option('-i', '--generate_index', action='store_true',
                      help='Generate an index.html document with sitemap content')

    parser.add_option('-s', '--skip-bad-files', action='store_true',
                      dest='skip_bad_files',
                      help='Continue processing after hitting a bad file')

    opts, sources = parser.parse_args()
    if opts.outdir == '':
        outdir = '.'
    else:
        outdir = opts.outdir

    process(sources, outdir=outdir, preserve_paths=opts.paths,
            language=opts.language, index=opts.generate_index,
            skip=opts.skip_bad_files)

    # If the -w / --watch option was present, monitor the source directories
    # for changes and re-generate documentation for source files whenever they
    # are modified.
    if opts.watch:
        try:
            import watchdog.events
            import watchdog.observers
        except ImportError:
            sys.exit('The -w/--watch option requires the watchdog package.')

        monitor(sources, opts)

# Run the script.
if __name__ == "__main__":
    main()

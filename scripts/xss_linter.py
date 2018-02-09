#!/usr/bin/env python
"""
A linting tool to check for xss vulnerabilities.
"""
import argparse
import os
import sys

from scripts.xss_utils.linters import JavaScriptLinter, MakoTemplateLinter, PythonLinter, UnderscoreTemplateLinter
from scripts.xss_utils.reporting import SummaryResults
from scripts.xss_utils.utils import is_skip_dir, SKIP_DIRS


def _process_file(full_path, template_linters, options, summary_results, out):
    """
    For each linter, lints the provided file.  This means finding and printing
    violations.

    Arguments:
        full_path: The full path of the file to lint.
        template_linters: A list of linting objects.
        options: A list of the options.
        summary_results: A SummaryResults with a summary of the violations.
        out: output file

    """
    num_violations = 0
    directory = os.path.dirname(full_path)
    file_name = os.path.basename(full_path)
    for template_linter in template_linters:
        results = template_linter.process_file(directory, file_name)
        results.print_results(options, summary_results, out)


def _process_os_dir(directory, files, template_linters, options, summary_results, out):
    """
    Calls out to lint each file in the passed list of files.

    Arguments:
        directory: Directory being linted.
        files: All files in the directory to be linted.
        template_linters: A list of linting objects.
        options: A list of the options.
        summary_results: A SummaryResults with a summary of the violations.
        out: output file

    """
    for current_file in sorted(files, key=lambda s: s.lower()):
        full_path = os.path.join(directory, current_file)
        _process_file(full_path, template_linters, options, summary_results, out)


def _process_os_dirs(starting_dir, template_linters, options, summary_results, out):
    """
    For each linter, lints all the directories in the starting directory.

    Arguments:
        starting_dir: The initial directory to begin the walk.
        template_linters: A list of linting objects.
        options: A list of the options.
        summary_results: A SummaryResults with a summary of the violations.
        out: output file

    """
    for root, dirs, files in os.walk(starting_dir):
        if is_skip_dir(SKIP_DIRS, root):
            del dirs
            continue
        dirs.sort(key=lambda s: s.lower())
        _process_os_dir(root, files, template_linters, options, summary_results, out)


def _lint(file_or_dir, template_linters, options, summary_results, out):
    """
    For each linter, lints the provided file or directory.

    Arguments:
        file_or_dir: The file or initial directory to lint.
        template_linters: A list of linting objects.
        options: A list of the options.
        summary_results: A SummaryResults with a summary of the violations.
        out: output file

    """

    if file_or_dir is not None and os.path.isfile(file_or_dir):
        _process_file(file_or_dir, template_linters, options, summary_results, out)
    else:
        directory = "."
        if file_or_dir is not None:
            if os.path.exists(file_or_dir):
                directory = file_or_dir
            else:
                raise ValueError("Path [{}] is not a valid file or directory.".format(file_or_dir))
        _process_os_dirs(directory, template_linters, options, summary_results, out)

    summary_results.print_results(options, out)


def main():
    """
    Used to execute the linter. Use --help option for help.

    Prints all violations.
    """
    epilog = "For more help using the xss linter, including details on how to\n"
    epilog += "understand and fix any violations, read the docs here:\n"
    epilog += "\n"
    # pylint: disable=line-too-long
    epilog += "  http://edx.readthedocs.org/projects/edx-developer-guide/en/latest/conventions/preventing_xss.html#xss-linter\n"

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Checks that templates are safe.',
        epilog=epilog,
    )
    parser.add_argument(
        '--list-files', dest='list_files', action='store_true',
        help='Only display the filenames that contain violations.'
    )
    parser.add_argument(
        '--rule-totals', dest='rule_totals', action='store_true',
        help='Display the totals for each rule.'
    )
    parser.add_argument(
        '--verbose', dest='verbose', action='store_true',
        help='Print multiple lines where possible for additional context of violations.'
    )
    parser.add_argument('path', nargs="?", default=None, help='A file to lint or directory to recursively lint.')

    args = parser.parse_args()

    options = {
        'list_files': args.list_files,
        'rule_totals': args.rule_totals,
        'verbose': args.verbose,
    }
    template_linters = [MakoTemplateLinter(), UnderscoreTemplateLinter(), JavaScriptLinter(), PythonLinter()]
    summary_results = SummaryResults()

    _lint(args.path, template_linters, options, summary_results, out=sys.stdout)


if __name__ == "__main__":
    main()

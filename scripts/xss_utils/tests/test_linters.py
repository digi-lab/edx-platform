# -*- coding: utf-8 -*-
"""
Tests for linters.py
"""
from __future__ import print_function

import textwrap
from unittest import TestCase

from ddt import data, ddt

from scripts.xss_utils.reporting import FileResults
from scripts.xss_utils.linters import JavaScriptLinter, PythonLinter, UnderscoreTemplateLinter
from scripts.xss_utils.rules import Rules


class TestLinter(TestCase):
    """
    Test Linter base class
    """
    def _validate_data_rules(self, data, results):
        """
        Validates that the appropriate rule violations were triggered.

        Arguments:
            data: A dict containing the 'rule' (or rules) to be tests.
            results: The results, containing violations to be validated.

        """
        rules = []
        if isinstance(data['rule'], list):
            rules = data['rule']
        elif data['rule'] is not None:
            rules.append(data['rule'])
        results.violations.sort(key=lambda violation: violation.sort_key())

        # Print violations if the lengths are different.
        if len(results.violations) != len(rules):
            for violation in results.violations:
                print("Found violation: {}".format(violation.rule))

        self.assertEqual(len(results.violations), len(rules))
        for violation, rule in zip(results.violations, rules):
            self.assertEqual(violation.rule, rule)


@ddt
class TestUnderscoreTemplateLinter(TestLinter):
    """
    Test UnderscoreTemplateLinter
    """

    def test_check_underscore_file_is_safe(self):
        """
        Test check_underscore_file_is_safe with safe template
        """
        linter = UnderscoreTemplateLinter()
        results = FileResults('')

        template = textwrap.dedent("""
            <%- gettext('Single Line') %>

            <%-
                gettext('Multiple Lines')
            %>
        """)

        linter.check_underscore_file_is_safe(template, results)

        self.assertEqual(len(results.violations), 0)

    def test_check_underscore_file_is_not_safe(self):
        """
        Test check_underscore_file_is_safe with unsafe template
        """
        linter = UnderscoreTemplateLinter()
        results = FileResults('')

        template = textwrap.dedent("""
            <%= gettext('Single Line') %>

            <%=
                gettext('Multiple Lines')
            %>
        """)

        linter.check_underscore_file_is_safe(template, results)

        self.assertEqual(len(results.violations), 2)
        self.assertEqual(results.violations[0].rule, Rules.underscore_not_escaped)
        self.assertEqual(results.violations[1].rule, Rules.underscore_not_escaped)

    @data(
        {
            'template':
                '<% // xss-lint:   disable=underscore-not-escaped   %>\n'
                '<%= message %>',
            'is_disabled': [True],
        },
        {
            'template':
                '<% // xss-lint: disable=another-rule,underscore-not-escaped %>\n'
                '<%= message %>',
            'is_disabled': [True],
        },
        {
            'template':
                '<% // xss-lint: disable=another-rule %>\n'
                '<%= message %>',
            'is_disabled': [False],
        },
        {
            'template':
                '<% // xss-lint: disable=underscore-not-escaped %>\n'
                '<%= message %>\n'
                '<%= message %>',
            'is_disabled': [True, False],
        },
        {
            'template':
                '// This test does not use proper Underscore.js Template syntax\n'
                '// But, it is just testing that a maximum of 5 non-whitespace\n'
                '// are used to designate start of line for disabling the next line.\n'
                ' 1 2 3 4 5 xss-lint: disable=underscore-not-escaped %>\n'
                '<%= message %>\n'
                ' 1 2 3 4 5 6 xss-lint: disable=underscore-not-escaped %>\n'
                '<%= message %>',
            'is_disabled': [True, False],
        },
        {
            'template':
                '<%= message %><% // xss-lint: disable=underscore-not-escaped %>\n'
                '<%= message %>',
            'is_disabled': [True, False],
        },
        {
            'template':
                '<%= message %>\n'
                '<% // xss-lint: disable=underscore-not-escaped %>',
            'is_disabled': [False],
        },
    )
    def test_check_underscore_file_disable_rule(self, data):
        """
        Test check_underscore_file_is_safe with various disabled pragmas
        """
        linter = UnderscoreTemplateLinter()
        results = FileResults('')

        linter.check_underscore_file_is_safe(data['template'], results)

        violation_count = len(data['is_disabled'])
        self.assertEqual(len(results.violations), violation_count)
        for index in range(0, violation_count - 1):
            self.assertEqual(results.violations[index].is_disabled, data['is_disabled'][index])

    def test_check_underscore_file_disables_one_violation(self):
        """
        Test check_underscore_file_is_safe with disabled before a line only
        disables for the violation following
        """
        linter = UnderscoreTemplateLinter()
        results = FileResults('')

        template = textwrap.dedent("""
            <% // xss-lint: disable=underscore-not-escaped %>
            <%= message %>
            <%= message %>
        """)

        linter.check_underscore_file_is_safe(template, results)

        self.assertEqual(len(results.violations), 2)
        self.assertEqual(results.violations[0].is_disabled, True)
        self.assertEqual(results.violations[1].is_disabled, False)

    @data(
        {'template': '<%= HtmlUtils.ensureHtml(message) %>'},
        {'template': '<%= _.escape(message) %>'},
    )
    def test_check_underscore_no_escape_allowed(self, data):
        """
        Test check_underscore_file_is_safe with expressions that are allowed
        without escaping because the internal calls properly escape.
        """
        linter = UnderscoreTemplateLinter()
        results = FileResults('')

        linter.check_underscore_file_is_safe(data['template'], results)

        self.assertEqual(len(results.violations), 0)


@ddt
class TestJavaScriptLinter(TestLinter):
    """
    Test JavaScriptLinter
    """
    @data(
        {'template': 'var m = "Plain text " + message + "plain text"', 'rule': None},
        {'template': 'var m = "檌檒濦 " + message + "plain text"', 'rule': None},
        {
            'template':
                ("""$email_header.append($('<input>', type: "button", name: "copy-email-body-text","""
                 """ value: gettext("Copy Email To Editor"), id: 'copy_email_' + email_id))"""),
            'rule': None
        },
        {'template': 'var m = "<p>" + message + "</p>"', 'rule': Rules.javascript_concat_html},
        {
            'template': r'var m = "<p>\"escaped quote\"" + message + "\"escaped quote\"</p>"',
            'rule': Rules.javascript_concat_html
        },
        {'template': '  // var m = "<p>" + commentedOutMessage + "</p>"', 'rule': None},
        {'template': 'var m = " <p> " + message + " </p> "', 'rule': Rules.javascript_concat_html},
        {'template': 'var m = " <p> " + message + " broken string', 'rule': Rules.javascript_concat_html},
    )
    def test_concat_with_html(self, data):
        """
        Test check_javascript_file_is_safe with concatenating strings and HTML
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)
        self._validate_data_rules(data, results)

    @data(
        {'template': 'test.append( test.render().el )', 'rule': None},
        {'template': 'test.append(test.render().el)', 'rule': None},
        {'template': 'test.append(test.render().$el)', 'rule': None},
        {'template': 'test.append(testEl)', 'rule': None},
        {'template': 'test.append($test)', 'rule': None},
        # plain text is ok because any & will be escaped, and it stops false
        # negatives on some other objects with an append() method
        {'template': 'test.append("plain text")', 'rule': None},
        {'template': 'test.append("<div/>")', 'rule': Rules.javascript_jquery_append},
        {'template': 'graph.svg.append("g")', 'rule': None},
        {'template': 'test.append( $( "<div>" ) )', 'rule': None},
        {'template': 'test.append($("<div>"))', 'rule': None},
        {'template': 'test.append($("<div/>"))', 'rule': None},
        {'template': 'test.append(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'HtmlUtils.append($el, someHtml)', 'rule': None},
        {'template': 'test.append("fail on concat" + test.render().el)', 'rule': Rules.javascript_jquery_append},
        {'template': 'test.append("fail on concat" + testEl)', 'rule': Rules.javascript_jquery_append},
        {'template': 'test.append(message)', 'rule': Rules.javascript_jquery_append},
    )
    def test_jquery_append(self, data):
        """
        Test check_javascript_file_is_safe with JQuery append()
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    @data(
        {'template': 'test.prepend( test.render().el )', 'rule': None},
        {'template': 'test.prepend(test.render().el)', 'rule': None},
        {'template': 'test.prepend(test.render().$el)', 'rule': None},
        {'template': 'test.prepend(testEl)', 'rule': None},
        {'template': 'test.prepend($test)', 'rule': None},
        {'template': 'test.prepend("text")', 'rule': None},
        {'template': 'test.prepend( $( "<div>" ) )', 'rule': None},
        {'template': 'test.prepend($("<div>"))', 'rule': None},
        {'template': 'test.prepend($("<div/>"))', 'rule': None},
        {'template': 'test.prepend(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'HtmlUtils.prepend($el, someHtml)', 'rule': None},
        {'template': 'test.prepend("broken string)', 'rule': Rules.javascript_jquery_prepend},
        {'template': 'test.prepend("fail on concat" + test.render().el)', 'rule': Rules.javascript_jquery_prepend},
        {'template': 'test.prepend("fail on concat" + testEl)', 'rule': Rules.javascript_jquery_prepend},
        {'template': 'test.prepend(message)', 'rule': Rules.javascript_jquery_prepend},
    )
    def test_jquery_prepend(self, data):
        """
        Test check_javascript_file_is_safe with JQuery prepend()
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    @data(
        {'template': 'test.unwrap(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.wrap(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.wrapAll(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.wrapInner(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.after(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.before(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.replaceAll(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.replaceWith(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'test.replaceWith(edx.HtmlUtils.HTML(htmlString).toString())', 'rule': None},
        {'template': 'test.unwrap(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.wrap(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.wrapAll(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.wrapInner(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.after(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.before(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.replaceAll(anything)', 'rule': Rules.javascript_jquery_insertion},
        {'template': 'test.replaceWith(anything)', 'rule': Rules.javascript_jquery_insertion},
    )
    def test_jquery_insertion(self, data):
        """
        Test check_javascript_file_is_safe with JQuery insertion functions
        other than append(), prepend() and html() that take content as an
        argument (e.g. before(), after()).
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    @data(
        {'template': '  element.parentNode.appendTo(target);', 'rule': None},
        {'template': '  test.render().el.appendTo(target);', 'rule': None},
        {'template': '  test.render().$el.appendTo(target);', 'rule': None},
        {'template': '  test.$element.appendTo(target);', 'rule': None},
        {'template': '  test.testEl.appendTo(target);', 'rule': None},
        {'template': '$element.appendTo(target);', 'rule': None},
        {'template': 'el.appendTo(target);', 'rule': None},
        {'template': 'testEl.appendTo(target);', 'rule': None},
        {'template': 'testEl.prependTo(target);', 'rule': None},
        {'template': 'testEl.insertAfter(target);', 'rule': None},
        {'template': 'testEl.insertBefore(target);', 'rule': None},
        {'template': 'anycall().appendTo(target)', 'rule': Rules.javascript_jquery_insert_into_target},
        {'template': 'anything.appendTo(target)', 'rule': Rules.javascript_jquery_insert_into_target},
        {'template': 'anything.prependTo(target)', 'rule': Rules.javascript_jquery_insert_into_target},
        {'template': 'anything.insertAfter(target)', 'rule': Rules.javascript_jquery_insert_into_target},
        {'template': 'anything.insertBefore(target)', 'rule': Rules.javascript_jquery_insert_into_target},
    )
    def test_jquery_insert_to_target(self, data):
        """
        Test check_javascript_file_is_safe with JQuery insert to target
        functions that take a target as an argument, like appendTo() and
        prependTo().
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    @data(
        {'template': 'test.html()', 'rule': None},
        {'template': 'test.html( )', 'rule': None},
        {'template': "test.html( '' )", 'rule': None},
        {'template': "test.html('')", 'rule': None},
        {'template': 'test.html("")', 'rule': None},
        {'template': 'test.html(HtmlUtils.ensureHtml(htmlSnippet).toString())', 'rule': None},
        {'template': 'HtmlUtils.setHtml($el, someHtml)', 'rule': None},
        {'template': 'test.html("any string")', 'rule': Rules.javascript_jquery_html},
        {'template': 'test.html("broken string)', 'rule': Rules.javascript_jquery_html},
        {'template': 'test.html("檌檒濦")', 'rule': Rules.javascript_jquery_html},
        {'template': 'test.html(anything)', 'rule': Rules.javascript_jquery_html},
    )
    def test_jquery_html(self, data):
        """
        Test check_javascript_file_is_safe with JQuery html()
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)
        self._validate_data_rules(data, results)

    @data(
        {'template': 'StringUtils.interpolate()', 'rule': None},
        {'template': 'HtmlUtils.interpolateHtml()', 'rule': None},
        {'template': 'interpolate(anything)', 'rule': Rules.javascript_interpolate},
    )
    def test_javascript_interpolate(self, data):
        """
        Test check_javascript_file_is_safe with interpolate()
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    @data(
        {'template': '_.escape(message)', 'rule': None},
        {'template': 'anything.escape(message)', 'rule': Rules.javascript_escape},
    )
    def test_javascript_interpolate(self, data):
        """
        Test check_javascript_file_is_safe with interpolate()
        """
        linter = JavaScriptLinter()
        results = FileResults('')

        linter.check_javascript_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)


@ddt
class TestPythonLinter(TestLinter):
    """
    Test PythonLinter
    """
    @data(
        {'template': 'm = "Plain text " + message + "plain text"', 'rule': None},
        {'template': 'm = "檌檒濦 " + message + "plain text"', 'rule': None},
        {'template': '  # m = "<p>" + commentedOutMessage + "</p>"', 'rule': None},
        {'template': 'm = "<p>" + message + "</p>"', 'rule': [Rules.python_concat_html, Rules.python_concat_html]},
        {'template': 'm = " <p> " + message + " </p> "', 'rule': [Rules.python_concat_html, Rules.python_concat_html]},
        {'template': 'm = " <p> " + message + " broken string', 'rule': Rules.python_parse_error},
    )
    def test_concat_with_html(self, data):
        """
        Test check_python_file_is_safe with concatenating strings and HTML
        """
        linter = PythonLinter()
        results = FileResults('')

        linter.check_python_file_is_safe(data['template'], results)

        self._validate_data_rules(data, results)

    def test_check_python_expression_display_name(self):
        """
        Test _check_python_file_is_safe with display_name_with_default_escaped
        fails.
        """
        linter = PythonLinter()
        results = FileResults('')

        python_file = textwrap.dedent("""
            context = {
                'display_name': self.display_name_with_default_escaped,
            }
        """)

        linter.check_python_file_is_safe(python_file, results)

        self.assertEqual(len(results.violations), 1)
        self.assertEqual(results.violations[0].rule, Rules.python_deprecated_display_name)

    def test_check_custom_escaping(self):
        """
        Test _check_python_file_is_safe fails when custom escapins is used.
        """
        linter = PythonLinter()
        results = FileResults('')

        python_file = textwrap.dedent("""
            msg = mmlans.replace('<', '&lt;')
        """)

        linter.check_python_file_is_safe(python_file, results)

        self.assertEqual(len(results.violations), 1)
        self.assertEqual(results.violations[0].rule, Rules.python_custom_escape)

    @data(
        {
            'python':
                textwrap.dedent("""
                    msg = Text("Mixed {span_start}text{span_end}").format(
                        span_start=HTML("<span>"),
                        span_end=HTML("</span>"),
                    )
                """),
            'rule': None
        },
        {
            'python':
                textwrap.dedent("""
                    msg = "Mixed {span_start}text{span_end}".format(
                        span_start=HTML("<span>"),
                        span_end=HTML("</span>"),
                    )
                """),
            'rule': Rules.python_requires_html_or_text
        },
        {
            'python':
                textwrap.dedent("""
                    msg = "Mixed {span_start}{text}{span_end}".format(
                        span_start=HTML("<span>"),
                        text=Text("This should still break."),
                        span_end=HTML("</span>"),
                    )
                """),
            'rule': Rules.python_requires_html_or_text
        },
        {
            'python':
                textwrap.dedent("""
                    msg = Text("Mixed {link_start}text{link_end}".format(
                        link_start=HTML("<a href='{}'>").format(url),
                        link_end=HTML("</a>"),
                    ))
                """),
            'rule': [Rules.python_close_before_format, Rules.python_requires_html_or_text]
        },
        {
            'python':
                textwrap.dedent("""
                    msg = Text("Mixed {link_start}text{link_end}").format(
                        link_start=HTML("<a href='{}'>".format(url)),
                        link_end=HTML("</a>"),
                    )
                """),
            'rule': Rules.python_close_before_format
        },
        {
            'python':
                textwrap.dedent("""
                    msg = Text("Mixed {link_start}text{link_end}".format(
                        link_start=HTML("<a href='{}'>".format(HTML('<b>'))),
                        link_end=HTML("</a>"),
                    ))
                """),
            'rule':
                [
                    Rules.python_close_before_format,
                    Rules.python_requires_html_or_text,
                    Rules.python_close_before_format,
                    Rules.python_requires_html_or_text
                ]
        },
        {
            'python':
                textwrap.dedent("""
                    msg = "Mixed {span_start}text{span_end}".format(
                        span_start="<span>",
                        span_end="</span>",
                    )
                """),
            'rule': [Rules.python_wrap_html, Rules.python_wrap_html]
        },
        {
            'python':
                textwrap.dedent("""
                    msg = Text(_("String with multiple lines "
                        "{link_start}unenroll{link_end} "
                        "and final line")).format(
                            link_start=HTML(
                                '<a id="link__over_multiple_lines" '
                                'data-course-id="{course_id}" '
                                'href="#test-modal">'
                            ).format(
                                # Line comment with ' to throw off parser
                                course_id=course_overview.id
                            ),
                            link_end=HTML('</a>'),
                    )
                """),
            'rule': None
        },
        {
            'python': "msg = '<span></span>'",
            'rule': None
        },
        {
            'python': "msg = HTML('<span></span>')",
            'rule': None
        },
        {
            'python': r"""msg = '<a href="{}"'.format(url)""",
            'rule': Rules.python_wrap_html
        },
        {
            'python': r"""msg = '{}</p>'.format(message)""",
            'rule': Rules.python_wrap_html
        },
        {
            'python': r"""r'regex with {} and named group(?P<id>\d+)?$'.format(test)""",
            'rule': None
        },
        {
            'python': r"""msg = '<a href="%s"' % url""",
            'rule': Rules.python_interpolate_html
        },
        {
            'python':
                textwrap.dedent("""
                    def __repr__(self):
                        # Assume repr implementations are safe, and not HTML
                        return '<CCXCon {}>'.format(self.title)
                """),
            'rule': None
        },
        {
            'python': r"""msg = '%s</p>' % message""",
            'rule': Rules.python_interpolate_html
        },
        {
            'python': "msg = HTML('<span></span>'",
            'rule': Rules.python_parse_error
        },
    )
    def test_check_python_with_text_and_html(self, data):
        """
        Test _check_python_file_is_safe tests for proper use of Text() and
        Html().

        """
        linter = PythonLinter()
        results = FileResults('')

        file_content = textwrap.dedent(data['python'])

        linter.check_python_file_is_safe(file_content, results)

        self._validate_data_rules(data, results)

    def test_check_python_with_text_and_html_mixed(self):
        """
        Test _check_python_file_is_safe tests for proper use of Text() and
        Html() for a Python file with a mix of rules.

        """
        linter = PythonLinter()
        results = FileResults('')

        file_content = textwrap.dedent("""
            msg1 = '<a href="{}"'.format(url)
            msg2 = "Mixed {link_start}text{link_end}".format(
                link_start=HTML("<a href='{}'>".format(url)),
                link_end="</a>",
            )
            msg3 = '<a href="%s"' % url
        """)

        linter.check_python_file_is_safe(file_content, results)

        results.violations.sort(key=lambda violation: violation.sort_key())

        self.assertEqual(len(results.violations), 5)
        self.assertEqual(results.violations[0].rule, Rules.python_wrap_html)
        self.assertEqual(results.violations[1].rule, Rules.python_requires_html_or_text)
        self.assertEqual(results.violations[2].rule, Rules.python_close_before_format)
        self.assertEqual(results.violations[3].rule, Rules.python_wrap_html)
        self.assertEqual(results.violations[4].rule, Rules.python_interpolate_html)

    @data(
        {
            'python':
                """
                    response_str = textwrap.dedent('''
                        <div>
                            <h3 class="result">{response}</h3>
                        </div>
                    ''').format(response=response_text)
                """,
            'rule': Rules.python_wrap_html,
            'start_line': 2,
        },
        {
            'python':
                """
                def function(self):
                    '''
                    Function comment.
                    '''
                    response_str = textwrap.dedent('''
                        <div>
                            <h3 class="result">{response}</h3>
                        </div>
                    ''').format(response=response_text)
                """,
            'rule': Rules.python_wrap_html,
            'start_line': 6,
        },
        {
            'python':
                """
                def function(self):
                    '''
                    Function comment.
                    '''
                    response_str = '''<h3 class="result">{response}</h3>'''.format(response=response_text)
                """,
            'rule': Rules.python_wrap_html,
            'start_line': 6,
        },
        {
            'python':
                """
                def function(self):
                    '''
                    Function comment.
                    '''
                    response_str = textwrap.dedent('''
                        <div>
                            \"\"\" Do we care about a nested triple quote? \"\"\"
                            <h3 class="result">{response}</h3>
                        </div>
                    ''').format(response=response_text)
                """,
            'rule': Rules.python_wrap_html,
            'start_line': 6,
        },
    )
    def test_check_python_with_triple_quotes(self, data):
        """
        Test _check_python_file_is_safe with triple quotes.

        """
        linter = PythonLinter()
        results = FileResults('')

        file_content = textwrap.dedent(data['python'])

        linter.check_python_file_is_safe(file_content, results)

        self._validate_data_rules(data, results)
        self.assertEqual(results.violations[0].start_line, data['start_line'])

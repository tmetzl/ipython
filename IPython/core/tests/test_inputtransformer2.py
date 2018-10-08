"""Tests for the token-based transformers in IPython.core.inputtransformer2

Line-based transformers are the simpler ones; token-based transformers are
more complex. See test_inputtransformer2_line for tests for line-based
transformations.
"""
import nose.tools as nt
import string

from IPython.core import inputtransformer2 as ipt2
from IPython.core.inputtransformer2 import make_tokens_by_line

from textwrap import dedent

MULTILINE_MAGIC = ("""\
a = f()
%foo \\
bar
g()
""".splitlines(keepends=True), (2, 0), """\
a = f()
get_ipython().run_line_magic('foo', ' bar')
g()
""".splitlines(keepends=True))

INDENTED_MAGIC = ("""\
for a in range(5):
    %ls
""".splitlines(keepends=True), (2, 4), """\
for a in range(5):
    get_ipython().run_line_magic('ls', '')
""".splitlines(keepends=True))

MULTILINE_MAGIC_ASSIGN = ("""\
a = f()
b = %foo \\
  bar
g()
""".splitlines(keepends=True), (2, 4), """\
a = f()
b = get_ipython().run_line_magic('foo', '   bar')
g()
""".splitlines(keepends=True))

MULTILINE_SYSTEM_ASSIGN = ("""\
a = f()
b = !foo \\
  bar
g()
""".splitlines(keepends=True), (2, 4), """\
a = f()
b = get_ipython().getoutput('foo    bar')
g()
""".splitlines(keepends=True))

AUTOCALL_QUOTE = (
    [",f 1 2 3\n"], (1, 0),
    ['f("1", "2", "3")\n']
)

AUTOCALL_QUOTE2 = (
    [";f 1 2 3\n"], (1, 0),
    ['f("1 2 3")\n']
)

AUTOCALL_PAREN = (
    ["/f 1 2 3\n"], (1, 0),
    ['f(1, 2, 3)\n']
)

SIMPLE_HELP = (
    ["foo?\n"], (1, 0),
    ["get_ipython().run_line_magic('pinfo', 'foo')\n"]
)

DETAILED_HELP = (
    ["foo??\n"], (1, 0),
    ["get_ipython().run_line_magic('pinfo2', 'foo')\n"]
)

MAGIC_HELP = (
    ["%foo?\n"], (1, 0),
    ["get_ipython().run_line_magic('pinfo', '%foo')\n"]
)

HELP_IN_EXPR = (
    ["a = b + c?\n"], (1, 0),
    ["get_ipython().set_next_input('a = b + c');"
     "get_ipython().run_line_magic('pinfo', 'c')\n"]
)

HELP_CONTINUED_LINE = ("""\
a = \\
zip?
""".splitlines(keepends=True), (1, 0),
[r"get_ipython().set_next_input('a = \\\nzip');get_ipython().run_line_magic('pinfo', 'zip')" + "\n"]
)

HELP_MULTILINE = ("""\
(a,
b) = zip?
""".splitlines(keepends=True), (1, 0),
[r"get_ipython().set_next_input('(a,\nb) = zip');get_ipython().run_line_magic('pinfo', 'zip')" + "\n"]
)

def null_cleanup_transformer(lines):
    """
    A cleanup transform that returns an empty list.
    """
    return []

def check_make_token_by_line_never_ends_empty():
    """
    Check that not sequence of single or double characters ends up leading to en empty list of tokens
    """
    from string import printable
    for c in printable:
        nt.assert_not_equal(make_tokens_by_line(c)[-1], [])
        for k in printable:
            nt.assert_not_equal(make_tokens_by_line(c+k)[-1], [])

def check_find(transformer, case, match=True):
    sample, expected_start, _  = case
    tbl = make_tokens_by_line(sample)
    res = transformer.find(tbl)
    if match:
        # start_line is stored 0-indexed, expected values are 1-indexed
        nt.assert_equal((res.start_line+1, res.start_col), expected_start)
        return res
    else:
        nt.assert_is(res, None)

def check_transform(transformer_cls, case):
    lines, start, expected = case
    transformer = transformer_cls(start)
    nt.assert_equal(transformer.transform(lines), expected)

def test_continued_line():
    lines = MULTILINE_MAGIC_ASSIGN[0]
    nt.assert_equal(ipt2.find_end_of_continued_line(lines, 1), 2)

    nt.assert_equal(ipt2.assemble_continued_line(lines, (1, 5), 2), "foo    bar")

def test_find_assign_magic():
    check_find(ipt2.MagicAssign, MULTILINE_MAGIC_ASSIGN)
    check_find(ipt2.MagicAssign, MULTILINE_SYSTEM_ASSIGN, match=False)

def test_transform_assign_magic():
    check_transform(ipt2.MagicAssign, MULTILINE_MAGIC_ASSIGN)

def test_find_assign_system():
    check_find(ipt2.SystemAssign, MULTILINE_SYSTEM_ASSIGN)
    check_find(ipt2.SystemAssign, (["a =  !ls\n"], (1, 5), None))
    check_find(ipt2.SystemAssign, (["a=!ls\n"], (1, 2), None))
    check_find(ipt2.SystemAssign, MULTILINE_MAGIC_ASSIGN, match=False)

def test_transform_assign_system():
    check_transform(ipt2.SystemAssign, MULTILINE_SYSTEM_ASSIGN)

def test_find_magic_escape():
    check_find(ipt2.EscapedCommand, MULTILINE_MAGIC)
    check_find(ipt2.EscapedCommand, INDENTED_MAGIC)
    check_find(ipt2.EscapedCommand, MULTILINE_MAGIC_ASSIGN, match=False)

def test_transform_magic_escape():
    check_transform(ipt2.EscapedCommand, MULTILINE_MAGIC)
    check_transform(ipt2.EscapedCommand, INDENTED_MAGIC)

def test_find_autocalls():
    for case in [AUTOCALL_QUOTE, AUTOCALL_QUOTE2, AUTOCALL_PAREN]:
        print("Testing %r" % case[0])
        check_find(ipt2.EscapedCommand, case)

def test_transform_autocall():
    for case in [AUTOCALL_QUOTE, AUTOCALL_QUOTE2, AUTOCALL_PAREN]:
        print("Testing %r" % case[0])
        check_transform(ipt2.EscapedCommand, case)

def test_find_help():
    for case in [SIMPLE_HELP, DETAILED_HELP, MAGIC_HELP, HELP_IN_EXPR]:
        check_find(ipt2.HelpEnd, case)

    tf = check_find(ipt2.HelpEnd, HELP_CONTINUED_LINE)
    nt.assert_equal(tf.q_line, 1)
    nt.assert_equal(tf.q_col, 3)

    tf = check_find(ipt2.HelpEnd, HELP_MULTILINE)
    nt.assert_equal(tf.q_line, 1)
    nt.assert_equal(tf.q_col, 8)

    # ? in a comment does not trigger help
    check_find(ipt2.HelpEnd, (["foo # bar?\n"], None, None), match=False)
    # Nor in a string
    check_find(ipt2.HelpEnd, (["foo = '''bar?\n"], None, None), match=False)

def test_transform_help():
    tf = ipt2.HelpEnd((1, 0), (1, 9))
    nt.assert_equal(tf.transform(HELP_IN_EXPR[0]), HELP_IN_EXPR[2])

    tf = ipt2.HelpEnd((1, 0), (2, 3))
    nt.assert_equal(tf.transform(HELP_CONTINUED_LINE[0]), HELP_CONTINUED_LINE[2])

    tf = ipt2.HelpEnd((1, 0), (2, 8))
    nt.assert_equal(tf.transform(HELP_MULTILINE[0]), HELP_MULTILINE[2])

def test_check_complete():
    cc = ipt2.TransformerManager().check_complete
    nt.assert_equal(cc("a = 1"), ('complete', None))
    nt.assert_equal(cc("for a in range(5):"), ('incomplete', 4))
    nt.assert_equal(cc("raise = 2"), ('invalid', None))
    nt.assert_equal(cc("a = [1,\n2,"), ('incomplete', 0))
    nt.assert_equal(cc(")"), ('incomplete', 0))
    nt.assert_equal(cc("\\\r\n"), ('incomplete', 0))
    nt.assert_equal(cc("a = '''\n   hi"), ('incomplete', 3))
    nt.assert_equal(cc("def a():\n x=1\n global x"), ('invalid', None))
    nt.assert_equal(cc("a \\ "), ('invalid', None))  # Nothing allowed after backslash
    nt.assert_equal(cc("1\\\n+2"), ('complete', None))
    nt.assert_equal(cc("exit"), ('complete', None))

    example = dedent("""
        if True:
            a=1""" )

    nt.assert_equal(cc(example), ('incomplete', 4))
    nt.assert_equal(cc(example+'\n'), ('complete', None))
    nt.assert_equal(cc(example+'\n    '), ('complete', None))

    # no need to loop on all the letters/numbers.
    short = '12abAB'+string.printable[62:]
    for c in short:
        # test does not raise:
        cc(c)
        for k in short:
            cc(c+k)

def test_null_cleanup_transformer():
    manager = ipt2.TransformerManager()
    manager.cleanup_transforms.insert(0, null_cleanup_transformer)
    nt.assert_is(manager.transform_cell(""), "")

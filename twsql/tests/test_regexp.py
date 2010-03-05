import unittest
import re

class RegexpPatternTest(unittest.TestCase):

    def test_control_comment_start_pattern(self):
        pattern = r"""
            /\*\#            # opening
            
            ([\w\.\:]+)      # keyword
            
            ((?:\s+:?\w+)*)  # text
            
            \s*              # more whitespace
            
            \*/              # closing
            """
        reg = re.compile(pattern, re.S | re.X)

        # for statement
        match = reg.match('/*#for item in :items*/followed text...')
        assert match is not None
        assert match.group(1) == 'for'
        assert match.group(2) == ' item in :items'

        # embed statement
        match = reg.match('/*#embed :embed_item*/followed text...')
        assert match is not None
        assert match.group(1) == 'embed'
        assert match.group(2) == ' :embed_item'

        # if statement
        match = reg.match('/*#if :boolean_item*/followed text...')
        assert match is not None
        assert match.group(1) == 'if'
        assert match.group(2) == ' :boolean_item'

        # invalid values
        assert reg.match('/*for item in :items*/followed text...') is None
        assert reg.match('/*embed :item*/followed test...') is None
        assert reg.match('/*if :item*/followed test...') is None

        assert reg.match('/*#for item in ite:ms*/') is None
        assert reg.match('/*#for item in :ite:ms*/') is None
        assert reg.match('/*#for item in $items*/') is None
        assert reg.match('/*#for item in #items*/') is None

    def test_control_comment_end_pattern(self):
        pattern = r"""/\*#(?:/|end)[\t ]*(\w+?)[\t ]*\*/"""
        reg = re.compile(pattern)

        # for statement
        match = reg.match('/*#/for*/ followed text...')
        assert match is not None
        assert match.group(1) == 'for'
        match = reg.match('/*#endfor*/ followed text...')
        assert match is not None
        assert match.group(1) == 'for'

        # embed statement
        match = reg.match('/*#/embed*/')
        assert match is not None
        assert match.group(1) == 'embed'

        # if statement
        match = reg.match('/*#/if*/')
        assert match is not None
        assert match.group(1) == 'if'

        # invalid values
        assert reg.match('/*#for*/') is None
        assert reg.match('/*/for*/') is None
        assert reg.match('/*endfor*/') is None

    def test_placeholder_comment_pattern(self):
        pattern = r"""/\*:(\w+?)\*/"""
        reg = re.compile(pattern)

        # string literal
        match = reg.match("/*:item*/'phantom string' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/'truthly phrantom string/*this is not a comment*/' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match(
            """/*:item*/'phantom string allowing multi-line text
            this line also phantom string
            ...
            '""")
        assert match is not None
        assert match.group(1) == 'item'

        # number literal
        match = reg.match("/*:item*/1000 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/1000")
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/1000.235 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/+1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/-1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/3.402823E+38")
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/2.802597E-45")
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/-2.802597E-45")
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/-3.402823E+38")
        assert match.group(1) == 'item'

        # SQL literal
        match = reg.match("/*:item*/CURRENT_TIMESTAMP and id = 38293")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/CURRENT_TIMESTAMP")
        assert match is not None
        assert match.group(1) == 'item'

        # SQL function
        match = reg.match("/*:item*/now()")
        assert match is not None
        assert match.group(1) == 'item'

        # paren
        match = reg.match("/*:item*/('one', 'two', 'three') and...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/(1, 2, 3) and...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/('one', 2, ';<>@=~') and...")
        assert match is not None
        assert match.group(1) == 'item'
        match = reg.match("/*:item*/(CURRENT_TIMESTAMP, '2010-03-04 12:45:00') and id = 323")
        assert match is not None
        assert match.group(1) == 'item'

        match = reg.match("/*:item*/(now(), CURRENT_TIMESTAMP, '2010-03-04 12:45:00') and ...")
        assert match is not None
        assert match.group(1) == 'item'
        print match.groups()
        match = reg.match("/*:item*/(CURRENT_TIMESTAMP, now(), '2010-03-04 12:45:00') and ...")
        assert match is not None
        assert match.group(1) == 'item'
        print match.groups()
        match = reg.match("/*:item*/('2010-03-04 12:45:00', CURRENT_TIMESTAMP, now()) and id in ()...")
        assert match is not None
        assert match.group(1) == 'item'
        print match.groups()

        # invalid values
        assert reg.match("/*item*/'phantom text'") is None

    def test_block_comment_pattern(self):
        pattern = r"""/\*([^:#].*?)\*/"""
        reg = re.compile(pattern, re.S)

        match = reg.match("""/*comment text*/""")
        assert match is not None
        assert match.group(1) == 'comment text'
        match = reg.match("""/* comment text*/""")
        assert match is not None
        assert match.group(1) == ' comment text'

        match = reg.match("""/*comment text */""")
        assert match is not None
        assert match.group(1) == 'comment text '

        match = reg.match("""/*
            comment text
            this is a multiline comment
            */""")
        assert match is not None
        assert match.group(1) == """
            comment text
            this is a multiline comment
            """

    def test_line_comment_pattern(self):
        pattern = r"""--([^\n\r]*)"""
        reg = re.compile(pattern)

        match = reg.match("""-- line comment""")
        assert match is not None
        assert match.group(1) == ' line comment'

        match = reg.match("""-- line comment
            , count(*)
            """)
        assert match is not None
        assert match.group(1) == ' line comment'

class LiteralPatternTest(unittest.TestCase):

    pattern = r"""
        (.*?)         # anything, followed by:
        (
         (?=--) # an eval or line-based comment preceded by a consumed \n and whitespace
         |
         (?=\/\*) # multiline comment
         |
         (?=</?[%&])  # a substitution or block or call start or end
                                      # - don't consume
         |
         (\\\r?\n)         # an escaped newline - throw away
         |
         \Z           # end of string
        )"""
    reg = re.compile(pattern, re.X | re.S)

    def test_multiline_comment(self):
        data = """
            select
                *
            from
            /* this is a multiline comment
               ...
               end
            */
            """
        match = self.reg.match(data)
        assert match is not None
        print match.group(1)
        assert match.group(1) == """
            select
                *
            from
            """
        (start, end) = match.span()
        assert start == 0
        assert data[end] == '/'

    def test_singleline_comment(self):
        data = """
            select
                ident -- member.ident
            """
        match = self.reg.match(data)
        assert match is not None
        print match.groups()
        assert match.group(1) == """
            select
                ident """
        (start, end) = match.span()
        assert start == 0
        assert data[end] == '-'

    def test_end_of_text(self):
        data = """
            select
                ident
            from
                t_member"""
        match = self.reg.match(data)
        assert match is not None
        print match.groups()
        assert match.group(1) == """
            select
                ident
            from
                t_member"""
        (start, end) = match.span()
        assert start == 0
        self.assertRaises(IndexError, lambda: data[end])
        assert data[end-1] == 'r'

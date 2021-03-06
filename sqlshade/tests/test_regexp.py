import unittest
import re

class RegexpPatternTest(unittest.TestCase):

    def test_control_comment_start_pattern(self):
        pattern = r"""
            /\*\#(?!\/|end)  # opening
            
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

        assert reg.match('/*#/for*/') is None
        assert reg.match('/*#endfor*/') is None

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

class PlaceholderPatternTest(unittest.TestCase):

    pattern = r"""/\*:(\w+?)\*/([\w'(+-])"""
    reg = re.compile(pattern)

    def test_string_literal(self):
        match = self.reg.match("/*:item*/'phantom string' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == "'"
        match = self.reg.match("/*:item*/'truthly phrantom string/*this is not a comment*/' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == "'"
        match = self.reg.match(
            """/*:item*/'phantom string allowing multi-line text
            this line also phantom string
            ...
            '""")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == "'"

    def test_number_literal(self):
        match = self.reg.match("/*:item*/1000 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '1'
        match = self.reg.match("/*:item*/1000")
        assert match.group(1) == 'item'
        match = self.reg.match("/*:item*/1000.235 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '1'
        match = self.reg.match("/*:item*/+1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '+'
        match = self.reg.match("/*:item*/-1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '-'
        match = self.reg.match("/*:item*/3.402823E+38")
        assert match.group(1) == 'item'
        assert match.group(2) == '3'
        match = self.reg.match("/*:item*/2.802597E-45")
        assert match.group(1) == 'item'
        assert match.group(2) == '2'
        match = self.reg.match("/*:item*/-2.802597E-45")
        assert match.group(1) == 'item'
        assert match.group(2) == '-'
        match = self.reg.match("/*:item*/-3.402823E+38")
        assert match.group(1) == 'item'
        assert match.group(2) == '-'

    def test_other_sql_literal(self):
        match = self.reg.match("/*:item*/CURRENT_TIMESTAMP and id = 38293")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == 'C'
        match = self.reg.match("/*:item*/CURRENT_TIMESTAMP")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == 'C'
        match = self.reg.match("/*:item*/now()")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == 'n'

    def test_in_arrays(self):
        match = self.reg.match("/*:item*/('one', 'two', 'three') and...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        match = self.reg.match("/*:item*/(1, 2, 3) and...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        match = self.reg.match("/*:item*/('one', 2, ';<>@=~') and...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        match = self.reg.match("/*:item*/(CURRENT_TIMESTAMP, '2010-03-04 12:45:00') and id = 323")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('

        # complex
        match = self.reg.match("/*:item*/(now(), CURRENT_TIMESTAMP, '2010-03-04 12:45:00') and ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        print match.groups()
        match = self.reg.match("/*:item*/(CURRENT_TIMESTAMP, now(), '2010-03-04 12:45:00') and ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        print match.groups()
        match = self.reg.match("/*:item*/('2010-03-04 12:45:00', CURRENT_TIMESTAMP, now()) and id in ()...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '('
        print match.groups()

    def test_invalid_patterns(self):
        assert self.reg.match("/*item*/'phantom text'") is None

class CommentPatternTest(unittest.TestCase):

    pattern = r"""
        (?:
         /\*([^:#].*?)\*/
         |
         --([^\n\r]*)
        )
        """
    reg = re.compile(pattern, re.S | re.X)

    def test_multiline(self):
        match = self.reg.match("""/*comment text*/""")
        assert match is not None
        assert match.group(1) == 'comment text'
        match = self.reg.match("""/* comment text*/""")
        assert match is not None
        assert match.group(1) == ' comment text'

        match = self.reg.match("""/*comment text */""")
        assert match is not None
        assert match.group(1) == 'comment text '

        match = self.reg.match("""/*
            comment text
            this is a multiline comment
            */""")
        assert match is not None
        assert match.group(1) == """
            comment text
            this is a multiline comment
            """

    def test_not_match_control_or_placeholder_comment(self):
        match = self.reg.match("""/*#for item in :items*/""")
        assert match is None
        match = self.reg.match("""/*:item*/'replaceme'""")
        assert match is None

    def test_singleline(self):
        match = self.reg.match("""-- line comment""")
        assert match is not None
        print match.groups()
        assert match.group(2) == ' line comment'

        match = self.reg.match("""-- line comment
            , count(*)
            """)
        assert match is not None
        assert match.group(2) == ' line comment'

class LiteralPatternTest(unittest.TestCase):

    pattern = r"""
        (.*?)         # anything, followed by:
        (
         (?=--) # singleline comment
         |
         (?=\/\*) # multiline comment
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

    def test_escaped_newline(self):
        data = """
            select
                "string"
                , \\\n
                , column"""
        match = self.reg.match(data)
        assert match is not None
        print match.groups()
        assert match.group(1) == """
            select
                "string"
                , """
        (start, end) = match.span()
        assert start == 0
        assert data[end] == '\n'

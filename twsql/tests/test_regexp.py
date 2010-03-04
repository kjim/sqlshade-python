import unittest
import re

class RegexpPatternTest(unittest.TestCase):

    def test_control_comment_start_pattern(self):
        pattern = r"""
                /\*\#     # opening
                
                ([\w\.\:]+)   # keyword

                ((?:\s+:?\w+)*)  # text
                
                \s*     # more whitespace
                
                \*/   # closing
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
        pattern = r'/\*#(?:/|end)[\t ]*(\w+?)[\t ]*\*/'
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
        pattern = r"""
                /\*:    # opening
                
                (\w+?)  # keyword
                
                \*/     # closing
                
                (       # phantom
                  \'([^\\]|(\\.))*?\' # string literal
                  |
                  [^\s\n\r]+          # literal
                )
        """
        reg = re.compile(pattern, re.X)

        # string literal
        match = reg.match("/*:item*/'phantom string' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == "'phantom string'"
        match = reg.match("/*:item*/'truthly phrantom string/*this is not a comment*/' followed literal")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == "'truthly phrantom string/*this is not a comment*/'"
        match = reg.match(
            """/*:item*/'phantom string allowing multi-line text
            this line also phantom string
            ...
            '""")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == """'phantom string allowing multi-line text
            this line also phantom string
            ...
            '"""

        # number literal
        match = reg.match("/*:item*/1000 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '1000'
        match = reg.match("/*:item*/1000")
        assert match.group(2) == '1000'
        match = reg.match("/*:item*/1000.235 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '1000.235'
        match = reg.match("/*:item*/+1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '+1000.893'
        match = reg.match("/*:item*/-1000.893 and conditions ...")
        assert match is not None
        assert match.group(1) == 'item'
        assert match.group(2) == '-1000.893'
        match = reg.match("/*:item*/3.402823E+38")
        assert match.group(2) == '3.402823E+38'
        match = reg.match("/*:item*/2.802597E-45")
        assert match.group(2) == '2.802597E-45'
        match = reg.match("/*:item*/-2.802597E-45")
        assert match.group(2) == '-2.802597E-45'
        match = reg.match("/*:item*/-3.402823E+38")
        assert match.group(2) == '-3.402823E+38'

#         (start, end) = match.span()
#         assert start == 0
#         assert end == 9

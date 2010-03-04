import unittest
import re

class RegexpPatternTest(unittest.TestCase):

    def test_control_comment_start_pattern(self):
        pattern = r"""
                /\*\#     # opening control comment
                
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

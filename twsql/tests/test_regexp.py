import unittest
import re

class RegexpPatternTest(unittest.TestCase):

    def test_control_comment_start_pattern(self):
        pattern = r"""
                /\*\#     # opening control comment
                
                ([\w\.\:]+)   # keyword

                \s*     # whitespace
                
                ((?:\s+|:\w+|\w+)*)  # text
                
                \s*     # more whitespace
                
                \*/   # closing
                """
        reg = re.compile(pattern, re.I | re.S | re.X)
        match = reg.match('/*#for item in :items*/followed text...')
        assert match is not None
        assert match.group(1) == 'for'
        assert match.group(2) == 'item in :items'

        match = reg.match('/*#embed :embed_item*/followed text...')
        assert match is not None
        assert match.group(1) == 'embed'
        assert match.group(2) == ':embed_item'

        match = reg.match('/*#if :boolean_item*/')
        assert match is not None
        assert match.group(1) == 'if'
        assert match.group(2) == ':boolean_item'

# -*- coding: utf-8 -*-

"""provides the Lexer class for parsing template strings into parse trees."""

import re, codecs
from twsql import tree, exc

_regexp_cache = {}

should_be_end_char_rules = {
    '(': ')',
}

class Lexer(object):

    def __init__(self, text, filename=None, disable_unicode=False, input_encoding=None):
        self.text = text
        self.filename = filename
        self.template = tree.TemplateNode(self.filename)
        self.control_comment = []
        self.matched_lineno = 1
        self.matched_charpos = 0
        self.lineno = 1
        self.match_position = 0
        self.disable_unicode = disable_unicode
        self.encoding = input_encoding

    @property
    def exception_kwargs(self):
        return {'source': self.text, 'lineno': self.matched_lineno, 'pos': self.matched_charpos, 'filename': self.filename}

    def match(self, regexp, flags=None):
        """match the given regular expression string and flags to the current text position.
        
        if a match occurs, update the current text and line position."""
        mp = self.match_position
        try:
            reg = _regexp_cache[(regexp, flags)]
        except KeyError:
            if flags:
                reg = re.compile(regexp, flags)
            else:
                reg = re.compile(regexp)
            _regexp_cache[(regexp, flags)] = reg

        match = reg.match(self.text, self.match_position)
        if match:
            (start, end) = match.span()
            if end == start:
                self.match_position = end + 1
            else:
                self.match_position = end
            self.matched_lineno = self.lineno
            lines = re.findall(r"\n", self.text[mp:self.match_position])
            cp = mp - 1
            while (cp >= 0 and cp<self.textlength and self.text[cp] != '\n'):
                cp -=1
            self.matched_charpos = mp - cp
            self.lineno += len(lines)
            #print "MATCHED:", match.group(0), "LINE START:", self.matched_lineno, "LINE END:", self.lineno
        #print "MATCH:", regexp, "\n", self.text[mp : mp + 15], (match and "TRUE" or "FALSE")
        return match

    def append_node(self, nodecls, *args, **kwargs):
        kwargs.setdefault('source', self.text)
        kwargs.setdefault('lineno', self.matched_lineno)
        kwargs.setdefault('pos', self.matched_charpos)
        kwargs['filename'] = self.filename
        node = nodecls(*args, **kwargs)
        if len(self.control_comment):
            self.control_comment[-1].nodes.append(node)
        else:
            self.template.nodes.append(node)
        if isinstance(node, tree.ControlComment):
            if len(self.control_comment):
                node.parent = self.control_comment[-1]
            self.control_comment.append(node)

    def parse(self):
        if not isinstance(self.text, unicode) and self.text.startswith(codecs.BOM_UTF8):
            self.text = self.text[len(codecs.BOM_UTF8):]
            parsed_encoding = 'utf-8'
            me = self.match_encoding()
            if me is not None and me != 'utf-8':
                raise exc.CompileError("Found utf-8 BOM in file, with conflicting magic encoding comment of '%s'" % me, self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)
        else:
            parsed_encoding = self.match_encoding()
        if parsed_encoding:
            self.encoding = parsed_encoding
        if not self.disable_unicode and not isinstance(self.text, unicode):
            if self.encoding:
                try:
                    self.text = self.text.decode(self.encoding)
                except UnicodeDecodeError, e:
                    raise exc.CompileError("Unicode decode operation of encoding '%s' failed" % self.encoding, self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)
            else:
                try:
                    self.text = self.text.decode()
                except UnicodeDecodeError, e:
                    raise exc.CompileError("Could not read template using encoding of 'ascii'.  Did you forget a magic encoding comment?", self.text.decode('utf-8', 'ignore'), 0, 0, self.filename)

        self.textlength = len(self.text)

        while (True):
            if self.match_position > self.textlength:
                break

            if self.match_end():
                break
            if self.match_comment():
                continue
            if self.match_substitute_comment():
                continue
            if self.match_control_comment_start():
                continue
            if self.match_control_comment_end():
                continue
            if self.match_literal():
                continue

            if self.match_position > self.textlength:
                break
            raise exc.CompileError("assertion failed")

    def match_encoding(self):
        match = self.match(r'#.*coding[:=]\s*([-\w.]+).*\r?\n')
        if match:
            return match.group(1)
        else:
            return None

    def match_substitute_comment(self):
        match = self.match(r"""/\*:(\w+?)\*/(?=[\w'(+-])""")
        if match:
            (ident, fake_value_prefix) = (match.group(1), self.text[self.match_position])
            if fake_value_prefix == "'":
                m = self.match(r"(\'(?:[^\\]|(\\.))*?\')")
                if not m:
                    raise exc.SyntaxError("Invalid string literal", **self.exception_kwargs)
                text = m.group(1)
            else:
                text = self.parse_sqlliteral_end()
            self.append_node(tree.SubstituteComment, ident, text)
            return True
        else:
            return False

    def parse_sqlliteral_end(self):
        start = self.match_position
        text = self.text[start:]
        should_end_char = should_be_end_char_rules.get(text[0], None)
        end = self.parse_until_end_of_sqlword(text, should_end_char)
        if end != -1:
            end += start
            if end == start:
                self.match_position = end + 1
            else:
                self.match_position = end
            text = self.text[start:end]
            self.matched_lineno = self.lineno
            lines = re.findall(r"\n", text)
            cp = start - 1
            while (0 <= cp < self.textlength and self.text[cp] != '\n'):
                cp -= 1
            self.matched_charpos = start - cp
            self.lineno += len(lines)
            return text
        else:
            raise exc.SyntaxError("Invalid fake value literal", **self.exception_kwargs)

    @staticmethod
    def parse_until_end_of_sqlword(text, should_be_end_char=None):
        if not text:
            return -1
        (stack, string, escape) = (0, False, False)
        if should_be_end_char is not None:
            end = should_be_end_char
        else:
            end = text[-1]
        invalid_endset = set([' ', '\n', '\r'])
        for i, c in enumerate(text):
            if string is False:
                if c == '(':
                    stack += 1
                elif  c == ')':
                    stack -= 1
            if escape is False:
                if c == "'":
                    string = not string
                elif c == "\\":
                    escape = True
            else:
                escape = False
            if stack == 0 and c == end and c not in invalid_endset:
                return i + 1
        else:
            return -1

    def match_control_comment_start(self):
        match = self.match(r'''
            /\*\#(?!\/|end)  # opening
            
            ([\w\.\:]+)      # keyword
            
            ((?:\s+:?\w+)*)  # text
            
            \s*              # more whitespace
            
            \*/              # closing
            ''', re.S | re.X)

        if match:
            (keyword, text) = (match.group(1), match.group(2))
            self.keyword = keyword
            self.append_node(tree.ControlComment, keyword, text)
            return True
        else:
            return False

    def match_control_comment_end(self):
        match = self.match(r"""/\*#(?:/|end)[\t ]*(\w+?)[\t ]*\*/""")
        if match:
            if not len(self.control_comment):
                raise exc.SyntaxError("Closing control without opening control: /*#/%s*/" % match.group(1), **self.exception_kwargs)
            elif self.control_comment[-1].keyword != match.group(1):
                raise exc.SyntaxError("Closing control </%%%s> does not match control: <%%%s>" % (match.group(1), self.control_comment[-1].keyword), **self.exception_kwargs)
            self.control_comment.pop()
            return True
        else:
            return False

    def match_end(self):
        match = self.match(r'\Z', re.S)
        if match:
            string = match.group()
            if string:
                return string
            else:
                return True
        else:
            return False

    def match_literal(self):
        match = self.match(r"""
            (.*?)   # anything, followed by:
            (
             (?=--) # singleline comment
             |
             (?=\/\*)  # multiline comment
             |
             (\\\r?\n)  # an escaped newline - throw away
             |
             \Z     # end of string
            )""", re.X | re.S)

        if match:
            text = match.group(1)
            self.append_node(tree.Literal, text)
            return True
        else:
            return False

    def match_comment(self):
        """matches the multiline version of a comment"""
        match = self.match(r"""
            (?:
             /\*([^:#].*?)\*/
             |
             --([^\n\r]*)
            )
            """, re.S | re.X)
        if match:
            is_multiline = match.group(1) is not None
            text = match.group(1) if is_multiline else match.group(2)
            self.append_node(tree.Comment, text, is_multiline)
        else:
            return False

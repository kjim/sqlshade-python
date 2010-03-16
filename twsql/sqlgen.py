from twsql import exc, util
from twsql.lexer import Lexer

def compile(node, filename, data,
            source_encoding=None,
            generate_unicode=True,
            strict=True):
    buf = util.FastEncodingBuffer()
    printer = QueryPrinter(buf)
    CompileSQL(
        printer,
        CompileContext(data, strict=strict),
        node
    )
    return printer.freeze()

class CompileContext(object):

    def __init__(self, data, **env):
        self._data = data
        self._env = env

        self._mode = 'strict' if env['strict'] else 'nostrict'

    def update(self, **kwargs):
        self._data.update(**kwargs)

    @property
    def data(self):
        return self._data

    @property
    def env(self):
        return self._env

    @property
    def mode(self):
        return self._mode

class QueryPrinter(object):

    def __init__(self, buf):
        self._sql_fragments = buf
        self._bound_variables = []
        self.compiled_sql = None

    def write(self, fragment):
        self._sql_fragments.write(fragment)

    def bind(self, variable):
        self._bound_variables.append(variable)

    def freeze(self):
        return self._sql_fragments.getvalue(), self._bound_variables


ITERABLE_DATA_TYPES = (list, tuple, dict)

def _resolve_value_in_context_data(ident, data):
    ident_struct = ident.split('.')
    if '' in ident_struct:
        raise KeyError(ident)
    tmp = data
    for e in ident_struct:
        tmp = tmp[e]
    return tmp

class CompileSQL(object):

    def __init__(self, printer, context, node):
        self.printer = printer
        self.node = node

        # begin compilation
        for n in self.node.get_children():
            n.accept_visitor(self, context)

    def visitLiteral(self, node, context):
        self.printer.write(node.text)
    visitLiteral_strict = visitLiteral
    visitLiteral_nostrict = visitLiteral
    del visitLiteral

    def visitSubstituteComment_strict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_substitute_comment(node, variable)

    def visitSubstituteComment_nostrict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            self.printer.write('/*:%(ident)s*/%(text)s' % dict(ident=node.ident, text=node.text))
        else:
            self.write_substitute_comment(node, variable)

    def write_substitute_comment(self, node, variable):
        if type(variable) in ITERABLE_DATA_TYPES:
            if not len(variable):
                raise exc.RuntimeError("Binding data should not be empty.")
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_embed(node, context)

    def visitEmbed_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_embed(node, context)

    def write_embed(self, node, context):
        self.printer.write(context.data[node.ident])

    def write_control_comment(self, node, context):
        self.printer.write('/*#%(keyword)s %(text)s*/' % dict(keyword=node.keyword, text=node.text.strip()))
        for n in node.get_children():
            n.accept_visitor(self, context)
        self.printer.write('/*#end%s*/' % node.keyword)

    def visitEval_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_eval(node, context)

    def visitEval_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_eval(node, context)

    def write_eval(self, node, context):
        template_text = context.data[node.ident]
        sub_lexer = Lexer(template_text)
        sub_node = sub_lexer.parse()
        inner_query, inner_bound_variables = compile(sub_node, '<eval template text>', context.data)
        self.printer.write(inner_query)
        for variable in inner_bound_variables:
            self.printer.bind(variable)

    def visitIf_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_if(node, context)

    def visitIf_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_if(node, context)

    def write_if(self, node, context):
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_for(node, context)

    def visitFor_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_for(node, context)

    def write_for(self, node, context):
        alias = node.item
        for_block_context = CompileContext(context.data, strict=context.env['strict'])
        for iterdata in context.data[node.ident]:
            for_block_context.update(**{str(alias): iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)

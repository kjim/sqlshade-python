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

    def update(self, **kwargs):
        self._data.update(**kwargs)

    @property
    def data(self):
        return self._data

    @property
    def env(self):
        return self._env

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

    def visitSubstituteComment(self, node, context):
        data = context.data
        try:
            variable = _resolve_value_in_context_data(node.ident, data)
            variable_type = type(variable)
        except KeyError, e:
            if context.env['strict']:
                raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
            else:
                self.printer.write('/*:%(ident)s*/%(text)s' % dict(ident=node.ident, text=node.text))
                return
        if variable_type in ITERABLE_DATA_TYPES:
            if not len(variable):
                raise exc.RuntimeError("Binding data should not be empty.")
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed(self, node, context):
        if node.ident not in context.data:
            if context.env['strict']:
                raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
            else:
                self.printer.write('/*#embed :%s*/' % node.ident)
                for n in node.get_children():
                    n.accept_visitor(self, context)
                self.printer.write('/*#endembed*/')
                return
        self.printer.write(context.data[node.ident])

    def visitEval(self, node, context):
        if node.ident not in context.data:
            if context.env['strict']:
                raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
            else:
                self.printer.write('/*#eval :%s*/' % node.ident)
                for n in node.get_children():
                    n.accept_visitor(self, context)
                self.printer.write('/*#endeval*/')
                return
        template_text = context.data[node.ident]
        sub_lexer = Lexer(template_text)
        sub_node = sub_lexer.parse()
        inner_query, inner_bound_variables = compile(sub_node, '<eval template text>', context.data)
        self.printer.write(inner_query)
        for variable in inner_bound_variables:
            self.printer.bind(variable)

    def visitIf(self, node, context):
        if node.ident not in context.data:
            if context.env['strict']:
                raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
            else:
                self.printer.write('/*#if :%s*/' % node.ident)
                for n in node.get_children():
                    n.accept_visitor(self, context)
                self.printer.write('/*#endif*/')
                return
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor(self, node, context):
        if node.ident not in context.data:
            if context.env['strict']:
                raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
            else:
                self.printer.write('/*#for %s in :%s*/' % (node.item, node.ident))
                for n in node.get_children():
                    n.accept_visitor(self, context)
                self.printer.write('/*#endfor*/')
                return
        alias = node.item
        for_block_context = CompileContext(context.data)
        for iterdata in context.data[node.ident]:
            for_block_context.update(**{str(alias): iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)

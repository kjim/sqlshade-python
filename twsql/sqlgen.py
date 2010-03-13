from twsql import exc, util

def compile(node, filename, data,
            source_encoding=None,
            generate_unicode=True):
    buf = util.FastEncodingBuffer()
    printer = QueryPrinter(buf)
    context = CompileContext(data)
    CompileSQL(printer, context, node)
    printer.freeze()
    return printer

class CompileContext(object):

    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data

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
        self.compiled_sql = self._sql_fragments.getvalue()

    @property
    def bound_variables(self):
        return self._bound_variables

    @property
    def sql(self, sep=''):
        if self.compiled_sql is None:
            raise exc.RuntimeError('object was not freezed.')
        return self.compiled_sql

class CompileSQL(object):

    def __init__(self, printer, context, node):
        self.printer = printer
        self.node = node

        # begin compilation
        for n in self.node.get_children():
            n.accept_visitor(self, context)

    def visitLiteral(self, node, context):
        self.printer.write(node.text)

    def _resolve_context_value(self, ident_struct, data):
        tmp = data
        for e in ident_struct:
            tmp = tmp[e]
        return tmp

    def visitSubstituteComment(self, node, context):
        data = context.data
        ident_struct = node.ident.split('.')
        if '' in ident_struct:
            raise exc.RuntimeError("Invalid key: %s" % node.ident)
        try:
            variable = self._resolve_context_value(ident_struct, data)
        except KeyError, e:
            raise exc.RuntimeError("Has no '%s' variable" % node.ident)
        if type(variable) in (list, tuple):
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        self.printer.write(context.data[node.ident])

    def visitIf(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        alias = node.item
        for iterdata in context.data[node.ident]:
            for_block_context = CompileContext({alias: iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)

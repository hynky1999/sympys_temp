import sympy
from sympy.logic.boolalg import BooleanAtom
import antlr4
import re
from antlr4.error.ErrorListener import ErrorListener

from .gen.PSParser import PSParser
from .gen.PSLexer import PSLexer
from .gen.PSListener import PSListener

from sympy.printing.str import StrPrinter

fraction_plus_re = r'(-?)\s*(\d+\.?\d*)(\s*(\\frac{.+}{.+})|\s+(\(?\d+\)?/\(?\d+\)?))'

def process_sympy(sympy):
    sympy = re.sub(fraction_plus_re,lambda x: '{}({}+{})'.format(x.group(1),x.group(2),x.group(3)),sympy)
    if re.search(r'\d\s+\d',sympy):
        raise ValueError()
    matherror = MathErrorListener(sympy)

    stream = antlr4.InputStream(sympy)
    lex    = PSLexer(stream)
    lex.removeErrorListeners()
    lex.addErrorListener(matherror)

    tokens = antlr4.CommonTokenStream(lex)
    parser = PSParser(tokens)

    # remove default console error listener
    parser.removeErrorListeners()
    parser.addErrorListener(matherror)


    relation = parser.math().relation()
    expr = convert_relation(relation)

    return expr

def process_set(sympy):

    stream = antlr4.InputStream(sympy)
    lex    = PSLexer(stream)

    tokens = antlr4.CommonTokenStream(lex)
    parser = PSParser(tokens)

    struct_f = parser.struct_form()
    expr = convert_struct_form(struct_f)

    return expr

class MathErrorListener(ErrorListener):
    def __init__(self, src):
        super(ErrorListener, self).__init__()
        self.src = src

    def syntaxError(self, recog, symbol, line, col, msg, e):
        fmt = "%s\n%s\n%s"
        marker = "~" * col + "^"
        
        if msg.startswith("missing"):
            err = fmt % (msg, self.src, marker)
        elif msg.startswith("no viable"):
            err = fmt % ("I expected something else here", self.src, marker)
        elif msg.startswith("mismatched"):
            names = PSParser.literalNames
            expected = [names[i] for i in e.getExpectedTokens() if i < len(names)]
            if expected < 10:
                expected = " ".join(expected)
                err = (fmt % ("I expected one of these: " + expected,
                    self.src, marker))
            else:
                err = (fmt % ("I expected something else here", self.src, marker))
        else:
            err = fmt % ("I don't understand this", self.src, marker)
        raise Exception(err)

def convert_struct_form(form):
    if len(form.value()) == 1:
        return convert_value(form.value()[0])
    l = []
    for x in form.value():
        l.append(convert_value(x))
    l = ['any'] + l + ['any']
    return l

def convert_value(value):
    if value.list_form():
        return convert_list_form(value.list_form())
    elif value.set_form_2():
        return convert_set_form(value.set_form_2())
    elif value.set_form():
        return convert_set_form(value.set_form())
    elif value.mixed_form():
        return convert_mixed_form(value.mixed_form())
    elif value.relation():
        return convert_relation(value.relation())

def convert_list_form(form):
    l = []
    for x in form.value():
        l.append(convert_value(x))
    l = ['list'] + l + ['list']
    return l

def convert_set_form(form):
    l = []
    for x in form.value():
        l.append(convert_value(x))
    l = ['set'] + sorted(l,key=lambda x: str(x)) + ['set']
    return l

def convert_mixed_form(form):
    l = []
    for x in form.value():
        l.append(convert_value(x))
    l_p = form.left_p().getText()
    r_p = form.right_p().getText()
    l = [l_p] + sorted(l) + [r_p]
    return l

def convert_relation(rel):
    if rel.expr():
        return convert_expr(rel.expr())

    lh = convert_relation(rel.relation(0))
    rh = convert_relation(rel.relation(1))
    if rel.LT():
        return sympy.StrictLessThan(lh, rh,evaluate=False)
    elif rel.LTE():
        return sympy.LessThan(lh, rh,evaluate=False)
    elif rel.GT():
        return sympy.StrictGreaterThan(lh, rh,evaluate=False) 
    elif rel.GTE():
        return sympy.GreaterThan(lh, rh,evaluate=False)
    elif rel.EQUAL():
        return sympy.Eq(lh, rh,evaluate=False)

def convert_expr(expr):
    if expr.additive():
        return convert_add(expr.additive())
    elif expr.set_notation_sub():
        return handle_set_notation(expr)
    elif expr.interval():
        return handle_interval(expr.interval())

def convert_add(add):
    if add.ADD():
       lh = convert_add(add.additive(0))
       rh = convert_add(add.additive(1))
       return sympy.Add(lh, rh, evaluate=False)
    elif add.SUB():
        lh = convert_add(add.additive(0))
        rh = convert_add(add.additive(1))
        return sympy.Add(lh, -1 * rh, evaluate=False)
    else:
        return convert_mp(add.mp())

def convert_mp(mp):
    if hasattr(mp, 'mp'):
        mp_left = mp.mp(0)
        mp_right = mp.mp(1)
    else:
        mp_left = mp.mp_nofunc(0)
        mp_right = mp.mp_nofunc(1)

    if mp.MUL() or mp.CMD_TIMES() or mp.CMD_CDOT():
        lh = convert_mp(mp_left)
        rh = convert_mp(mp_right)
        return sympy.Mul(lh, rh, evaluate=False)
    elif mp.DIV() or mp.CMD_DIV() or mp.COLON():
        lh = convert_mp(mp_left)
        rh = convert_mp(mp_right)
        return sympy.Mul(lh, sympy.Pow(rh, -1, evaluate=False), evaluate=False)
    else:
        if hasattr(mp, 'unary'):
            return convert_unary(mp.unary())
        else:
            return convert_unary(mp.unary_nofunc())

def convert_unary(unary):
    if hasattr(unary, 'unary'):
        nested_unary = unary.unary()
    else:
        nested_unary = unary.unary_nofunc()
    if hasattr(unary, 'postfix_nofunc'):
        first = unary.postfix()
        tail = unary.postfix_nofunc()
        postfix = [first] + tail
    else:
        postfix = unary.postfix()

    if unary.ADD():
        return convert_unary(nested_unary)
    elif unary.SUB():
        return sympy.Mul(-1, convert_unary(nested_unary), evaluate=False)
    elif postfix:
        return convert_postfix_list(postfix)

def convert_postfix_list(arr, i=0):
    if i >= len(arr):
        raise Exception("Index out of bounds")

    res = convert_postfix(arr[i])
    if isinstance(res, sympy.Expr) or isinstance(res, sympy.Matrix):
        if i == len(arr) - 1:
            return res # nothing to multiply by
        else:
            if i > 0:
                left = convert_postfix(arr[i - 1])
                right = convert_postfix(arr[i + 1])
                if isinstance(left, sympy.Expr) and isinstance(right, sympy.Expr):
                    left_syms  = convert_postfix(arr[i - 1]).atoms(sympy.Symbol)
                    right_syms = convert_postfix(arr[i + 1]).atoms(sympy.Symbol)
                    # if the left and right sides contain no variables and the
                    # symbol in between is 'x', treat as multiplication.
                    if len(left_syms) == 0 and len(right_syms) == 0 and str(res) == "x":
                        return convert_postfix_list(arr, i + 1)
            # multiply by next
            return sympy.Mul(res, convert_postfix_list(arr, i + 1), evaluate=False)
    else: # must be derivative
        wrt = res[0]
        if i == len(arr) - 1:
            raise Exception("Expected expression for derivative")
        else:
            expr = convert_postfix_list(arr, i + 1)
            return sympy.Derivative(expr, wrt).doit()

def do_subs(expr, at):
    if at.expr():
        at_expr = convert_expr(at.expr())
        syms = at_expr.atoms(sympy.Symbol)
        if len(syms) == 0:
            return expr
        elif len(syms) > 0:
            sym = next(iter(syms))
            return expr.subs(sym, at_expr)
    elif at.equality():
        lh = convert_expr(at.equality().expr(0))
        rh = convert_expr(at.equality().expr(1))
        return expr.subs(lh, rh)

def convert_postfix(postfix):
    if hasattr(postfix, 'exp'):
        exp_nested = postfix.exp()
    else:
        exp_nested = postfix.exp_nofunc()
    exp = convert_exp(exp_nested)
    for op in postfix.postfix_op():
        if op.BANG():
            if isinstance(exp, list):
                raise Exception("Cannot apply postfix to derivative")
            exp = sympy.factorial(exp, evaluate=False)
        elif op.eval_at():
            ev = op.eval_at()
            at_b = None
            at_a = None
            if ev.eval_at_sup():
                at_b = do_subs(exp, ev.eval_at_sup()) 
            if ev.eval_at_sub():
                at_a = do_subs(exp, ev.eval_at_sub())
            if at_b != None and at_a != None:
                exp = sympy.Add(at_b, -1 * at_a, evaluate=False)
            elif at_b != None:
                exp = at_b
            elif at_a != None:
                exp = at_a
    return exp

def convert_exp(exp):
    if hasattr(exp, 'exp'):
        exp_nested = exp.exp()
    else:
        exp_nested = exp.exp_nofunc()
    if exp_nested:
        base = convert_exp(exp_nested)
        if isinstance(base, list):
            raise Exception("Cannot raise derivative to power")
        if exp.atom():
            exponent = convert_atom(exp.atom())
        elif exp.expr():
            exponent = convert_expr(exp.expr())
        return sympy.Pow(base, exponent, evaluate=False)
    else:
        if hasattr(exp, 'comp'):
            return convert_comp(exp.comp())
        else:
            return convert_comp(exp.comp_nofunc())

def convert_comp(comp):
    if comp.group():
        return convert_expr(comp.group().expr())
    elif comp.abs_group():
        return sympy.Abs(convert_expr(comp.abs_group().expr()), evaluate=False)
    elif comp.atom():
        return convert_atom(comp.atom())
    elif comp.frac():
        return convert_frac(comp.frac())
    elif comp.func():
        return convert_func(comp.func())

def convert_atom(atom):
    if atom.LETTER():
        subscriptName = ''
        if atom.subexpr():
            subscript = None
            if atom.subexpr().expr():           # subscript is expr
                subscript = convert_expr(atom.subexpr().expr())
            else:                               # subscript is atom
                subscript = convert_atom(atom.subexpr().atom())
            subscriptName = '_{' + StrPrinter().doprint(subscript) + '}'
        if atom.LETTER().getText() + subscriptName == 'E':
            return sympy.E
        return sympy.Symbol(atom.LETTER().getText() + subscriptName)
    elif atom.SYMBOL():
        s = atom.SYMBOL().getText()[1:]
        if s == "infty":
            return sympy.oo
        elif s == r"%":
            return sympy.Rational(1,100)
        elif s == 'pi':
            return sympy.pi
        else:
            if atom.subexpr():
                subscript = None
                if atom.subexpr().expr():           # subscript is expr
                    subscript = convert_expr(atom.subexpr().expr())
                else:                               # subscript is atom
                    subscript = convert_atom(atom.subexpr().atom())
                subscriptName = StrPrinter().doprint(subscript)
                s += '_{' + subscriptName + '}'
            return sympy.Symbol(s)
    elif atom.NUMBER():
        s = atom.NUMBER().getText().replace(",", "")
        return sympy.Number(s)
    elif atom.DIFFERENTIAL():
        var = get_differential_var(atom.DIFFERENTIAL())
        return sympy.Symbol('d' + var.name)
    elif atom.mathit():
        text = rule2text(atom.mathit().mathit_text())
        return sympy.Symbol(text)

def rule2text(ctx):
    stream = ctx.start.getInputStream()
    # starting index of starting token
    startIdx = ctx.start.start 
    # stopping index of stopping token
    stopIdx = ctx.stop.stop

    return stream.getText(startIdx, stopIdx)

def convert_frac(frac):
    diff_op = False
    partial_op = False
    lower_itv = frac.lower.getSourceInterval()
    lower_itv_len = lower_itv[1] - lower_itv[0] + 1
    if (frac.lower.start == frac.lower.stop and
        frac.lower.start.type == PSLexer.DIFFERENTIAL):
        wrt = get_differential_var_str(frac.lower.start.text)
        diff_op = True
    elif (lower_itv_len == 2 and
        frac.lower.start.type == PSLexer.SYMBOL and
        frac.lower.start.text == '\\partial' and
        (frac.lower.stop.type == PSLexer.LETTER or frac.lower.stop.type == PSLexer.SYMBOL)):
        partial_op = True
        wrt = frac.lower.stop.text
        if frac.lower.stop.type == PSLexer.SYMBOL:
            wrt = wrt[1:]

    if diff_op or partial_op:
        wrt = sympy.Symbol(wrt)
        if (diff_op and frac.upper.start == frac.upper.stop and
            frac.upper.start.type == PSLexer.LETTER and
            frac.upper.start.text == 'd'):
            return [wrt]
        elif (partial_op and frac.upper.start == frac.upper.stop and
            frac.upper.start.type == PSLexer.SYMBOL and
            frac.upper.start.text == '\\partial'):
            return [wrt]
        upper_text = rule2text(frac.upper)

        expr_top = None
        if diff_op and upper_text.startswith('d'):
            expr_top = process_sympy(upper_text[1:])
        elif partial_op and frac.upper.start.text == '\\partial':
            expr_top = process_sympy(upper_text[len('\\partial'):])
        if expr_top:
            return sympy.Derivative(expr_top, wrt).doit()

    expr_top = convert_expr(frac.upper)
    expr_bot = convert_expr(frac.lower)
    return sympy.Mul(expr_top, sympy.Pow(expr_bot, -1, evaluate=False), evaluate=False)

def convert_func(func):
    if func.func_normal():
        if func.L_PAREN(): # function called with parenthesis
            arg = convert_func_arg(func.func_arg())
        else:
            arg = convert_func_arg(func.func_arg_noparens())
            
        name = func.func_normal().start.text[1:]
        # change arc<trig> -> a<trig>
        if name in ["arcsin", "arccos", "arctan", "arccsc", "arcsec",
        "arccot"]:
            name = "a" + name[3:]
            expr = getattr(sympy.functions, name)(arg, evaluate=False)
        if name in ["arsinh", "arcosh", "artanh"]:
            name = "a" + name[2:]
            expr = getattr(sympy.functions, name)(arg, evaluate=False)
            
        if (name=="log" or name=="ln"):
            if func.subexpr():
                base = convert_expr(func.subexpr().expr())
            elif name == "log":
                base = 10
            elif name == "ln":
                base = sympy.E
            expr = sympy.log(arg, base, evaluate=False)
        if (name=="exp"):
            expr = getattr(sympy.functions, name)(arg, evaluate=False)
        func_pow = None
        should_pow = True
        if func.supexpr():
            if func.supexpr().expr():
                func_pow = convert_expr(func.supexpr().expr())
            else:
                func_pow = convert_atom(func.supexpr().atom())

        if name in ["sin", "cos", "tan", "csc", "sec", "cot", "sinh", "cosh", "tanh"]:
                if func_pow == -1:
                    name = "a" + name
                    should_pow = False
                expr = getattr(sympy.functions, name)(arg, evaluate=False)


        if func_pow and should_pow:
            expr = sympy.Pow(expr, func_pow, evaluate=False)

        return expr
    elif func.LETTER() or func.SYMBOL():
        if func.LETTER(): 
            fname = func.LETTER().getText()
        elif func.SYMBOL():
            fname = func.SYMBOL().getText()[1:]
        fname = str(fname) # can't be unicode
        if func.subexpr():
            subscript = None
            if func.subexpr().expr():                   # subscript is expr
                subscript = convert_expr(func.subexpr().expr())
            else:                                       # subscript is atom
                subscript = convert_atom(func.subexpr().atom())
            subscriptName = StrPrinter().doprint(subscript)
            fname += '_{' + subscriptName + '}'
        input_args = func.args()
        output_args = []
        while input_args.args():                        # handle multiple arguments to function
            output_args.append(convert_expr(input_args.expr()))
            input_args = input_args.args()
        output_args.append(convert_expr(input_args.expr()))
        return sympy.Function(fname)(*output_args)
    elif func.FUNC_INT():
        return handle_integral(func)
    elif func.FUNC_SQRT():
        expr = convert_expr(func.base)
        if func.root:
            r = convert_expr(func.root)
            return sympy.root(expr, r,evaluate=False)
        else:
            return sympy.root(expr,2,evaluate=False)
    elif func.FUNC_SUM():
        return handle_sum_or_prod(func, "summation")
    elif func.FUNC_PROD():
        return handle_sum_or_prod(func, "product")
    elif func.FUNC_LIM():
        return handle_limit(func)
    elif func.FUNC_MATRIX_START():
        return handle_matrix(func)

def convert_func_arg(arg):
    if hasattr(arg, 'expr'):
        return convert_expr(arg.expr())
    else:
        return convert_mp(arg.mp_nofunc())

def handle_matrix(matrix):
    matrix = matrix.matrix()
    m_list = []
    for row in matrix.matrix_row():
        m_list.append(convert_matrix_row(row))
    return sympy.Matrix(m_list)

def convert_matrix_row(row):
    row_list = []
    for expr in row.expr():
        row_list.append(convert_expr(expr))
    return row_list

def handle_set_notation(func):
    sub = func.set_notation_sub()
    if sub.LETTER():
        var = sympy.Symbol(sub.LETTER().getText())
    elif sub.SYMBOL():
        var = sympy.Symbol(sub.SYMBOL().getText()[1:])
    else:
        var = sympy.Symbol('x')
    rel = convert_relation(sub.relation())
    sol = sympy.S.Reals
    while isinstance(rel,sympy.relational.Relational):
        future_rel = rel.lhs
        if isinstance(rel.lhs,sympy.relational.Relational):
            future_rel = rel.lhs
            rel = type(rel)(rel.lhs.rhs,rel.rhs)

        if not isinstance(rel,BooleanAtom):
            sol_tmp = sympy.solveset(rel,var,sympy.S.Reals)
            sol = sympy.Intersection(sol,sol_tmp)
        rel = future_rel
    return sol

def handle_interval(interval):
    left_bool = False
    right_bool = False
    if interval.L_PAREN():
        left_bool = True
    if interval.R_PAREN():
        right_bool = True
    left_expr = convert_expr(interval.expr(0))
    right_expr = convert_expr(interval.expr(1))
    return sympy.Interval(left_expr,right_expr,left_bool,right_bool)
    
def handle_integral(func):
    if func.additive():
        integrand = convert_add(func.additive())
    elif func.frac():
        integrand = convert_frac(func.frac())
    else:
        integrand = 1

    int_var = None
    if func.DIFFERENTIAL():
        int_var = get_differential_var(func.DIFFERENTIAL())
    else:
        for sym in integrand.atoms(sympy.Symbol):
            s = str(sym)
            if len(s) > 1 and s[0] == 'd':
                if s[1] == '\\':
                    int_var = sympy.Symbol(s[2:])
                else:
                    int_var = sympy.Symbol(s[1:])
                int_sym = sym
        if int_var:
            integrand = integrand.subs(int_sym, 1)
        else:
            # Assume dx by default
            int_var = sympy.Symbol('x')

    if func.subexpr():
        if func.subexpr().atom():
            lower = convert_atom(func.subexpr().atom())
        else:
            lower = convert_expr(func.subexpr().expr())
        if func.supexpr().atom():
            upper = convert_atom(func.supexpr().atom())
        else:
            upper = convert_expr(func.supexpr().expr())
        return sympy.Integral(integrand, (int_var, lower, upper)).doit()
    else:
        return sympy.Integral(integrand, int_var).doit()

def handle_sum_or_prod(func, name):
    val      = convert_mp(func.mp())
    iter_var = convert_expr(func.subeq().equality().expr(0))
    start    = convert_expr(func.subeq().equality().expr(1))
    if func.supexpr().expr(): # ^{expr}
        end = convert_expr(func.supexpr().expr())
    else: # ^atom
        end = convert_atom(func.supexpr().atom())
        

    if name == "summation":
        return sympy.Sum(val, (iter_var, start, end)).doit()
    elif name == "product":
        return sympy.Product(val, (iter_var, start, end)).doit()

def handle_limit(func):
    sub = func.limit_sub()
    if sub.LETTER():
        var = sympy.Symbol(sub.LETTER().getText())
    elif sub.SYMBOL():
        var = sympy.Symbol(sub.SYMBOL().getText()[1:])
    else:
        var = sympy.Symbol('x')
    if sub.SUB():
        direction = "-"
    else:
        direction = "+"
    approaching = convert_expr(sub.expr())
    content     = convert_mp(func.mp())
    
    return sympy.Limit(content, var, approaching, direction).doit()

def get_differential_var(d):
    text = get_differential_var_str(d.getText())
    return sympy.Symbol(text)

def get_differential_var_str(text):
    for i in range(1, len(text)):
        c = text[i]
        if not (c == " " or c == "\r" or c == "\n" or c == "\t"):
            idx = i
            break
    text = text[idx:]
    if text[0] == "\\":
        text = text[1:]
    return text

def test_sympy():
    print(process_sympy("e^{(45 + 2)}"))
    print(process_sympy("e + 5"))
    print(process_sympy("5 + e"))
    print(process_sympy("e"))
    print(process_sympy("\\frac{dx}{dy} \\int y x^2 dy"))
    print(process_sympy("\\frac{dx}{dy} 5"))
    print(process_sympy("\\frac{d}{dx} \\int x^2 dx"))
    print(process_sympy("\\frac{dx}{dy} \\int x^2 dx"))
    print(process_sympy("\\frac{d}{dy} x^2 + x y = 0"))
    print(process_sympy("\\frac{d}{dy} x^2 + x y = 2"))
    print(process_sympy("\\frac{d x^3}{dy}"))
    print(process_sympy("\\frac{d x^3}{dy} + x^3"))
    print(process_sympy("\\int^{5x}_{2} x^2 dy"))
    print(process_sympy("\\int_{5x}^{2} x^2 dx"))
    print(process_sympy("\\int x^2 dx"))
    print(process_sympy("2 4 5 - 2 3 1"))

if __name__ == "__main__":
    test_sympy()

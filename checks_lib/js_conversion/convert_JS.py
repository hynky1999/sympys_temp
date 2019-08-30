from sympy import (expand,simplify,symbols)
from sympy.printing.jscode import JavascriptCodePrinter
from sympy.printing.codeprinter import CodePrinter
from sympy.printing.precedence import precedence, PRECEDENCE
from sympy.logic.boolalg import BooleanAtom
from sympy.core.relational import Relational
from sympy import S, Eq
from checks_lib.utils.graph_utils import formatEquation
from checks_lib.utils.test_utils import result
from checks_lib.testing_func.test_minor import string_match
from checks_lib.regexes import JS_support

known_functions = {
    'Abs': 'abs',
    'acos': 'acos',
    'acosh': 'acosh',
    'asin': 'asin',
    'asinh': 'asinh',
    'atan': 'atan',
    'atan2': 'atan2',
    'atanh': 'atanh',
    'ceiling': 'ceil',
    'cos': 'cos',
    'cosh': 'cosh',
    'exp': 'exp',
    'floor': 'floor',
    'log': 'log',
    'Max': 'max',
    'Min': 'min',
    'sign': 'sign',
    'sin': 'sin',
    'sinh': 'sinh',
    'tan': 'tan',
    'tanh': 'tanh',
}

class JavascriptCodePrinterMod(JavascriptCodePrinter):
    """"A Printer to convert python expressions to strings of javascript code
    """

    def __init__(self, settings={}):
        CodePrinter.__init__(self, settings)
        self.known_functions = dict(known_functions)
        userfuncs = settings.get('user_functions', {})
        self.known_functions.update(userfuncs)

    def _print_Pow(self, expr):
        PREC = precedence(expr)
        if expr.exp == -1:
            return '1/%s' % (self.parenthesize(expr.base, PREC))
        elif expr.exp == 0.5:
            return 'sqrt(%s)' % self._print(expr.base)
        elif expr.exp == S(1)/3:
            return 'cbrt(%s)' % self._print(expr.base)
        else:
            return 'pow(%s, %s)' % (self._print(expr.base),
                                 self._print(expr.exp))

    def _print_Exp1(self, expr):
        return "exp(1)"

    def _print_Pi(self, expr):
        return 'PI'

    def _print_Infinity(self, expr):
        return 'POSITIVE_INFINITY'

    def _print_NegativeInfinity(self, expr):
        return 'NEGATIVE_INFINITY'

def formatEquationJS(eq):
        eq_l = JavascriptCodePrinterMod(
                {'user_functions':known_functions}).doprint(
                    eq.lhs-eq.rhs,None)

        if JS_support.search(eq_l):
            raise ValueError('Function not supported')

        rel_op = '=' if eq.rel_op == '==' else eq.rel_op
        eq_str = '{} {} {}'.format(eq_l,rel_op,'0')
        eq_str = eq_str.replace(' ','')
        return eq_str

def convert_JS(input_latex, expected_latex=None, options={}):
    x,y = symbols('x y')
    try:
        eq = formatEquation(input_latex,evaluate=True)
        if not isinstance(eq,Relational):
            if isinstance(eq,BooleanAtom):
                eq = formatEquation(input_latex,evaluate=False)
            else:
                eq = Eq(eq,0,evaluate=False)
        if not eq.free_symbols.issubset([x,y]):
            raise ValueError('Free Symbols')
        eq1 = formatEquationJS(eq)
        eq2 = formatEquationJS(eq.reversed)
        options_temp = {'ignoreLeadingAndTrailingSpaces':True,
                        'treatMultipleSpacesAsOne':True}
        expected_latex = expected_latex.replace(' ','')
        if (string_match(eq1,expected_latex,options_temp) == 'true'
            or string_match(eq2,expected_latex,options_temp) == 'true'):
            return result(True)
        else:
            return result(False)
        
    except:
        return r'Conversion_Error'

def Latex2JS(input_latex, expected_latex=None, options={}):
    x,y = symbols('x y')
    eq = formatEquation(input_latex,evaluate=True)
    if not isinstance(eq,Relational):
        if isinstance(eq,BooleanAtom):
            eq = formatEquation(input_latex,evaluate=False)
        else:
            eq = Eq(eq,0,evaluate=False)
    if not eq.free_symbols.issubset([x,y]):
        raise ValueError('Free Symbols')
    eq1 = formatEquationJS(eq)
    return eq1

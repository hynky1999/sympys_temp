import re
from sympy.assumptions.handlers import (CommonHandler, test_closed_group)
from sympy.assumptions import ask, Q
from checks_lib.regexes import (integer,number,sci_num_type_re)
from checks_lib.default_values import separator_functions

class AskRationalHandler2(CommonHandler):
    """
    Handler for Q.rational_2
    Test that an expression belongs to the field of rational numbers
    """


    @staticmethod
    def Expr(expr, assumptions):
        return True

    @staticmethod
    def Add(expr, assumptions):
        """
        Rational + Rational     -> Rational
        Rational + !Rational    -> !Rational
        !Rational + !Rational   -> ?
        """
        if expr.is_number:
            if expr.as_real_imag()[1]:
                return False
        return test_closed_group(expr, assumptions, Q.rational_2)


    Mul = Add
    
    @staticmethod
    def Pow(expr, assumptions):
        if ask(Q.integer(expr.exp), assumptions):
            return ask(Q.rational_2(expr.base), assumptions)
        else:
            return False
    Rational = staticmethod(CommonHandler.AlwaysTrue)

    Float = staticmethod(CommonHandler.AlwaysNone)

    ImaginaryUnit, Infinity, NegativeInfinity, Pi, Exp1,\
    GoldenRatio, TribonacciConstant = \
    [staticmethod(CommonHandler.AlwaysFalse)]*7

    @staticmethod
    def exp(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return ask(~Q.nonzero(x), assumptions)

    @staticmethod
    def cot(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return False

    @staticmethod
    def log(expr, assumptions):
        x = expr.args[0]
        if ask(Q.rational(x), assumptions):
            return ask(~Q.nonzero(x - 1), assumptions)

    sin, cos, tan, asin, atan = [exp]*5
    acos, acot = log, cot


def number_type(input,options):
    '''
    Checking for specific type of number
    Might be swaped to AskHandler later,
    right now we use regex
    '''
    equiv = True
    if 'complexType' in options:
        equiv = (re.search(r'(?<![a-z])I(?![a-z])',input)
                or re.match(number + r'$',input)
                or re.match(integer + r'$',input))
        
    if 'realType' in options:
        equiv = (not re.search(r'(?<![a-z])i(?![a-z])',input,re.IGNORECASE)
                or re.search(r'\\infty',input))
        
    if 'numberType' in options:
        equiv = re.match(number + r'$',input)
        
    if 'integerType' in options:
        equiv = re.match(integer + r'$',input)
        
    if 'variableType' in options:
        equiv = re.match(r'\s*[a-zA-Z]\s*$',input)
        
    if 'scientificType' in options:
        matching = sci_num_type_re.match(input)
        if matching and float(matching.group('number')) != 10:
            equiv = True
        else:
            equiv = False
            
    return equiv

def convertEquation(eq_latex):
    eq = 'NotLatex:{}'.format(
        separator_functions[eq_latex.group('sign')])
    eq = eq.format(eq_latex.group('l'),eq_latex.group('r'))
    return eq

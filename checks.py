#!/usr/bin/env python3

import re
import os
import sys
import json
import itertools
from collections import OrderedDict
import decimal
decimal.getcontext().rounding = decimal.ROUND_HALF_UP

from sympy import sympify
from sympy import simplify 
from sympy import expand, factor, logcombine, expand_log, expand_power_exp  
from sympy.printing.jscode import JavascriptCodePrinter
from sympy.printing.codeprinter import CodePrinter
from sympy.printing.precedence import precedence, PRECEDENCE
from sympy import symbols,Matrix,linsolve,solveset
from sympy.assumptions import register_handler, ask, Q
from sympy import nsimplify,radsimp
from sympy.core.relational import Relational
from sympy.core import Add, Basic, Mul, Lt, Le, Gt, Ge, Eq
from sympy.core.basic import preorder_traversal
from sympy.core.singleton import S
from sympy.simplify.radsimp import fraction
from sympy.assumptions.handlers import CommonHandler, test_closed_group
from latex2sympy.process_latex import process_sympy
# default values and dictionaries ---------------------------------------------
UNIT_FOLDER = 'units'
SI_CSV = 'si.csv'
US_CSV = 'us.csv'
si_csv_path = os.path.join(UNIT_FOLDER, SI_CSV)
us_csv_path = os.path.join(UNIT_FOLDER, US_CSV)

DEFAULT_THOUSANDS_SEP = ','
DEFAULT_DECIMAL_SEP = '.'
POSSIBLE_THOUSANDS_SEP = ',. '
POSSIBLE_DECIMAL_SEP = ',.'
THOUSANDS_SEP_PLACEHOLDER = '<THOUSANDSEP>'
DECIMAL_SEP_PLACEHOLDER = '<DECIMALSEP>'
SEP_ERROR_PLACEHOLDER = '<SEPERROR>'
DEFAULT_PRECISION = 10

ERROR = 'error'
UNITS = {
    # Unit, Description, ConvertTo, Coefficient
    # SI
    'g':  ('gram', 'g', 1),
    'cg': ('centigram', 'g', 0.01),
    'kg': ('kilogram', 'g', 1000),
    'mg': ('milligram', 'g', 0.001),
    'ng': ('nanogram', 'g', 0.000000001),
    'm':  ('meter', 'm', 1),
    'cm': ('centimeter', 'm', 0.01),
    'km': ('kilometer', 'm', 1000),
    'mm': ('millimeter', 'm', 0.001),
    'nm': ('nanometer', 'm', 0.000000001),
    's':  ('second', 's', 1),
    'cs': ('centisecond', 's', 0.01),
    'ks': ('kilosecond', 's', 1000),
    'ms': ('millisecond', 's', 0.001),
    'ns': ('nanosecond', 's', 0.000000001),
    'L':  ('liter', 'L', 1),
    'mL': ('milliliter', 'L', 0.01),
    # US
    'in':  ('inch', 'in', 1),
    'ft':  ('foot', 'in', 12),
    'mi':  ('mile', 'in', 63360),
    'fl':  ('fluid ounce', 'fl', 1),
    'cup': ('cup', 'fl', 8),
    'pt':  ('pint', 'fl', 16),
    'qt':  ('quart', 'fl', 32),
    'gal': ('gallon', 'fl', 128),
    'oz':  ('ounce', 'oz', 1),
    'lb':  ('pound', 'oz', 16),
    r'\\degree': (r'\degree', r'\degree', r'2*\pi'),
    r'\\\$': (r'\$', r'\$', '1')
}

#List containing all units both long and short names
units_list = [v[0] for v in UNITS.values()] + [k for k in UNITS.keys()]

#Openings and closings of intervals with boundary -> False == not include
#True == not include
interval_opening = {
    '(': True,
    '[': False
}

interval_closing = {
    ')': True,
    ']': False
}

#Signs that must be used in both expected and student input
separator_pairs = {
    '>=':'<=',
    '<=':'>=',
    '>':'<',
    '<':'>',
    '=':'='
}

#Math to Sympy conversion of signs
separator_functions = {
    '>=': 'GreaterThan(Format({})Format,Format({})Format)',
    '<=':'LessThan(Format({})Format,Format({})Format)',
    '>':'StrictGreaterThan(Format({})Format,Format({})Format)',
    '<':'StrictLessThan(Format({})Format,Format({})Format)',
    '=':'Equality(Format({})Format,Format({})Format)',
    '≠':'Unequality(Format({})Format,Format({})Format)'
}

#Latex to math conversion of signs
latex_separators = {
    r'\geq':'>=',
    r'\ge':'>=',
    r'\gt':'>',
    r'\leq':'<=',
    r'\le':'<=',
    r'\lt':'<',
    r'\eq':'=',
    r'\neq':'≠'
}

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
# end of default values and dictionaries block --------------------------------

# several functions and regexes for LaTeX-to-sympy conversions ----------------
# and LaTeX-to-LaTeX preprocessing


#REGEXES-----------------------------------------------------------------------
curl_br = '(?:[^{}]*?(?:\{[^{}]+?\})?)*?'

times = r'(\* ?|\\cdot ?|\\times ?)?'

times_re = re.compile(r'(\*|\\cdot ?|\\times)')

percent_re = re.compile(
r'(^|[+-/* ])(.+)\\%')

log_re = re.compile(
r'\\log_([^{])')

multiple_spaces_re = re.compile(
' {2,}')

variable_before_parentheses_re = re.compile(
r'\b([abcdxyz])\(')

trailing_zeros_re = re.compile(
r'(\.[0-9]*?)0+\b')

neg_fraction_re = re.compile(
r'-\\frac\{(.*?)\}\{(.*?)\}')

closing_text_re = re.compile(
r'(^|[^\\a-zA-Z])[a-zA-Z]+')

closing_text_decorated_re = re.compile(
r'(\\text\{.*?\})')

closed_to_normal_text_re = re.compile(
r'\\text\{(.*?)\}')

mixed_frac_re = re.compile(
r'-?\s*[0-9]+(\s*\\frac{[^-]+?}{[^-]+?}|\s+\(?\d+\)?/\(?\d+\)?)')

mixed_fraction_error_re = re.compile(
r'[0-9] *\( *[0-9]+ */ *[0-9]+ *\)')

parenthesis_re = re.compile(
r'\((-?[a-z]|\d+(?:.\d+)?)\)')

matrix_form_re = re.compile(
r'\\begin\{bmatrix\}(.*?)\\end{bmatrix}')

interval_form_re = re.compile(
r'\s*([{}])([^,]*?),([^,]*?)([{}])\s*'
.format(
re.escape(''.join(interval_opening.keys())),
re.escape(''.join(interval_closing.keys()))))

set_form_re = re.compile(
(r'\{{\s*(?P<var>[a-zA-Z])\s*\|\s*(?:(?P<num1>\d*)\s*(?P<sign1>{0}))'
+ r'?\s*\1\s*(?:(?P<sign2>{0})\s*(?P<num2>\d*))?\s*\}}')
.format(
'|'.join(separator_functions.keys())))

eq_form_re = re.compile(
r'^(?P<l>.*?)(?P<sign>{})(?P<r>.*)$'
.format(
'|'.join(separator_functions.keys())))

not_latex_re = re.compile(
r'NotLatex:')

format_latex_re = re.compile(
r'Format\((.*?)\)Format')

format_func_re = re.compile(
r'Format:(?P<func>.+?)\((.*?)\)Format:(?P=func)')

latex_sign_re = re.compile(
'|'.join(map(re.escape,latex_separators.keys())))
 
scientific_re = re.compile(
r'e(-?\d+)',re.IGNORECASE)

diffentiation_re = re.compile(
r'\\frac\{d\}\{d([a-z]+)\}(.*)')

separator_re = re.compile(
'|'.join(separator_pairs.keys()))

integral_re = re.compile(
r'\\int(_(?P<down>{0})\^\{{(?P<up>{0})\}})?\s*(?P<expr>.*?)d(?P<symbol>[a-z])'
.format(curl_br))

sums_re = re.compile(
r'\\sum_\{{([a-z])\=({0})\}}\^\{{({0})\}}(.*)'
.format(curl_br))

coefficient_of_one_re = re.compile(
                        r'(?<![0-9].)1'
                        + times
                        + r'(?=[a-z(\\])'
                        , flags=re.IGNORECASE)
                        
constituent_parts_re = re.compile(
r'[^\s()*+-]')

leading_zero_re = re.compile(
r'\b0(?=\.)')

escaped_par_re = re.compile(
r'\\([\{\[\(\}\]\)])'
)
left_par_re = re.compile(
r'\\left([\{\(\[])'
)
right_par_re = re.compile(
r'\\right([\}\)\]])'
)
trailing_zeros_re = re.compile(
r'(\.[0-9]*?)0+\b')

limits_re = re.compile(
r'\\lim_\{{({0})\\to({0})\}}(.*)'
.format(curl_br))

preceding_zeroes_re = re.compile(
r'(?<![\d\.])(0+)(\d+?)')

units = [r'({})(?:\^{{?(-?\d*)}}?)?(\*)?'
.format(u) for u in sorted(units_list,key=len,reverse=True)]

unit_text_re = re.compile(
r'(?<=[^a-zA-Z\\])(?:\\text{{)?(?P<up>(?:{0})+)(?P<down>\/(?:{0})+)?(?:}})?(?:(?=\=)|$)'
.format('|'.join(units)))

#Rexegex for sets
set_re_brackets = re.compile(
r'(\[)([^|]*?)(\])$')

set_re_par = re.compile(
r'(\()([^|]*?)(\))$')

set_re_par2 = re.compile(
r'(\{)([^|]*?)(\})$')

set_re_error = re.compile(
r'^\s*[({].*?\d{1,3},\d{1,2}[^\d].*?[})]\s*$')

set_res = [set_re_brackets,set_re_par,set_re_par2]

#Functions---------------------------------------------------------------------
def load_units(units_csv_path):
    ''' Load conversion tables for SI/US units
    '''
    conversion_table = {}
    with open(units_csv_path, 'r', encoding='utf-8') as csv_file:
        csv_file.readline()


def convert_percent(matchobj):
    percent_str = (r'NotLatex:Format:convert_percent_final({})'
    + r'Format:convert_percent_final')
    percent_str = percent_str.format(matchobj.group(2))
    return percent_str


def convert_percent_final(found_str):
    precision = len((str(found_str) + '.').split('.')[1]) + 2
    return str(round(found_str * 0.01, precision))
 
 
def convert_frac(matchobj):
    if matchobj.group(1) == '1':
        return ''.join((r'\frac{\one}{',
                        matchobj.group(2), r'}*(-1)'))
    else:
        return ''.join((r'\frac{', matchobj.group(1),
                        r'}{', matchobj.group(2), r'}*(-1)'))

                    
def convertMatrix(matrix_latex):
    matrix_form = [[r'Format({0})Format'.format(cell) 
                    for cell in row.split(r'&')]
                    for row in matrix_latex.group(1).split('\\\\')]
                
    return r'NotLatex:Matrix({})'.format(
                                    matrix_form)
    

def convertInterval(interval_latex):
    opening = interval_opening[interval_latex.group(1)]
    closing = interval_closing[interval_latex.group(4)]
    interval_str = (r'NotLatex:Interval(Format({1})'
    + r'Format,Format({2})Format,{0},{3})')
    
    return interval_str.format(
            opening,*interval_latex.groups()[1:3],closing)

  
def convertDif(dif_latex):
    derivation_symbols = list(dif_latex.group(1))
    derivated = r'NotLatex:diff(Format({})Format,{})'
    return derivated.format(
            dif_latex.group(2),','.join(derivation_symbols))

   
def convertSum(sum_latex):
    sym,start,end,expr = sum_latex.groups()
    sum_str = (r'NotLatex:Sum(Format({})Format,(Format({})Format,Format'
    + r'({})Format,Format({})Format)).doit()')
    return sum_str.format(
            expr,sym,start,end)


def convertIntegral(int_latex):
    up = int_latex.group('up')
    down = int_latex.group('down')
    optional = int_latex.group('symbol')
    if up and down:
        optional = r'({},Format({})Format,Format({})Format)'.format(
                                        optional,down,up)
                                        
    interval_syntax = r'NotLatex:integrate(Format({})Format,{})'.format(
                                        int_latex.group('expr'),optional)
    return interval_syntax
    
    
def convertLimit(limit_latex):
    variable,limit,expr = limit_latex.groups()
    limit = re.sub(r'\\infty','oo',limit)
    if re.search(r'\^',limit):
        limit = r"Format({p[0]})Format,'{p[1]}'".format(
                                        p=limit.split(r'^'))
                                        
    limit_syntax = r'NotLatex:limit(Format({})Format,Format({})Format,{})'
    return limit_syntax.format(
            expr,variable,limit)


def convertSet(set_latex):
    input_latex = 'NotLatex:'
    variable = set_latex.group('var')
    if(set_latex.group('sign1') and set_latex.group('num1')
    and set_latex.group('sign2') and set_latex.group('num2')): 
        func1 = separator_functions[set_latex.group('sign1')].format(
                                    set_latex.group('num1'),variable)
        func2 = separator_functions[set_latex.group('sign2')].format(
                                    variable, set_latex.group('num2'))
        input_latex += (r'Intersection(solveset({1},Format({0})Format,S.Reals)'
        +r',solveset({2},Format({0})Format,S.Reals))').format(
        variable,func1,func2)
    
    elif set_latex.group('sign1') and set_latex.group('num1'):
    
        func1 = separator_functions[set_latex.group('sign1')].format(
                        set_latex.group('num1'),set_latex.group('var'))
        input_latex += r'solveset({1},Format({0})Format,S.Reals)'.format(
                                                            variable,func1)
        
    elif set_latex.group('sign2') and set_latex.group('num2'):
        func2 = separator_functions[set_latex.group('sign2')].format(
                        set_latex.group('var'),set_latex.group('num2'))
        input_latex += r'solveset({1},Format({0})Format,S.Reals)'.format(
                                                            variable,func2)
                                                            
    else:
        input_latex += r'Interval(-oo,oo,True,True)'
    
    return input_latex


def convertComplexUnit(unit_latex):
    units_dict = dict(zip(units_list,[v[2] for v in UNITS.values()]*2))
    
    def convertUnits(unit):
        output=''
        g = unit.groups()
        for u_i,unit_mark in enumerate(g[::3]):
            if not unit_mark:
                continue
                
            output += str(units_dict[unit_mark])
            if g[3*u_i+1]:
                output = '({})^{{{}}}'.format(output,str(g[3*u_i+1]))
                
            output = r'*' + output
            break
            
        return output
    
    units_re = re.compile('|'.join(units))
    output = '({})'.format(
        units_re.sub(convertUnits,unit_latex.group('up'))[1:])
    if unit_latex.group(2):
        output += r'/({})'.format(
        units_re.sub(convertUnits,unit_latex.group('down'))[2:])
    
    return output    


def convertEquation(eq_latex):
    eq = 'NotLatex:{}'.format(
        separator_functions[eq_latex.group('sign')])
    eq = eq.format(eq_latex.group('l'),eq_latex.group('r'))
    return eq

def transform_set(set_latex
                ,par_open=['(','[','{']
                ,par_close=[')',']','}']
                ,options={}):
    ''' Transform string set into list and return type of set
        any == type does not matter - default
        list == type matters and order matters
        set == type matters and order does not matter
    '''
    #Parsing of list
    #Try to match string using set regex and then perform balance check
    type = 'any'
    search_set = set_latex
    for set_re in set_res:
        search = set_re.match(set_latex)
        if search and balance_check(search.group(2)):
            if set_re == set_re_par:
                type = 'list'
            elif set_re == set_re_par2:
                type = 'set'
            search_set = search.group(2)
            break
    opening = []
    set_symbolic = []
    last_char = 0
    quoted = False
    closed = False
    for i,char in enumerate(search_set):
        if char in par_open and len(opening) == 0 and not quoted:
            if closed:
                raise ValueError

            opening.append(char)
            set_symbolic.append([char])
            last_char = i+1
            
        elif char in par_close and len(opening) == 1 and not quoted:
            element = str(convert(search_set[last_char:i],
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             ignore_text=options.get('ignoreText', False),
                             ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                             euler_number=options.get('allowEulersNumber',False),
                             evaluate=True))
                             
            if element == None:
                raise ValueError
                
            set_symbolic[-1].append(str(element))
            set_symbolic[-1].append(char)
            char2 = opening.pop()
            if char2 == '{' and char == '}':
                set_symbolic[-1] = [[set_symbolic[-1][0]]
                                  + sorted(set_symbolic[-1][1:-1])
                                  + [set_symbolic[-1][-1]]]
                                  
            last_char = i+1
            if closed:
                raise ValueError
                
            closed = True
        elif char == '"':
            if quoted:
                quoted = False
                
            else:
                quoted = True
                last_char = i+1 
                
        elif char == ',' and not quoted:
            if opening:
                element = str(convert(search_set[last_char:i],
                                  thousand_sep=getThousandsSeparator(options),
                                  decimal_sep=getDecimalSeparator(options),
                                  ignore_text=options.get('ignoreText', False),
                                  ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                                  euler_number=options.get('allowEulersNumber',False),
                                  evaluate=True))
                if element is None:
                    raise ValueError
                set_symbolic[-1].append(str(element))
                last_char = i+1
            else:
                if closed:
                    last_char = i+1
                    closed = False
                    
                else:
                    element = str(convert(search_set[last_char:i],
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      ignore_text=options.get('ignoreText', False),
                                      ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                                      euler_number=options.get('allowEulersNumber',False),
                                      evaluate=True))
                    
                    if element is None:
                        raise ValueError
                        
                    set_symbolic.append([str(element)])
                    last_char = i+1
                    
    if last_char != len(search_set) and not closed:
        element = str(convert(search_set[last_char:],
                          thousand_sep=getThousandsSeparator(options),
                          decimal_sep=getDecimalSeparator(options),
                          ignore_text=options.get('ignoreText', False),
                          ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                          euler_number=options.get('allowEulersNumber',False),
                          evaluate=True))
        if element is None:
            raise ValueError
            
        set_symbolic.append([str(element)])
    return set_symbolic,type

def strToList(s):
    s = s.strip()
    level = 0
    list_temp = []
    esc1,esc2 = [False]*2
    last_char = 0
    flag = 0
    for i,char in enumerate(s):

        if not esc1 and not esc2:

            if char in ('(','['):
                level+= 1
                flag = 1

                if level == 1:
                    last_char = i+1

            elif char in (')',']'):
                if level == 1:
                    element = strToList(s[last_char:i])

                    if element is not None:
                        list_temp.append(element)

                    last_char = i+1
                level-= 1
            elif char == ',' and level == 1:
                    element = strToList(s[last_char:i])
                    if element is not None:
                        list_temp.append(element)

                    last_char = i+1
        if char == '"':
            esc1 = not esc1

        elif char == "'":
            esc2 = not esc2

    if not flag:
        s = s.replace("'",'').replace('"','')
        return s if s else None

    else:
        return list_temp
        
def formatEquation(equation,options={}):
    equation = convert(equation, evaluate=False,
                        thousand_sep=getThousandsSeparator(options),
                        decimal_sep=getDecimalSeparator(options),
                        euler_number=True)
    if equation is None:
        raise ValueError('Error')
    return equation

def formatLine(params):
    point1,point2 = [list(map(convert,x)) for x in params]
    a, b, x, y = symbols('a b x y')
    if point1[0] == point2[0]:

        if point1[1] == point2[1]:
            raise ValueError('Point')

        else:
            return Eq(x,point1[0])

    if point1[1] == point2[1]:
        return Eq(y,point1[1])

    A = Matrix([[point1[0],1],
                [point2[0],1]])
    B = Matrix([[point1[1]],
                [point2[1]]])
    a,b = linsolve((A,B),[a,b]).args[0]
    return Eq(y,a*x+b)

def formatCircle(params):
    x, y = symbols('x y')
    center,point1 = [list(map(convert,x)) for x in params]
    if center == point1:
        raise ValueError('Point')

    e = (point1[0]-center[0])**2+(point1[1]-center[1])**2
    return Eq((x-center[0])**2+(y-center[1])**2,e)

def formatEllipse(params):
    x, y = symbols('x y')
    center,point1,point2 = [list(map(convert,x)) for x in params]
    a_2 = (center[0]-point1[0])**2 
    b_2 = (center[1]-point2[1])**2
    if a_2 == 0 or b_2 == 0:
        raise ValueError('Invalid Elipse')

    return Eq(((x-center[0])**2)/a_2+((y-center[1])**2)/b_2,1)

def formatParabola(params):
    x, y = symbols('x y')
    apex,point1,point2 = [list(map(convert,x)) for x in params]
    if ((apex[1] < point1[1] and apex[1] < point2[1])#X-centric
        or (apex[1] > point1[1] and apex[1] > point2[1])):
        p1 = (point1[0]-apex[0])**2/(point1[1]-apex[1])
        p2 = (point2[0]-apex[0])**2/(point2[1]-apex[1])
        if point1[1] == apex[1] or point2[1] == apex[1]:
            raise ValueError('Invalid Parabola')

        if p1 == p2:
            return Eq((x-apex[0])**2,p1*(y-apex[1]))

        else:
            raise ValueError('Invalid Parabola')

    else:
        if point1[0] == apex[0] or point2[0] == apex[0]:
            raise ValueError('Invalid Parabola')

        p1 = (point1[1]-apex[1])**2/(point1[0]-apex[0])
        p2 = (point2[1]-apex[1])**2/(point2[0]-apex[0])
        if p1 == p2:
            return Eq((y-apex[1])**2,p1*(x-apex[0]))

        else:
            raise ValueError('Invalid Parabola')

def formatHyperbola(params):
    x, y, a_2, b_2 = symbols('x y a b')
    foci1,foci2,point1 = [list(map(convert,x)) for x in params]
    if foci1[1] == foci2[1]: 
        e = (foci1[0]-foci2[0])/2
        center = (foci2[0]+e,foci1[1])
        a_2 = solveset(
              Eq(((point1[0]-center[0])**2)/a_2\
              -((point1[1]-center[1])**2)/(e**2-a_2),1),a_2).args[0]
        b_2 = e**2 - a_2
        if a_2 == 0 or b_2 ==0:
            raise ValueError('Invalid Hyperbola')

        else:
            return Eq(((x-center[0])**2)/a_2-((y-center[1])**2)/b_2,1)

    elif foci1[0] == foci2[0]:
        e = (foci1[1]-foci2[1])/2
        center = (foci1[0],foci2[1]+e)
        b_2 = solveset(
              Eq((((point1[1]-center[1])**2)/b_2-\
                (point1[0]-center[0])**2)/(e**2-b_2),1),b_2).args[0]
        a_2 = e**2 - b_2
        if a_2 == 0 or b_2 ==0:
            raise ValueError('Invalid Hyperbola')

        else:
            return Eq(((y-center[1])**2)/b_2-((x-center[0])**2)/a_2,1)

    else:
        raise ValueError('Invalid Hyperbola')

def formatOp(eq,points,shapeStyle,strict=False):
    equality,higher,lower = [False]*3
    if shapeStyle == '' and strict:
        if isinstance(eq,(Lt,Gt)):
            shapeStyle = 'dashed'
    #print(points,eq)
        
    for p in points:
        if subPoint(p,Eq(eq.lhs,eq.rhs)):
            equality = True

        elif subPoint(p,Lt(eq.lhs,eq.rhs)):
            lower = True
                
        elif subPoint(p,Gt(eq.lhs,eq.rhs)):
            higher = True

    if higher and lower:
        raise ValueError('Wrong Points')
    
    elif equality and shapeStyle == 'dashed':
        raise ValueError('Wrong shapeStyle')

    elif higher:
        if shapeStyle == 'dashed':
            op = Gt

        else:
            op = Ge

    elif lower:
        if shapeStyle == 'dashed':
            op = Lt
        
        else:
            op = Le

    elif equality:
        op = Eq

    else:
        raise ValueError()
    return op(eq.lhs,eq.rhs)

def formatEquations(equations,points,shapeStyle):
    eqs = []
    for i,eq in enumerate(equations):
        strict = False
        object_type = eq[0]
        if object_type == 'eqn':
            formated_eqn = formatEquation(eq[1])

            strict = True
        elif object_type == 'line':
            formated_eqn = formatLine(eq[1])

        elif object_type == 'circle':
            formated_eqn = formatCircle(eq[1])

        elif object_type == 'ellipse':
            formated_eqn = formatEllipse(eq[1])

        elif object_type == 'parabola':
            formated_eqn = formatParabola(eq[1])

        elif object_type == 'hyperbola':
            formated_eqn = formatHyperbola(eq[1])

        else:
            raise ValueError('Not Defined object')

        formated_eqn = formatOp(formated_eqn,
                                points,
                                shapeStyle[i],
                                strict=strict)
        eqs.append(formated_eqn)
    return eqs

def formatGraphList(graph_list):
    no_solution_re = re.compile(r'\s*no\s*solution\s*$')
    graph_list = strToList('('+graph_list+')')
    if len(graph_list) == 1:
        shapeEqn = graph_list[0]

        if (isinstance(shapeEqn,str)
            and no_solution_re.match(shapeEqn)):
            shapeEqn = []
        shapeStyle = ['']*len(shapeEqn)
        regionPoints = []

    elif len(graph_list) == 2:
        shapeEqn,regionPoints = graph_list
        shapeStyle = ['']*len(shapeEqn)

    elif len(graph_list) == 3:
        shapeEqn,shapeStyle,regionPoints = graph_list

    else:
        raise ValueError('Could not format')

    shapeStyle = formatShapeStyle(shapeStyle,len(shapeEqn))
    return shapeEqn,shapeStyle,regionPoints
    
def formatShapeStyle(shapes,len_eqs):
    if len(shapes) == 0:
        shapes = [''] * len_eqs
        
    else:
        shapes = [x for x in shapes]
        
    if len(shapes) != len_eqs:
        raise ValueError('Error_graph')
    
    return shapes
        
    
    return shapes
def checkEquations(eq1,eq2):
    if isinstance(eq1,Ge) or isinstance(eq1,Gt):
        eq1 = eq1.reversed

    if isinstance(eq2,Ge) or isinstance(eq2,Gt):
        eq2 = eq2.reversed

    if isinstance(eq1,type(eq2)):
        division = simplify(expand((eq1.lhs-eq1.rhs)/(eq2.lhs-eq2.rhs)))
        if (division.is_number and
            (division.is_positive or isinstance(eq1,Eq))):
            return True
    return False
        
def checkRegionPoints(points,equations):
    for e in equations:
        for p in points:
            e = subPoint(p,e)
            if e != True:
                raise ValueError('Error_graph')

    return True
    
def subPoint(point,eq):
    x,y = symbols('x y')
    a = eq.subs([[x,point[0]],[y,point[1]]])
    return eq.subs([[x,point[0]],[y,point[1]]])


def replace_separators(input_latex,
                       thousand=None,
                       decimal=DEFAULT_DECIMAL_SEP):
    # replace allowed thousand and decimal separators with placeholders
    if thousand is not None:
        thousand_sep_re = re.compile(
                          ''.join((r'(?<=[0-9])(['
                          ,thousand
                          ,r'])(?=[0-9]{3}([^0-9]|$))')))
        input_latex = thousand_sep_re.sub('', input_latex)
        
    decimal_sep_re = re.compile(r'([{}])(?=[0-9])'.format(
                                                    decimal))
    input_latex = decimal_sep_re.sub(DECIMAL_SEP_PLACEHOLDER, input_latex)

    # replace not allowed thousand and decimal separators with error placeholders
    not_thousand = ''.join(
                    sorted(set(POSSIBLE_THOUSANDS_SEP)
                    - set(thousand or '')
                    - set(decimal)))
    if len(not_thousand) != 0:
        not_thousand_sep_re = re.compile(
                                ''.join((r'(?<=[0-9])(['
                                ,not_thousand
                                ,r'])(?=[0-9]{3})')))
        input_latex = not_thousand_sep_re.sub(
                    SEP_ERROR_PLACEHOLDER, input_latex)
        
    not_decimal = ''.join(sorted(set(POSSIBLE_DECIMAL_SEP) - set(decimal)))
    not_decimal_sep_re = re.compile(r'([{}])(?=[0-9])'.format(decimal))
    input_latex = not_decimal_sep_re.sub(SEP_ERROR_PLACEHOLDER, input_latex)

    # replace placeholders with actual separators
    input_latex = input_latex.replace(DECIMAL_SEP_PLACEHOLDER, '.')
    return input_latex
    
    
def balance_check(str_input,par_open=['(','[','{'],par_close=[')',']','}']):
    str_input = escaped_par_re.sub(r'\1',str_input)
    opening = []
    for i,char in enumerate(str_input):
            if char in par_open:
                par_index = par_open.index(char)
                if i >= 6 and str_input[i-6:i] == r'\\left':
                    par_index = par_index*-1
                if i >= 6 and str_input[i-6:i] == r'\\right':
                    raise ValueError('Not_Supported_Error')
                    
                opening.append(par_index)

            elif char in par_close:
                par_index = par_close.index(char)
                if len(opening) <= 0:
                    return False
                last_par = opening.pop()
                if i >= 6 and str_input[i-6:i] == r'\\right':
                    par_index = par_index*-1
                    
                if i >= 6 and str_input[i-6:i] == r'\\left':
                    raise ValueError('Not_Supported_Error')    
                if par_index != last_par:
                    return False
    return not opening

def replaceNonEffective(input_latex):
    input_latex = escaped_par_re.sub(r'\1',input_latex)
    # \left,\right
    input_latex = left_par_re.sub(r'\1',input_latex)
    input_latex = right_par_re.sub(r'\1',input_latex)
    # times for *
    input_latex = times_re.sub(r'*',input_latex)
    # \cfrac to frac
    input_latex = input_latex.replace(r'\cfrac', r'\frac')
    
    return input_latex    
    
def identify_expected(input_latex,expected_latex,options):
    '''
    Identification of expected and calling set_evaluation properly
    '''
    expected_tmp = replaceNonEffective(expected_latex)
    if ('setEvaluation' in options
        or 'orderedElements' in options
        or 'orderedPair' in options):
        return set_evaluation(input_latex,expected_latex,options)
    
    if 'interpretAsList' in options:
        options['orderedPair'] = True
        return set_evaluation(input_latex,expected_latex,options)
        
    if 'interpretAsSet' in options:
        return set_evaluation(input_latex,expected_latex,options)
        
    for set_re in set_res:
        search = set_re.match(expected_tmp)
        if search and balance_check(search.group(2)):
            break
            
        else:
            search = ''
            
    if search:
        if (search.group(1) == '(' and search.group(3) == ')' and
            not len(re.findall(r',',search.group(2))) == 1):
            options['orderedPair'] = True
            return set_evaluation(input_latex,expected_latex,options)
            
        elif search.group(1) == '{' and search.group(3) == '}':
            return set_evaluation(input_latex,expected_latex,options)
            
    if (set_re_error.search(input_latex)
        and getThousandsSeparator(options)) == ',':
        return 'Undefined_Expected_Error'
    else:
        return None

 
def preprocess_latex(input_latex,
                     ignore_trailing_zeros=False,
                     keep_neg_fraction_form=False,
                     thousand_sep=None,
                     decimal_sep=DEFAULT_DECIMAL_SEP,
                     preprocess_sep=True,
                     ignore_text=False,
                     ignore_alpha=False,
                     euler_number=False,
                     fix_parenthesis=False):
                     
    ''' Convert anything that latex2sympy can't handle,
        e.g., percentages and logarithms
        If we want to convert to sympy formulas the expression
        has to be preceded with NotLatex:
        If NotLatex: is used it can also be specified which
        parts of expression will be formated by sympy2latex
        by surrounding them with Format(expr)Format, by preceding
        with Format:() we call specific function with expression;
        More in sympify_latex
    '''
    # check for incorrect mixed fractions such as 1 (3/4)
    if mixed_fraction_error_re.search(input_latex) is not None:
        return None

    # replace decimal separators from allowed to appropriate,
    # report errors if there are separators that are not allowed
    if preprocess_sep:
        input_latex = replace_separators(input_latex,
                                         thousand=thousand_sep,
                                         decimal=decimal_sep)
        if SEP_ERROR_PLACEHOLDER in input_latex:
            return None
            
    if not balance_check(input_latex) and not interval_form_re.search(input_latex):
        raise ValueError('Parenthesis_Error')
        
    input_latex = replaceNonEffective(input_latex)
    # $ to \dol
    input_latex = input_latex.replace(r'\$', r'\dol')
    # latex signs to normal
    input_latex = latex_sign_re.sub(
                        lambda x: latex_separators[x.group(0)],input_latex)
    # \textit to \text
    input_latex = input_latex.replace(r'\textit',r'\text')

    # Euler Number handling
    if euler_number:
        input_latex = re.sub(r'([^\\a-zA-Z]+|[xy]|^)e',r'\1E',input_latex)
        input_latex = re.sub(r'\\exp\^',r'E^',input_latex)
        
    else:
        input_latex = scientific_re.sub(r'*10^{\1}',input_latex)
        
    # Imaginary number
    input_latex = re.sub(r'(?<![a-zA-Z])(i)(?![a-zA-Z])','I',input_latex)
    # Percent sign (\%)
    input_latex = percent_re.sub(convert_percent, input_latex)
	# Degree fix
    input_latex = re.sub('°',r'*2*\\pi',input_latex)
    # \log_a -> \log_{a}
    input_latex = log_re.sub(r'\\log_{\1}', input_latex)
    # a(x+1) -> x*(x+1)
    input_latex = variable_before_parentheses_re.sub(r'\1*(', input_latex)
    #ignore parenthesis
    if fix_parenthesis:
        input_latex = parenthesis_re.sub(r'\1',input_latex)
        
    # ignore trailing \text{}
    if ignore_text:
        input_latex = closing_text_decorated_re.sub(r'', input_latex)
        
    # ignore all trailing text
    if ignore_alpha:
        input_latex = closing_text_decorated_re.sub(r'', input_latex)
        input_latex = closing_text_re.sub(r'\1', input_latex)
        
    input_latex = closed_to_normal_text_re.sub(r'\1',input_latex)
    # trailing zeros
    if ignore_trailing_zeros:
        input_latex = trailing_zeros_re.sub(
            lambda x: '' if (x.group(1) == '.') else x.group(1), input_latex)
        
    #Interval preparation
    if interval_form_re.search(input_latex) and decimal_sep != ',':
        input_latex = interval_form_re.sub(convertInterval,input_latex)
        
    #Diferentiation preparation
    if diffentiation_re.search(input_latex):
        input_latex = diffentiation_re.sub(convertDif,input_latex)
        
    #Integral preparation
    if integral_re.search(input_latex):
        input_latex = integral_re.sub(convertIntegral,input_latex)
        
    #Limit preparation
    if limits_re.search(input_latex):
        input_latex = limits_re.sub(convertLimit,input_latex)
    
    #Sums preparation
    if sums_re.search(input_latex):
        input_latex = sums_re.sub(convertSum,input_latex)
        
    #fix fractions so that -\frac{1}{2} is not converted into -1/2    
    if keep_neg_fraction_form:
        input_latex = neg_fraction_re.sub(convert_frac, input_latex)
        
    #Matrices preparation
    if matrix_form_re.search(input_latex):
        input_latex = re.sub(r'\\end\{bmatrix\}*\\begin\{bmatrix\}'
                            ,r'\\end{bmatrix}*\\begin{bmatrix}'
                            ,input_latex)
        input_latex = matrix_form_re.sub(convertMatrix,input_latex)
        
    #Form perparation
    if set_form_re.search(input_latex):
        input_latex = set_form_re.sub(convertSet,input_latex)   
    return input_latex


def sympify_latex(input_latex, evaluate=None):
    ''' Return sympy representation of a latex string if possible;
        If latex string contains NotLatex: only parts surrounded by
        Format()Format will be converted using latex2sympy
        
        None if conversion fails.
    '''
    try:
        if not_latex_re.search(input_latex):
            input_latex = not_latex_re.sub('',input_latex)
            input_latex = format_latex_re.sub(
                            lambda x: str(process_sympy(x.group(1)))
                            ,input_latex)
            input_latex = format_func_re.sub(
                            lambda x: globals()[x.group('func')](
                            sympify(str(process_sympy(x.group(2)))))
                            ,input_latex)
            input_symbolic = sympify(input_latex,evaluate=evaluate)
        else:
            input_symbolic = process_sympy(input_latex)
            if evaluate == True:
                input_symbolic = sympify(str(input_symbolic))
        if input_symbolic == S.EmptySet:
            return None
            
    except:
        return None
    return input_symbolic


def convert(input_latex, evaluate=None,
            ignore_trailing_zeros=False,
            keep_neg_fraction_form=False,
            thousand_sep=None,
            decimal_sep=DEFAULT_DECIMAL_SEP,
            preprocess_sep=True,
            ignore_text=False,
            ignore_alpha=False,
            euler_number=False,
            fix_parenthesis=False):
    ''' All preprocessing + sympy conversion in one function
    '''
    input_latex = preprocess_latex(input_latex,
                                   ignore_trailing_zeros=ignore_trailing_zeros,
                                   keep_neg_fraction_form=keep_neg_fraction_form,
                                   thousand_sep=thousand_sep,
                                   decimal_sep=decimal_sep,
                                   preprocess_sep=preprocess_sep,
                                   ignore_text=ignore_text,
                                   ignore_alpha=ignore_alpha,
                                   euler_number=euler_number,
                                   fix_parenthesis=fix_parenthesis)
    if input_latex is None:
        return None
    input_symbolic = sympify_latex(input_latex, evaluate=evaluate)
    return input_symbolic

# Replace variables in the input_latex
# # input_latex: normal latex string
# # variables: [
# #     { id: 'x', type: 'value', value: 3 },
# #     { id: 'y', type: 'value', value: 5 },
# #     { id: 'z', type: 'formula', value: 'x+y' }
# # ]
def replace_variables(input_latex,
                      variables):
    input_latex = preprocess_latex(input_latex)
    
    # Replace variables first deeply until fixed times
    for i in range(0, 10):
        prev_latex = input_latex
        for variable in variables:
            variable_re = re.compile(re.escape(variable['id']) + r'\b')    
            input_latex = re.sub(
                        variable_re
                        , '(' + str(variable['value']) + ')'
                        , input_latex)
                        
        if prev_latex == input_latex:
            break
            
    return input_latex


# Calculate the formula
def calculate_expression(input_latex):
    input_latex = preprocess_latex(input_latex.strip(), ',', '.')
    input_symbolic = sympify_latex(input_latex)
    return simplify(input_symbolic)

# end of preprocessing block --------------------------------------------------

# a couple of helper functions to wrap the return -----------------------------
# results in a more neat form
def xor(a, b):
    ''' Logical xor one-liner
    '''
    return a and not b or not a and b

def result(bool_result):
    ''' Convert bool value to lowercase str
    ''' 
    return str(bool_result).lower()

def getThousandsSeparator(options):
    thousand_sep = options.get('setThousandsSeparator', None)
    decimal_sep = options.get('setDecimalSeparator', None)

    if thousand_sep is None and decimal_sep is None:
        thousand_sep = ','
        
    elif thousand_sep is None and decimal_sep is not None:
        thousand_sep = '.' if decimal_sep == ',' else ','
        
    return thousand_sep

def getDecimalSeparator(options):
    thousand_sep = options.get('setThousandsSeparator', None)
    decimal_sep = options.get('setDecimalSeparator', None)

    if thousand_sep is None and decimal_sep is None:
        decimal_sep = '.'
        
    elif thousand_sep is not None and decimal_sep is None:
        decimal_sep = ',' if thousand_sep == '.' else '.'
        
    return decimal_sep

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
    
    
register_handler('rational_2', AskRationalHandler2)
    
def number_type(input,options):
    '''
    Checking for specific type of number
    Might be swaped to AskHandler later,
    right now we use regex
    '''
    
    integer = r'\s*-?\s*\d+\s*'
    number = r'\s*-?\s*\d+(\.\d+)?\s*'
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
        matching = re.match((r'\s*-?\s*(?P<number>\d+(\.\d+)?)\s*'
                    + times +r'\s*10\s*\^\s*('
                    + number + r'|\{' + number + r'})\s*$')
                    ,input)
        if matching and float(matching.group('number')) != 10:
            equiv = True
        else:
            equiv = False
            
    return equiv

def derivateExpected(inp,exp):
    parts = re.search(r'\\int(?!_)(.*?)(d[a-z])',inp)
    inp = r'\frac{{d}}{{{}}}{}'.format(parts.group(2),exp)
    exp = parts.group(1)
    return inp,exp

def swap_units(input_latex,expected_latex):
    expected_unit_search = unit_text_re.search(expected_latex)
    if expected_unit_search:
        if not unit_text_re.search(input_latex):
            raise ValueError('No unit in input')
        expected_unit = convertComplexUnit(expected_unit_search)
        expected_latex = unit_text_re.sub(lambda x:'('
                                        + convertComplexUnit(x)
                                        + '/'
                                        + expected_unit
                                        + ')'
                                        ,expected_latex)
        input_latex = unit_text_re.sub(lambda x:'('
                                        + convertComplexUnit(x)
                                        + '/'
                                        + expected_unit
                                        + ')'
                                        ,input_latex)

    else:
        if unit_text_re.search(input_latex):
            raise ValueError('No unit in expected')
        
    return input_latex,expected_latex
    
def equation_parts(input_latex,expected_latex,options):
    ''' Function splits input and expected into 2 parts
        by sign
    '''
    try:
        a_sep = separator_re.search(input_latex).group(0)
        s_sep = separator_re.search(expected_latex).group(0)
    except:
        raise ValueError('Signs_Error')
    flipped = False
    if a_sep != s_sep:
        if separator_pairs[a_sep] == s_sep:
            flipped = True
            
        else:
            raise ValueError('false')
    
    expected_latex, expected_result_latex = expected_latex.split(
                                                s_sep, maxsplit=1)
    expected_symbolic = sympify_latex(expected_latex)
    expected_result_symbolic = sympify_latex(expected_result_latex)
        
    input_latex, input_result_latex = input_latex.split(
                                                a_sep, maxsplit=1)
    input_symbolic = sympify_latex(input_latex)
    input_result_symbolic = sympify_latex(input_result_latex)
        
    if flipped:
        input_symbolic,input_result_symbolic = (input_result_symbolic
                                                ,input_symbolic)
                                                
    equiv = (checkOptions(input_latex,options)
        or checkOptions(input_result_latex,options))
        
    return (input_symbolic,input_result_symbolic,
                expected_symbolic,expected_result_symbolic,
                equiv,a_sep)


def format_sym_expression(exp,options):
    if options.get('allowEulersNumber'):
        try:
            exp = logcombine(expand_log(exp,force=True))
        except:
            pass
    try:
        exp = expand(simplify(exp))
    except AttributeError:
        exp = simplify(exp)
    decimal_places = options.get('significantDecimalPlaces')
    if decimal_places:
        try:
            exp = round(decimal.Decimal(str(float(exp))),decimal_places)
        except:
            pass
    return exp
                
def parse_tolerance(tolerance,expected_result_numeric):
    if '%' in tolerance:
        try:
            tolerance = float(tolerance.replace('%',''))
        except ValueError:
            raise ValueError('Unparsable_Tolerance_Error')
        return float(tolerance)*expected_result_numeric/100
    else:
        return float(tolerance)
    
def checkOptions(input,options):
    '''
    Additional checks from main function are perfomed using
    this. If more than one function from group is used
    raise collision error
    '''
    equiv = True
    options = options.copy()
    options['inverseResult'] = False
    syntax_func = allowed_options['equivSyntax']
    integer_func = ['complexType'
                    ,'integerType'
                    ,'realType'
                    ,'numberType']
    simple_func = ['isFactorised'
                    ,'isExpanded'
                    ,'isSimplified'
                    ,'isRationalized'
                    ,'isRational']
    collisions = [0] * 3
    for option in options:
        if option in integer_func:
            if collisions[0] == 1:
                raise ValueError('Complex number check collision')
            equiv = equiv and number_type(input,options)
            collisions[0] = 1
            
        elif option in syntax_func:
            if collisions[1] == 1:
                raise ValueError('Syntax check collision')
            if equiv_syntax(input,options={option:True})=='false':
                equiv = False
            collisions[1] = 1
            
        elif option in simple_func:
            if collisions[2] == 1:
                raise ValueError('Simplification check collision')
            if check_func[option](input,options) == 'false':
                equiv = False
            collisions[2] = 1
            
    return equiv
            
# end of helper functions -----------------------------------------------------

# check functions -------------------------------------------------------------
def equiv_symbolic(input_latex, expected_latex, options):
    ''' check equivSymbolic
        Function format and simplify both input and expected
        and then compare them using str compare
        If expected contains sign, it is processed as equation
        Equation is processed by simplifing both sides and then deduction
        left side from right side on both expected and input and then
        those expressions are str compared
        If compareSides is set equations are processed by simplifing
        both sides of input and expected and then those expressions
        are str compared
    '''
    
    
    ''' Expected result identification
        If set indications are found call setEvaluation else proceed
    '''
    identified = identify_expected(input_latex,expected_latex,options)
    if identified is not None:
        return identified
    #Swap of integral for derivation
    if re.search(r'\\int(?!_).*d[a-z]',input_latex):
        input_latex,expected_latex = derivateExpected(
                                        input_latex
                                        ,expected_latex)
    
    #Preprocessing of Latex
    try:
        expected_latex = preprocess_latex(expected_latex.strip(),
            thousand_sep=getThousandsSeparator(options),
            decimal_sep=getDecimalSeparator(options),
            ignore_text=options.get('ignoreText', False),
            ignore_alpha=options.get('ignoreAlphabeticCharacters', False),
            euler_number=options.get('allowEulersNumber',False))
    except ValueError as e:
        return e.args[0]
    try:
        input_latex = preprocess_latex(input_latex.strip(),
            thousand_sep=getThousandsSeparator(options),
            decimal_sep=getDecimalSeparator(options),
            ignore_text=options.get('ignoreText', False),
            ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
            euler_number=options.get('allowEulersNumber',False))
    except ValueError:
        return result(False)
        
    if input_latex is None:
        return 'Parsing_Error'
    
    #Swap of units to numbers
    try:
        input_latex,expected_latex = swap_units(input_latex,expected_latex)
    except ValueError:
        return result(False)
    
    #Detection of equation signs in expected_latex
    if (separator_re.search(expected_latex)
        or 'compareSides' in options):
        
        #Split latexes by a sign
        try:
            (input_symbolic
            ,input_result_symbolic
            ,expected_symbolic
            ,expected_result_symbolic
            ,equiv
            ,a_sep) = equation_parts(input_latex,expected_latex,options)
            
        except ValueError as e:
            return e.args[0]    
        if expected_symbolic is None or expected_result_symbolic is None:
            return 'Sympy_Parsing_Error'
            
        if input_symbolic is None or input_result_symbolic is None:
            return 'false'
        
        '''if compareSides are set on both sides in student input
           and expected input must be the same
           if not can must have same numbers on different sides
           but with different signs - and +
        '''
        if options.get('compareSides'):
            La = format_sym_expression(input_symbolic,options)
            Ra = format_sym_expression(input_result_symbolic
                                                    ,options)
            Ls = format_sym_expression(expected_symbolic,options)
            Rs = format_sym_expression(expected_result_symbolic
                                                    ,options)
            # if equal sign --> sides can be swapped
            if a_sep == '=':
                equiv = (equiv
                        and ((La == Rs and Ra == Ls)
                        or (La == Ls and Ra == Rs)))
                
            else:
                equiv = (equiv
                        and (La == Ls
                        and Ra == Rs))
                
        else:
            try:
                input_one_side_1 = format_sym_expression(input_symbolic-input_result_symbolic,options)
                input_one_side_2 = format_sym_expression(input_result_symbolic-input_symbolic,options)
                expected_one_side = format_sym_expression(expected_symbolic-expected_result_symbolic,options)
        
            except TypeError:
                input_one_side_1 = (str(input_symbolic)
                            + '-'
                            + str(input_result_symbolic))
                input_one_side_2 = (str(input_result_symbolic)
                            + '-'
                            + str(input_symbolic))
                expected_one_side = (str(expected_symbolic)
                            + '-'
                            + str(expected_result_symbolic))
            # if equal sign --> sides can be swapped     
            if a_sep == '=':
                equiv = (equiv
                        and (input_one_side_2 == expected_one_side
                        or input_one_side_1 == expected_one_side))
                        
            else:
                equiv = (equiv
                        and (input_one_side_1 == expected_one_side))

        return result(xor(equiv, 'inverseResult' in options))
    
    equiv = checkOptions(input_latex,options)
    
    expected_symbolic = sympify_latex(expected_latex)
    if expected_symbolic is None:
        return 'Sympy_Parsing_Error'
    
    input_symbolic = sympify_latex(input_latex)
    if input_symbolic is None:
        return 'false'
        
    # if expected answer evaluates to boolean
    # (most prominent case is when it's an equality),
    # evaluate if input evaluates to the same value
    
    if type(expected_symbolic) == bool:
        equiv = expected_symbolic == input_symbolic
        return result(xor(equiv, 'inverseResult' in options))
    input_symbolic = format_sym_expression(input_symbolic,options)
    expected_symbolic = format_sym_expression(expected_symbolic,options)
    try:
        equiv = (input_symbolic == expected_symbolic
                and equiv)
    except:
        return 'Compare_Error'
   
    return result(xor(equiv, 'inverseResult' in options))
    

def equiv_literal(input_latex, expected_latex, options):
    ''' check equivLiteral
        Function format and simplify both input and expected
        and then compare them using str compare
        If expected contains sign, it is processed as equation
        Equation is processed by simplifing both sides and then deduction
        left side from right side on both expected and input and then
        those expressions are str compared
        If compareSides is set equations are processed by simplifing
        both sides of input and expected and then those expressions
        are str compared
    '''
    
    ''' 
        Expected result identification
        If set indications are found call setEvaluation else proceed
    '''
  
    identified = identify_expected(input_latex,expected_latex,options)
    if identified is not None:
        return identified
        
    #Swap of integral for derivation
    if re.search(r'\\int(?!_).*d[a-z]',input_latex):
        input_latex,expected_latex = derivateExpected(
                                        input_latex
                                        ,expected_latex)
    
    #Conversion of latexes to sympy objects
    ignore_trailing_zeros = 'ignoreTrailingZeros' in options
    try:
        expected_symbolic = convert(expected_latex.strip(), evaluate=False,
                    ignore_trailing_zeros=ignore_trailing_zeros,
                    keep_neg_fraction_form=True,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    euler_number=options.get('allowEulersNumber',False),
                    ignore_text=options.get('ignoreText',False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters'))
    except ValueError as e:
        return e.args[0]
        
    if expected_symbolic is None:
        return 'Sympy_Parsing_Error'
    
    try:
        input_symbolic = convert(input_latex.strip(), evaluate=False,
                    ignore_trailing_zeros=ignore_trailing_zeros,
                    keep_neg_fraction_form=True,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    euler_number=options.get('allowEulersNumber',False),
                    ignore_text=options.get('ignoreText',False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters'))
    except ValueError as e:
        return result(False)
        
    if input_symbolic is None:
        return result(False)
    
    #Preprocessing of latexes
    preprocessed_expected_latex = preprocess_latex(expected_latex,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    ignore_trailing_zeros=ignore_trailing_zeros,
                    euler_number=options.get('allowEulersNumber',False),
                    ignore_text=options.get('ignoreText',False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters'))
    preprocessed_input_latex = preprocess_latex(input_latex,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    ignore_trailing_zeros=ignore_trailing_zeros,
                    euler_number=options.get('allowEulersNumber',False),
                    ignore_text=options.get('ignoreText', False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters', False))
                    
    equiv = checkOptions(preprocessed_input_latex,options)
    
    #Removal of leading zeros
    preprocessed_input_latex = leading_zero_re.sub(
                               ''
                               ,preprocessed_input_latex)
    preprocessed_expected_latex = leading_zero_re.sub(
                                ''
                                ,preprocessed_expected_latex)
    if 'ignoreCoefficientOfOne' in options:
        preprocessed_input_latex = coefficient_of_one_re.sub(
                                   ''
                                   , preprocessed_input_latex)
        preprocessed_expected_latex = coefficient_of_one_re.sub(
                                    ''
                                    , preprocessed_expected_latex)
    '''
    In order to be processed as true both input and expected but be created from
    same parts
    '''    
    input_parts = constituent_parts_re.findall(preprocessed_input_latex)
    expected_parts = constituent_parts_re.findall(preprocessed_expected_latex)
    if 'ignoreOrder' in options:
        input_parts.sort()
        expected_parts.sort()

    equiv = (equiv
            and (str(input_symbolic)
            == str(expected_symbolic))
            and input_parts == expected_parts)
            
    return result(xor(equiv, 'inverseResult' in options))

def equiv_value(input_latex, expected_latex, options):
    ''' check equivValue
        Function format and simplify both input and expected
        and then compare them using by comparing difference
        and tolerance. If tolerance is not set then simple str comparsion
        of input and expected is used
        If compareSides is set equations are processed by simplifing
        both sides and then difference of right sides of expected and input
        is compared against tolerance
    '''
    
    ''' 
        Expected result identification
        If set indications are found call setEvaluation else proceed
    '''
  
    identified = identify_expected(input_latex,expected_latex,options)
    if identified is not None:
        return identified
        
    #Swap of integral for derivation
    if re.search(r'\\int(?!_).*d[a-z]',input_latex):
        input_latex,expected_latex = derivateExpected(
                                        input_latex
                                        ,expected_latex)
    
    try:
        expected_latex = preprocess_latex(expected_latex,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    euler_number=options.get('allowEulersNumber',False),
                    ignore_text=options.get('ignoreText',False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters'))
    except ValueError as e:
        return e.args[0]
    try:
        input_latex = preprocess_latex(input_latex,
                    thousand_sep=getThousandsSeparator(options),
                    decimal_sep=getDecimalSeparator(options),
                    ignore_text=options.get('ignoreText', False),
                    ignore_alpha=options.get('ignoreAlphabeticCharacters', False),
                    euler_number=options.get('allowEulersNumber',False))
    except ValueError as e:
        return result(False)
        
    #Format units by unit in expected latex --> convert units to normal
    #and then to unit in expected
    try:
        input_latex,expected_latex = swap_units(input_latex,expected_latex)
    except ValueError:
        return result(False)
        
    if expected_latex is None:
        return 'Parsing_Error'
        
    if input_latex is None:
        return 'false'
    
    #If compareSides is set evaluate expression as equation with symbol on left
    #and number on right, then compare those numbers with tolerance
    if 'compareSides' in options:
        try:
            (input_symbolic
            ,input_result_symbolic
            ,expected_symbolic
            ,expected_result_symbolic
            ,equiv
            ,a_sep) = equation_parts(input_latex,expected_latex,options)
            
        except ValueError as e:
            return e.args[0]
            
        if expected_symbolic is None or expected_result_symbolic is None:
            return 'Sympy_Parsing_Error'
            
        if input_symbolic is None or input_result_symbolic is None:
            return 'false'
        
        input_numeric = format_sym_expression(input_symbolic,options)
        input_result_numeric = format_sym_expression(input_result_symbolic,options)
        expected_numeric = format_sym_expression(expected_symbolic,options)
        expected_result_numeric = format_sym_expression(expected_result_symbolic,options)
        try:
            tolerance = parse_tolerance(str(options.get('tolerance', 0.0))
                                                ,expected_result_numeric)
        except ValueError as e:
            return e.args[0]
        if tolerance == 0.0:
            tolerance_check = input_result_numeric == expected_result_numeric
        else:
            tolerance_check = abs(input_result_numeric - expected_result_numeric)\
                                <= float(tolerance)
            
        try:
            equiv = (equiv
                    and input_numeric == expected_numeric
                    and bool(tolerance_check))
            
        except TypeError:
            return 'Compare_Error'
            
        return result(xor(equiv, 'inverseResult' in options))
        
    equiv = checkOptions(input_latex,options)
    expected_symbolic = sympify_latex(expected_latex)
    if expected_symbolic is None:
        return 'Sympy_Parsing_Error'
        
    input_symbolic = sympify_latex(input_latex)
    if input_symbolic is None:
        return 'false'
        
    input_numeric = format_sym_expression(input_symbolic,options)
    expected_numeric = format_sym_expression(expected_symbolic,options)
    
    tolerance = parse_tolerance(str(options.get('tolerance', 0.0))
                                ,expected_numeric)
    if tolerance == 0.0:
        tolerance_check = input_numeric == expected_numeric
    else:
        tolerance_check = abs(input_numeric - expected_numeric)\
                                        <= float(tolerance)
    try:
        equiv = equiv and bool(tolerance_check)
        
    except TypeError:
        return 'Compare_Error'
        
    return result(xor(equiv, 'inverseResult' in options))

def evaluate_graph_eq(input_latex,expected_latex,options={}):
    '''
    Function which compares input equations against expected equations
    Equations can be either standar equations or JSXGraph objects
    If we encounter object it is converted to equation with = sign.
    All equations signs are then formated using points provided as
    region points to include these points.
    Then we compare these equations
    '''
    try:
        expectedShapeEqn,expectedShapeStyle,expectedRegionPoints =\
                                    formatGraphList(expected_latex)
        expectedRegionPoints = [list(map(convert,x)) for
                                    x in expectedRegionPoints]

        eq_expected = formatEquations(expectedShapeEqn,
                                      expectedRegionPoints,
                                      expectedShapeStyle)

    except ValueError as e:
        return 'Error_Graph'

    try:
        answerShapeEqn,answerShapeStyle,answerRegionPoints =\
                                 formatGraphList(input_latex)
        answerRegionPoints = [list(map(convert,x)) for
                                    x in answerRegionPoints]
        #print(answerRegionPoints)
        eq_answer = formatEquations(answerShapeEqn,
                                    answerRegionPoints,
                                    answerShapeStyle)
    except ValueError as e:
        return result(False)

    if (len(expectedRegionPoints) < 1
        or len(expectedRegionPoints) != len(answerRegionPoints)):
        return 'Error_Point'

    #print(eq_expected,eq_answer)
    for a in eq_answer:
        for eq in eq_expected:
            if checkEquations(eq,a):
                eq_expected.remove(eq)
                break
        else:
            return result(False)

    if len(eq_expected) == 0:
        return result(True)

    else:
        return result(False)

def string_match(input_latex, expected_latex, options):
    ''' check stringMatch
    '''
    if 'ignoreLeadingAndTrailingSpaces' in options:
        input_latex = input_latex.strip()
    if 'treatMultipleSpacesAsOne' in options:
        input_latex = multiple_spaces_re.sub(' ', input_latex)
    match = input_latex == expected_latex
    return result(xor(match, 'inverseResult' in options))

#Remove non-efective parenhesis
parentheses_minus_re = re.compile(r'\((-?\d*?)\)')

def is_simplified(input_latex, expected_latex=None, options={}):
    ''' check isSimplified
    '''
    equiv = number_type(input_latex,options)
    try:
        input_symbolic = convert(input_latex, evaluate=False,
                        thousand_sep=getThousandsSeparator(options),
                        decimal_sep=getDecimalSeparator(options),
                        euler_number=options.get('allowEulersNumber',False))
    except ValueError:
        return result(False)
        
    if input_symbolic is None:
        return result(False)
        
    input_symbolic = parentheses_minus_re.sub(r'\1',str(input_symbolic))
    simplified = (equiv
                and str(input_symbolic)
                == str(expand(simplify(convert(input_latex
                ,evaluate=False
                ,thousand_sep=getThousandsSeparator(options)
                ,decimal_sep=getDecimalSeparator(options)
                ,euler_number=options.get('allowEulersNumber',False))))))
    return result(xor(simplified, 'inverseResult' in options))

def is_expanded(input_latex, expected_latex=None, options={}):
    ''' check isExpanded
    '''
    equiv = number_type(input_latex,options)
    try:
        input_symbolic = convert(input_latex,
                        thousand_sep=getThousandsSeparator(options),
                        decimal_sep=getDecimalSeparator(options),
                        euler_number=options.get('allowEulersNumber',False),
                        evaluate=False,
                        fix_parenthesis=True)
    except ValueError:
        return result(False)
        
    if input_symbolic is None:
        return result(False)
        
    expanded = (equiv
                and input_symbolic - expand(simplify(input_symbolic))) == 0
    return result(xor(expanded, 'inverseResult' in options))

def is_factorised(input_latex, expected_latex=None, options={}):
    ''' check isFactorised
    '''
    equiv = number_type(input_latex,options)
    try:
        input_symbolic = convert(input_latex,
                        evaluate=False,
                        thousand_sep=getThousandsSeparator(options),
                        decimal_sep=getDecimalSeparator(options),
                        euler_number=options.get('allowEulersNumber',False))
    except ValueError:
        return result(False)
        
    if input_symbolic is None:
        return 'false'
    
    if re.search('^\(.*[\)\)].*\)$', str(input_symbolic)):
        factorised = (equiv
                    and bool(re.search('^\(.*[\)\)].*\)$',
                    str(input_symbolic))))
    else:
        factorised = (equiv
                    and str(input_symbolic)
                    == str(factor(input_symbolic, gaussian=True)))

    return result(xor(factorised, 'inverseResult' in options))
    
def is_rationalized(input_latex, expected_latex=None, options={}):
    ''' check isRationalized
    '''
    equiv = number_type(input_latex,options)
    
    try:
        input_symbolic = convert(input_latex, evaluate=False,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False))
    except ValueError:
        return result(False)
    
    if input_symbolic is None:
        return 'Sympy_Parsing_Error'
    rationalized = fraction(input_symbolic)[1]\
                   == fraction((nsimplify(input_symbolic)))[1]
    
    return result(xor(rationalized, 'inverseResult' in options))
    
def is_rational(input_latex, expected_latex=None, options={}):
    ''' check isRational
    '''
    equiv = number_type(input_latex,options)
    equiv = is_simplified(input_latex)
    try:
        input_symbolic = convert(input_latex, evaluate=False,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get(
                             'allowEulersNumber',False))
    except ValueError:
        return result(False)
    if input_symbolic is None:
        return 'Sympy_Parsing_Error'
    rational = (ask(Q.rational_2(input_symbolic))
                and input_symbolic.is_rational_function()
                and equiv)
    return result(xor(rational, 'inverseResult' in options))

def convert_JS(input_latex, expected_latex=None, options={}):
    x,y = symbols('x y')
    try:
        eq = formatEquation(input_latex)
        if not isinstance(eq,Relational):
            eq = Eq(y,eq)
        if not eq.free_symbols.issubset([x,y]):
            raise ValueError('Free Symbols')

        eq_l = JavascriptCodePrinterMod(
                {'user_functions':known_functions}).doprint(
                    expand(simplify(eq.lhs-eq.rhs)),None)
        if re.search('Not supported in Javascript',eq_l):
            raise ValueError('Function not supported')

        rel_op = '=' if eq.rel_op == '==' else eq.rel_op
        eq_str = '{} {} {}'.format(eq_l,rel_op,'0')
    except:
        return r'Conversion_Error'

    return eq_str
    
def set_evaluation(input_latex, expected_latex=None, options={}):
    ''' check setEvaluation
        checking type and also if sets/list are the same
    '''
    if not balance_check(expected_latex):
        return 'Parenthesis_Error'
    expected_latex = replaceNonEffective(expected_latex)
    if not balance_check(input_latex):
        return result(False)
    input_latex = replaceNonEffective(input_latex)
    #Parse sets
    try:
        input_symbolic,type1 = transform_set(input_latex)
    except ValueError:
        return 'false'

    try:
        expected_symbolic,type2 = transform_set(expected_latex)  
    except ValueError:
        return 'Unreadable_List_Error'

    if 'interpretAsList' in options or 'interpretAsSet' in options:
        type1 = 'any'
        
    #Sort sets according to options
    if not 'orderedElements' in options:
        input_symbolic = [sorted(x) for x in input_symbolic]
        expected_symbolic = [sorted(x) for x in expected_symbolic]
        
    if not 'orderedPair' in options:
        input_symbolic.sort()
        expected_symbolic.sort()
        
    #Compare lists and type
    if type1 == 'any' or type2 == 'any' or type2 == type1:
        evaluation = input_symbolic == expected_symbolic
    else:
        evaluation = False
    return result(xor(evaluation, 'inverseResult' in options))

def is_true(input_latex, expected_latex=None, options={}):
    ''' check isTrue
    '''
    input_latex = preprocess_latex(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             ignore_text=options.get('ignoreText', False),
                             ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                             euler_number=options.get('allowEulersNumber',False))
    if eq_form_re.search(input_latex):
        input_latex = eq_form_re.sub(convertEquation,input_latex)
    input_symbolic = sympify_latex(input_latex)
    if input_symbolic is None:
        return 'Sympy_Parsing_Error'
    try:
        true = bool(simplify(input_symbolic))
    except TypeError:
        return 'Cannot determine the truth value'
        
    return result(xor(true, 'inverseResult' in options))

def is_unit(input_latex, expected_latex=None, options={}):
    ''' check isUnit
    '''
    try:
        input_latex = preprocess_latex(input_latex,
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   euler_number=options.get('allowEulersNumber',False),
                                   ignore_text=options.get('ignoreText', False),
                                   ignore_alpha=options.get('ignoreAlphabeticCharacters', False))
    except ValueError:
        return result(False)
    if input_latex is None or input_latex.count('.') > 1:
        return 'Sympy_Parsing_Error'
        
    #Find unit using re
    is_unit_re = re.compile(r'^(.*?) *(?:\\text\{)?(' +
                            '|'.join(options['allowedUnits']) + ')\}?$')
    unit = is_unit_re.match(input_latex)
    return result(xor(unit, 'inverseResult' in options))

#Regular expressions for pattern checks for equivSyntax
coeff = r'([A-Wa-w]|\d+(\.\d+)?|-?\d+/-?\d+|\\frac\{-?\d+\}\{-?\d+\}|'\
+ r'\d+ *(\d+/\d+|\\frac\{\d+\}\{\d+\})|)'
        
decimal_re_pattern = r'^\d+\.\d{{{}}}$'

simple_frac_re = re.compile(
r'^(-?\d+/-?\d+|-?\d+\\div-?\d+|-?\\frac\{-?\d+\}\{-?\d+\})$')

exp_re = re.compile(
r'^(([A-Wa-w]+|\d+(\.\d+)?)\^(\{.*[x-z].*\}|[x-z])|exp\(.*[x-z].*\))$')

standard_form_linear_re = re.compile(
r'^-?{} *{} *x *[+-] *{} *{} *y *= *-?{}$'.format(
coeff, times, coeff, times, coeff))

standard_form_quadratic_re = re.compile(
r'^-?{} *{} *x\^(2|[{{]2[}}]) *[+-] *{} *{} *x *[+-] *{} *= *0$'.format(
coeff, times, coeff, times, coeff))

slope_intercept_form_re = re.compile(
r'^y *= *-?{} *{} *x *[+-] *{}$'.format(
coeff, times, coeff))

point_slope_form_re = re.compile(
(r'^(\(y *[+-] *{}\)|y *([+-] *{})?)'
+ r'*= *(-?{} *{} *\(x *[+-] *{}\)|x *([+-] *{})?)$').format(
coeff, coeff, coeff, times, coeff, coeff))

pattern_dict = {
    'isSimpleFraction': simple_frac_re,
    'isMixedFraction': mixed_frac_re,
    'isExponent': exp_re,
    'isSlopeInterceptForm': slope_intercept_form_re,
    'isPointSlopeForm': point_slope_form_re
}

standard_form_dict = {
    'linear': standard_form_linear_re,
    'quadratic': standard_form_quadratic_re
}

def equiv_syntax(input_latex, expected_latex=None, options={}):
    ''' check equivSyntax depending on the pattern specified
        Checks implemented:
         - isDecimal
         - isSimpleFraction
         - isMixedFraction
         - isExponent
         - isStandardForm - linear equation or quadratic equation
         - isSlopeInterceptForm - linear equation
         - isPointSlopeForm - linear equation
    '''
    #Check type on number
    equiv = number_type(input_latex,options)
    precision = options.get('isDecimal', None)
    pattern_re = None
    if precision is not None:
        # compile regex here to account for precision
        pattern_re = re.compile(decimal_re_pattern.format(precision))
    else:
        form = options.get('isStandardForm', None)
        if form is not None:
            pattern_re = standard_form_dict[form]
        else:
            for option in pattern_dict:
                if options.get(option, False):
                    pattern_re = pattern_dict[option]
    if pattern_re:
        input_latex = input_latex.replace('\\left', '').replace('\\right', '')
        equiv = equiv and bool(pattern_re.match(input_latex.strip()))
    return result(xor(equiv, 'inverseResult' in options))

def calculate(input_latex, expected_latex, options):
    '''Caluculation of expressions using substitute of variables
    '''
    input_str, formula = input_latex.split('formula:', maxsplit=1)
    input_str = input_str.split('input:')[1]
    var_strs = input_str.split(',')

    variables = []
    for var_str in var_strs:
        if '=' in var_str:
            variable, variable_value = var_str.split('=', 1)
            variables.append({
                "id": variable,
                "value": variable_value,
            })
    #Replacing of variables
    formula = replace_variables(formula, variables)
    return equiv_symbolic(formula, expected_latex, options)
    
# end of check functions block ------------------------------------------------

# helper functions, dictionaries, and regexes for parsing options -------------

# a dictionary mapping option names to functions performing the checks
check_func = {
    'evaluateGraphEquations': evaluate_graph_eq,
    'equivSymbolic': equiv_symbolic,
    'equivLiteral': equiv_literal,
    'equivValue': equiv_value,
    'stringMatch': string_match,
    'isSimplified': is_simplified,
    'isExpanded': is_expanded,
    'isFactorised': is_factorised,
    'isRationalized': is_rationalized,
    'isRational': is_rational,
    'isTrue': is_true,
    'isUnit': is_unit,
    'equivSyntax': equiv_syntax,
    'setEvaluation': set_evaluation,
    'calculate': calculate,
    'convertLatex2Js': convert_JS
}

# a dictionary of possible main options and their respective
# sets of suboptions; will be used to check validity
# of option combinations passed to the script
allowed_options = {
    'convertLatex2Js':{},
    'evaluateGraphEquations':{},
    'equivSymbolic': {
        'allowEulersNumber',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'significantDecimalPlaces',
        'compareSides',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'equivLiteral': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'inverseResult',
        'ignoreTrailingZeros',
        'ignoreOrder',
        'ignoreCoefficientOfOne',
        'allowEulersNumber',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'equivValue': {
        'tolerance',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'compareSides',
        'inverseResult',
        'significantDecimalPlaces',
        'allowEulersNumber',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'isSimplified': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isFactorised': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isExpanded': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isRationalized': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isRational': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isTrue': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber'},
    'isUnit': {
        'allowedUnits',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber'},
    'stringMatch': {
        'ignoreLeadingAndTrailingSpaces',
        'treatMultipleSpacesAsOne',
        'inverseResult'},
    'equivSyntax': {
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'realType',
        'integerType',
        'numberType',
        'scientificType',
        'variableType',
        'complexType'},
    'setEvaluation': {
        'inverseResult',
        'orderedElements',
        'orderedPair'},
    'calculate': {},
}

no_set_decimal_separator = {main for main in allowed_options 
                            if 'setDecimalSeparator' not in allowed_options[main]}

set_thousand_separator_re = re.compile(
r"(?<=setThousandsSeparator=)?\[([ ,.']+)\]")

thousand_separator_re = re.compile(
r"'([ .,])'")

set_decimal_separator_re = re.compile(
r"(?<=setDecimalSeparator=)?'([,.])'")

tolerance_re = re.compile(
r"(?<=tolerance=)?'([,.])'")

allowed_units_re = re.compile(
r"(?<=allowedUnits=)?\[(.+?)\]")

unit_re = re.compile(
r"'(.+?)'")

non_boolean_suboption_re = re.compile(
r'^(setThousandsSeparator|setDecimalSeparator|tolerance|allowedUnits)=')

equiv_syntax_option_re_list = [re.compile(r'(isDecimal)=(\d+)')]

def sub_thousand_separator(matchobj):
    return ''.join(thousand_separator_re.findall(matchobj.group(1))
                   ).replace(',', '<COMMA>')

def sub_comma(matchobj):
    return matchobj.group(1).replace(',', '<COMMA>')

def parse_checks(options_str):
    ''' Parse option string
    '''
    # first, split groups of options
    check_list = options_str.split(';')
    # second, split each 
    check_dict = OrderedDict()
    for check_string in check_list:
        add_dict = {'setDecimalSeparator': '.'}
        if ':' in check_string:
            check_string = set_thousand_separator_re.sub(
                        sub_thousand_separator
                        ,check_string)
            check_string = set_decimal_separator_re.sub(
                        sub_comma
                        ,check_string)
            check_string = allowed_units_re.sub(
                        sub_comma,
                        check_string)

            main, add_string = check_string.split(':', maxsplit=1)
            add_list = add_string.split(',')
            for add in add_list:
                if '=' not in add:
                    add_dict[add] = True
                else:
                    add, sep = add.split('=')
                    sep = sep.replace('<COMMA>', ',')
                    if add == 'allowedUnits':
                        #Checking of allowed units
                        units = []
                        sep_tmp = []
                        for unit in sep.split(','):
                            unplurar_units = str(re.sub('([a-z]+?)(?:es|s)?',r'\1'
                                                ,unit.strip().strip("'").lower()))
                            divide_split = re.split(r'\/',unplurar_units)
                            for split_i,split in enumerate(divide_split):
                                units += re.split('\*',split)
                            sep_tmp += [unit]
                        # sanity check for allowed units
                        for unit in units:
                            if unit not in units_list:
                                raise Exception(
                                '{} is not a valid SI or US Customary unit'.format(
                                                                              unit))
                        sep = sep_tmp
                    elif add == 'tolerance':
                        if '%' not in sep:   
                            try:
                                sep = float(sep)
                            except ValueError:
                                raise Exception(
                                '{} is not a valid float value for tolerance'.format(
                                                                                sep))
                    elif add == 'significantDecimalPlaces':
                        try:
                            sep = int(sep)
                        except ValueError:
                            raise Exception(
                            '{} is not a valid int value for significantDecimalPlaces'.format(
                                                                                          sep))
                    add_dict[add] = sep
        else:
            main = check_string
        if main in no_set_decimal_separator:
            add_dict.pop('setDecimalSeparator')
        if main not in allowed_options:
            
            raise Exception(
            'Option "{}" not allowed'.format(
                                        main))

        for add in add_dict:
            if add not in allowed_options[main]:
                raise Exception(
                        'Suboption "{}" '.format(add)
                        + 'not allowed for option "{}"'.format(
                                                         main))

        if 'setDecimalSeparator' in add_dict and\
           'setThousandsSeparator' in add_dict and\
           add_dict['setDecimalSeparator'] in add_dict['setThousandsSeparator']:
                raise Exception(
                'Same decimal and thousand separators for option "{}"'.format(
                                                                         main))
                

        check_dict[main] = add_dict
    return check_dict

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
from sympy import expand, factor, logcombine, expand_log
from sympy import srepr
from sympy import nsimplify
from sympy.core import Add, Basic, Mul
from sympy.core.basic import preorder_traversal
from sympy.core.singleton import S
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
}

units_list = [v[0] for v in UNITS.values()] + [k for k in UNITS.keys()]

interval_opening = {
    '(': True,
    '[': False
}

interval_closing = {
    ')': True,
    ']': False
}

separator_pairs = {
    '>=':'<=',
    '<=':'>=',
    '>':'<',
    '<':'>',
    '=':'='
}
separator_functions = {
    '>=': 'GreaterThan(Format({})Format,Format({})Format)',
    '<=':'LessThan(Format({})Format,Format({})Format)',
    '>':'StrictGreaterThan(Format({})Format,Format({})Format)',
    '<':'StrictLessThan(Format({})Format,Format({})Format)',
    '=':'Equality(Format({})Format,Format({})Format)',
    '≠':'Unequality(Format({})Format,Format({})Format)'
}

# end of default values and dictionaries block --------------------------------

# several functions and regexes for LaTeX-to-sympy conversions ----------------
# and LaTeX-to-LaTeX preprocessing 
percent_re = re.compile(r'([0-9.]+)\s*\\%')
log_re = re.compile(r'\\log_([^{])')
multiple_spaces_re = re.compile(' {2,}')
variable_before_parentheses_re = re.compile(r'\b([abcdxyz])\(')
trailing_zeros_re = re.compile(r'(\.[0-9]*?)0+\b')
neg_fraction_re = re.compile(r'-\\frac\{(.*?)\}\{(.*?)\}')
closing_text_decorated_re = re.compile(r'\\text\{.*?\}$')
closing_text_re = re.compile(r'[^0-9.}]*$')
mixed_frac_re = re.compile(r'-?\s*[0-9]+(\s*\\frac{[^-]+?}{[^-]+?}|\s+\(?\d+\)?/\(?\d+\)?)')
mixed_fraction_error_re = re.compile(r'[0-9] *\( *[0-9]+ */ *[0-9]+ *\)')
matrix_form_re = re.compile(r'\{bmatrix\}(.*?)end{bmatrix}')
interval_form_re = re.compile(r'\s*([{}])(.*?),(.*?)([{}])\s*'.format(
re.escape(''.join(interval_opening.keys())),re.escape(''.join(interval_closing.keys()))))
set_form_re = re.compile(r'\{{\s*(?P<var>[a-zA-Z])\s*\|\s*(?:(?P<num1>\d*)\s*(?P<sign1>{0}))?\s*\1\s*(?:(?P<sign2>{0})\s*(?P<num2>\d*))?\s*\}}'.format(
'|'.join(separator_functions.keys())))
not_latex_re = re.compile(r'NotLatex:')
format_latex_re = re.compile(r'Format\((.*?)\)Format')
times = r'(\*|\\cdot ?|\\times ?)?'
def load_units(units_csv_path):
    ''' Load conversion tables for SI/US units
    '''
    conversion_table = {}
    with open(units_csv_path, 'r', encoding='utf-8') as csv_file:
        csv_file.readline()

def convert_percent(matchobj):
    found_str = matchobj.group(1)
    precision = len((found_str + '.').split('.')[1]) + 2

    return str(round(float(found_str) * 0.01, precision))

def convert_frac(matchobj):
    if matchobj.group(1) == '1':
        return ''.join((r'\frac{\one}{',
                        matchobj.group(2), r'}*(-1)'))
    return ''.join((r'\frac{', matchobj.group(1),
                    r'}{', matchobj.group(2), r'}*(-1)'))
                    
def convertMatrix(matrix_latex):
    matrix_form = [[r'Format({0})Format'.format(cell) for cell in row.split(r'&')]
                for row in matrix_latex.group(1).split(r'\\\\')]
                
    return r'NotLatex:Matrix({})'.format(matrix_form)

def convertInterval(interval_latex):
    opening = interval_opening[interval_latex.group(1)]
    closing = interval_closing[interval_latex.group(4)]
    
    return r'NotLatex:Interval(Format({1})Format,Format({2})Format,{0},{3})'.format(
    opening,*interval_latex.groups()[1:3],closing)
def convertSet(set_latex):
    input_latex = 'NotLatex:'
    variable = set_latex.group('var')
    if(set_latex.group('sign1') and set_latex.group('num1')
    and set_latex.group('sign2') and set_latex.group('num2')): 
    
        func1 = separator_functions[set_latex.group('sign1')].format(
        set_latex.group('num1'),variable)
        func2 = separator_functions[set_latex.group('sign2')].format(
        variable, set_latex.group('num2'))
    
        input_latex += r'Intersection(solveset({1},Format({0})Format,S.Reals),solveset({2},Format({0})Format,S.Reals))'.format(
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
    assert(1,2)
    
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
    units = [r'({})(?:\^{{?(-?\d*)}}?)?(\*)?'.format(u) for u in sorted(units_list,key=len,reverse=True)]
    units_re = re.compile('|'.join(units))
    output = '({})'.format(units_re.sub(convertUnits,unit_latex.group('up'))[1:])
    if unit_latex.group(2):
        output += r'/({})'.format(units_re.sub(convertUnits,unit_latex.group('down'))[2:])
    #print(output,23432444)
    return output
    
    
    
        
    
   

def replace_separators(input_latex,
                       thousand=None,
                       decimal=DEFAULT_DECIMAL_SEP):
    # replace allowed thousand and decimal separators with placeholders
    if thousand is not None:
        thousand_sep_re = re.compile(''.join((r'(?<=[0-9])([',
                                              thousand,
                                              r'])(?=[0-9]{3}([^0-9]|$))')))
        input_latex = thousand_sep_re.sub('', input_latex)
    decimal_sep_re = re.compile(r'([{}])(?=[0-9])'.format(decimal))
    input_latex = decimal_sep_re.sub(DECIMAL_SEP_PLACEHOLDER, input_latex)

    # replace not allowed thousand and decimal separators with error placeholders
    not_thousand = ''.join(sorted(set(POSSIBLE_THOUSANDS_SEP) - set(thousand or '') - set(decimal)))
    if len(not_thousand) != 0:
        not_thousand_sep_re = re.compile(''.join((r'(?<=[0-9])([',
                                                  not_thousand,
                                                  r'])(?=[0-9]{3})')))
        input_latex = not_thousand_sep_re.sub(SEP_ERROR_PLACEHOLDER, input_latex)
    not_decimal = ''.join(sorted(set(POSSIBLE_DECIMAL_SEP) - set(decimal)))
    not_decimal_sep_re = re.compile(r'([{}])(?=[0-9])'.format(decimal))
    input_latex = not_decimal_sep_re.sub(SEP_ERROR_PLACEHOLDER, input_latex)

    # replace placeholders with actual separators
    input_latex = input_latex.replace(DECIMAL_SEP_PLACEHOLDER, '.')
    return input_latex

def preprocess_latex(input_latex,
                     ignore_trailing_zeros=False,
                     keep_neg_fraction_form=False,
                     thousand_sep=None,
                     decimal_sep=DEFAULT_DECIMAL_SEP,
                     preprocess_sep=True,
                     ignore_text=False,
                     euler_number=False,
                     complex_number=False):
    ''' Convert anything that latex2sympy can't handle,
        e.g., percentages and logarithms
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
    if ignore_text:
        input_latex = closing_text_re.sub('', input_latex)
        input_latex = closing_text_decorated_re.sub('', input_latex)
    #Euler Number handling
    if euler_number:
        input_latex = re.sub(r'(\\exp|e)','E',input_latex)
    if complex_number:
        input_latex = re.sub(r'(i)','I',input_latex)
    # \left,\right
    input_latex = input_latex.replace(r'\left', '').replace(r'\right', '')
    # percent sign (\%)
    input_latex = percent_re.sub(convert_percent, input_latex)
    # \log_a -> \log_{a}
    input_latex = log_re.sub(r'\\log_{\1}', input_latex)
    # a(x+1) -> x*(x+1)
    input_latex = variable_before_parentheses_re.sub(r'\1*(', input_latex)
    # trailing zeros
    if ignore_trailing_zeros:
        input_latex = trailing_zeros_re.sub(lambda x: '' if (x.group(1) == '.') else x.group(1), input_latex)
    
    input_latex = re.sub(r'\\neq','≠',input_latex)
    # fix fractions so that -\frac{1}{2} is not converted into -1/2
    #Interval preparation
    if interval_form_re.search(input_latex) and decimal_sep != ',':
        input_latex = interval_form_re.sub(convertInterval,input_latex)
        
    if keep_neg_fraction_form:
        input_latex = neg_fraction_re.sub(convert_frac, input_latex)
        
    # Matrices preparation
    if matrix_form_re.search(input_latex):
        input_latex = matrix_form_re.sub(convertMatrix,input_latex)
    #Form perparation
    if set_form_re.search(input_latex):
        input_latex = set_form_re.sub(convertSet,input_latex)
        
    return input_latex

def sympify_latex(input_latex, evaluate=None):
    ''' Return sympy representation of a latex string if possible;
        None if conversion fails.
    '''
    try:
        # latex2sympy conversion may yield a strange result,
        # possibly because authors of latex2sympy didn't
        # took into account something that authors of sympy 
        # consider in their definition of a 'standard expression form'
        # converting it to string and sympifying again does the trick
        if not_latex_re.search(input_latex):
            input_latex = not_latex_re.sub('',input_latex)
            input_latex = format_latex_re.sub(lambda x: str(process_sympy(x.group(1))),input_latex)
        else:
            #print(input_latex)
            input_latex = str(process_sympy(input_latex))
        
        input_symbolic = sympify(input_latex,evaluate=evaluate)
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
            complex_number=False,
            euler_number=False):
    ''' All preprocessing in one function
    '''
    input_latex = preprocess_latex(input_latex,
                                   ignore_trailing_zeros=ignore_trailing_zeros,
                                   keep_neg_fraction_form=keep_neg_fraction_form,
                                   thousand_sep=thousand_sep,
                                   decimal_sep=decimal_sep,
                                   preprocess_sep=preprocess_sep,
                                   ignore_text=ignore_text,
                                   euler_number=euler_number,
                                   complex_number=complex_number)
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
            input_latex = re.sub(variable_re, '(' + str(variable['value']) + ')', input_latex)
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
# end of helper functions -----------------------------------------------------

# check functions -------------------------------------------------------------
def equiv_symbolic(input_latex, expected_latex, options):
    ''' check equivSymbolic
    '''
    equiv = True
    if 'isSimplified' in options:
        equiv = is_simplified(input_latex, expected_latex,options)
    
    input_latex = preprocess_latex(input_latex.strip(),
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   ignore_text=options.get('ignoreText', False),
                                   euler_number=options.get('allowEulersNumber',False),
                                   complex_number=options.get('complexType',False))
    if input_latex is None:
        return ERROR

    expected_latex = preprocess_latex(expected_latex.strip(),
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      euler_number=options.get('allowEulersNumber',False),
                                      complex_number=options.get('complexType',False))
    
    if 'isMixedFraction' in options and not mixed_frac_re.search(input_latex):
        equiv = False and equiv
    
    fraction_plus_re = r'(-?)\s*([0-9]+)(\s*(?=\\frac{[^-]+}{[^-]+})|\s+(?=\(?\d+\)?/\(?\d+\)?))'
    input_latex = re.sub(fraction_plus_re,lambda x: '{}{}{}'.format(x.group(1),x.group(2),x.group(1) if x.group(1) else '+'),input_latex)
    expected_latex = re.sub(fraction_plus_re,lambda x: '{}{}{}'.format(x.group(1),x.group(2),x.group(1) if x.group(1) else '+'),expected_latex)
    input_symbolic = sympify_latex(input_latex)  
    if input_symbolic is None:
        return ERROR
    expected_symbolic = sympify_latex(expected_latex)
    if 'allowEulersNumber' in options:
        input_symbolic = logcombine(expand_log(input_symbolic,force=True))
        expected_symbolic = logcombine(expand_log(expected_symbolic,force=True))
        
    # if expected answer evaluates to boolean
    # (most prominent case is when it's an equality),
    # evaluate if input evaluates to the same value
    if type(expected_symbolic) == bool:
        equiv = expected_symbolic == input_symbolic
        return result(xor(equiv, 'inverseResult' in options))
    decimal_places = options.get('significantDecimalPlaces', None)
    if decimal_places is not None:
        try:
            equiv = equiv and (round(decimal.Decimal(str(float(simplify(input_symbolic)))), decimal_places) ==
                    round(decimal.Decimal(str(float(simplify(expected_symbolic)))), decimal_places))
        except AttributeError:
            equiv = (simplify(input_symbolic) == simplfy(expected_symbolic)) and equiv
        except:
            equiv = (simplify(expand(input_symbolic)) == simplify(expand(expected_symbolic))) and equiv

    else:
        try:
            equiv = (simplify(expand(input_symbolic)) == simplify(expand(expected_symbolic))) and equiv          
        except AttributeError:
            equiv = (simplify(input_symbolic) == simplify(expected_symbolic)) and equiv
        except:
            return ERROR

    return result(xor(equiv, 'inverseResult' in options))


def equiv_symbolic_eqn(input_latex, expected_latex, options):
    ''' check equivSymbolic
    '''
    input_latex = preprocess_latex(input_latex.strip(),
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   euler_number=options.get('allowEulersNumber',False),
                                   complex_number=options.get('complexType',False))
    if input_latex is None:
        return ERROR
    expected_latex = preprocess_latex(expected_latex.strip(),
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      euler_number=options.get('allowEulersNumber',False),
                                      complex_number=options.get('complexType',False))
    separator_re = re.compile('|'.join(separator_pairs.keys()))
    try:
        a_sep = separator_re.search(input_latex).group(0)
        s_sep = separator_re.search(expected_latex).group(0)
    except ValueError:
        return ERROR
    flipped = False
    if a_sep != s_sep:
        if separator_pairs[a_sep] == s_sep:
            flipped = True
        else:
            return ERROR
                
    input_latex, input_result_latex = input_latex.split(a_sep, maxsplit=1)
    input_symbolic = sympify_latex(input_latex)
    input_result_symbolic = sympify_latex(input_result_latex)
    
    if flipped:
        input_symbolic,input_result_symbolic = input_result_symbolic ,input_symbolic
    
    if input_symbolic is None or input_result_symbolic is None:
        return ERROR

    expected_latex, expected_result_latex = expected_latex.split(s_sep, maxsplit=1)
    expected_symbolic = sympify_latex(expected_latex)
    expected_result_symbolic = sympify_latex(expected_result_latex)
    
    if options.get('compareSides'):
        
        try:
            if options.get('allowEulersNumber'):
                input_symbolic = logcombine(expand_log(input_symbolic,force=True))
                input_result_symbolic = logcombine(expand_log(input_result_symbolic,force=True))
                expected_symbolic = logcombine(expand_log(expected_symbolic,force=True))
                expected_result_symbolic = logcombine(expand_log(expected_result_symbolic,force=True))
            
            La = expand(simplify(input_symbolic))
            Ls = expand(simplify(expected_symbolic))
            Ra = expand(simplify(input_result_symbolic))
            Rs = expand(simplify(expected_result_symbolic))
            
        except AttributeError:
            La = simplify(input_symbolic)
            Ls = simplify(expected_symbolic)
            Ra = simplify(input_result_symbolic)
            Rs = simplify(expected_result_symbolic)
        
        equiv = (La == Ls and Ra == Rs)
        if a_sep == '=':
            equiv = equiv or (La == Rs and Ra == Ls)
    else:
        try:
            input_one_side_1 = expand(simplify(input_symbolic-input_result_symbolic))
            input_one_side_2 = expand(simplify(input_result_symbolic-input_symbolic))
            expected_one_side = expand(simplify(expected_symbolic-expected_result_symbolic))
        except AttributeError:
            input_one_side_1 = simplify(input_symbolic-input_result_symbolic)
            input_one_side_2 = simplify(input_result_symbolic-input_symbolic)
            expected_one_side= simplify(expected_symbolic-expected_result_symbolic)
        
        if 'allowEulersNumber' in options:
            input_one_side_1 = logcombine(expand_log(input_one_side_1,force=True))
            input_one_side_2 = logcombine(expand_log(input_one_side_2,force=True))
            expected_one_side = logcombine(expand_log(expected_one_side,force=True))
        equiv = (input_one_side_1 == expected_one_side)
        if a_sep == '=':
            equiv = equiv or (input_one_side_2 == expected_one_side)

    return result(xor(equiv, 'inverseResult' in options))

coefficient_of_one_re = re.compile(r'(?<![0-9].)1' + times + r'(?=[a-z(\\])', flags=re.IGNORECASE)
constituent_parts_re = re.compile(r'[^\s()*+-]')
leading_zero_re = re.compile(r'\b0(?=\.)')
trailing_zeros_re = re.compile(r'(\.[0-9]*?)0+\b')

def equiv_literal(input_latex, expected_latex, options):
    ''' check equivLiteral
    '''
    ignore_trailing_zeros = 'ignoreTrailingZeros' in options

    input_symbolic = convert(input_latex.strip(), evaluate=False,
                             ignore_trailing_zeros=ignore_trailing_zeros,
                             keep_neg_fraction_form=True,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    expected_symbolic = convert(expected_latex.strip(), evaluate=False,
                                ignore_trailing_zeros=ignore_trailing_zeros,
                                keep_neg_fraction_form=True,
                                thousand_sep=getThousandsSeparator(options),
                                decimal_sep=getDecimalSeparator(options),
                                euler_number=options.get('allowEulersNumber',False),
                                complex_number=options.get('complexType',False))
    
    preprocessed_input_latex = preprocess_latex(input_latex,
                                                thousand_sep=getThousandsSeparator(options),
                                                decimal_sep=getDecimalSeparator(options),
                                                ignore_trailing_zeros=ignore_trailing_zeros,
                                                euler_number=options.get('allowEulersNumber',False),
                                                complex_number=options.get('complexType',False))
    preprocessed_expected_latex = preprocess_latex(expected_latex,
                                                   thousand_sep=getThousandsSeparator(options),
                                                   decimal_sep=getDecimalSeparator(options),
                                                   ignore_trailing_zeros=ignore_trailing_zeros,
                                                   preprocess_sep=False,
                                                   euler_number=options.get('allowEulersNumber',False),
                                                   complex_number=options.get('complexType',False))

    preprocessed_input_latex = leading_zero_re.sub('', preprocessed_input_latex)
    preprocessed_expected_latex = leading_zero_re.sub('', preprocessed_expected_latex)
    if 'ignoreCoefficientOfOne' in options:
        preprocessed_input_latex = coefficient_of_one_re.sub('', preprocessed_input_latex)
        preprocessed_expected_latex = coefficient_of_one_re.sub('', preprocessed_expected_latex)
    
    input_parts = constituent_parts_re.findall(preprocessed_input_latex)
    expected_parts = constituent_parts_re.findall(preprocessed_expected_latex)
    if 'ignoreOrder' in options:
        input_parts.sort()
        expected_parts.sort()

    equiv = (str(input_symbolic) == str(expected_symbolic)) and\
            input_parts == expected_parts
    return result(xor(equiv, 'inverseResult' in options))

def equiv_value(input_latex, expected_latex, options):
    ''' check equivValue
    '''
    units = [r'{}(?:\^{{?-?\d*}}?)?(?:{})?'.format(u,times) for u in sorted(units_list,key=len,reverse=True)]
    unit_text_re = re.compile(r'(?:\\text{{)?(?P<up>(?:{0})+)(?P<down>\/(?:{0})+)?(?:}})?(?:(?=\=)|$)'.format('|'.join(units)))
    input_latex = unit_text_re.sub(convertComplexUnit,input_latex)
    expected_latex = unit_text_re.sub(convertComplexUnit,expected_latex)
    #print(input_latex,expected_latex)
    input_latex = preprocess_latex(input_latex,
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   euler_number=options.get('allowEulersNumber',False),
                                   complex_number=options.get('complexType',False))
    if input_latex is None:
        return ERROR
    expected_latex = preprocess_latex(expected_latex,
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      euler_number=options.get('allowEulersNumber',False),
                                      complex_number=options.get('complexType',False))

    if 'compareSides' in options:
        input_latex, input_result_latex = input_latex.split('=', maxsplit=1)
        input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
        input_result_symblic = convert(input_result_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
        if input_symbolic is None or input_result_symblic is None:
            return ERROR

        expected_latex, expected_result_latex = expected_latex.split('=', maxsplit=1)
        expected_symbolic = convert(expected_latex,
                                    thousand_sep=getThousandsSeparator(options),
                                    decimal_sep=getDecimalSeparator(options),
                                    preprocess_sep=False,
                                    euler_number=options.get('allowEulersNumber',False),
                                    complex_number=options.get('complexType',False))
        expected_result_symbolic = convert(expected_result_latex,
                                    thousand_sep=getThousandsSeparator(options),
                                    decimal_sep=getDecimalSeparator(options),
                                    preprocess_sep=False,
                                    euler_number=options.get('allowEulersNumber',False),
                                    complex_number=options.get('complexType',False))      

        decimal_places = options.get('significantDecimalPlaces', None)
        if decimal_places is not None:
            input_numeric = expand(simplify(input_symbolic))
            try:
                input_result_numeric = round(decimal.Decimal(str(float(simplify(input_result_symblic)))), decimal_places)
            except:
                input_result_numeric = simplify(input_result_symblic)
            expected_numeric = expand(simplify(expected_symbolic))
            try:
                expected_result_numeric = round(decimal.Decimal(str(float(simplify(expected_result_symbolic)))), decimal_places)
            except:
                expected_result_numeric = simplify(expected_result_symbolic)
        else:
            input_numeric = expand(simplify(input_symbolic))
            input_result_numeric = simplify(input_result_symblic)
            expected_numeric = expand(simplify(expected_symbolic))
            expected_result_numeric = simplify(expected_result_symbolic)
        equiv = input_numeric == expected_numeric and\
                abs(input_result_numeric - expected_result_numeric) <= options.get('tolerance', 0.0)
        return result(xor(equiv, 'inverseResult' in options))

    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    #print(input_latex)
    expected_symbolic = convert(expected_latex,
                                thousand_sep=getThousandsSeparator(options),
                                decimal_sep=getDecimalSeparator(options),
                                preprocess_sep=False,
                                euler_number=options.get('allowEulersNumber',False),
                                complex_number=options.get('complexType',False))
    decimal_places = options.get('significantDecimalPlaces', None)
    if decimal_places is not None:
        try:
            input_numeric = round(decimal.Decimal(str(float(simplify(input_symbolic)))), decimal_places)
            expected_numeric = round(decimal.Decimal(str(float(simplify(expected_symbolic)))), decimal_places)
        except:
            input_numeric = simplify(input_symbolic)
            expected_numeric = simplify(expected_symbolic)
    else:
        input_numeric = simplify(input_symbolic)
        expected_numeric = simplify(expected_symbolic)
    equiv = abs(simplify(input_numeric - expected_numeric)) <= options.get('tolerance', 0.0)
    #print(equiv)
    return result(xor(equiv, 'inverseResult' in options))

def string_match(input_latex, expected_latex, options):
    ''' check stringMatch
    '''
    if 'ignoreLeadingAndTrailingSpaces' in options:
        input_latex = input_latex.strip()
    if 'treatMultipleSpacesAsOne' in options:
        input_latex = multiple_spaces_re.sub(' ', input_latex)
    match = input_latex == expected_latex
    return result(xor(match, 'inverseResult' in options))

parentheses_minus_re = re.compile(r'\((-?d*?)\)')
#parentheses_around = re.compile(r'(^\s*|\+\s*)\((.*?)\)(\s*\+|\s*$)')
#Remove non-efective parenheses might be used later
def is_simplified(input_latex, expected_latex=None, options={}):
    ''' check isSimplified
    '''
    input_symbolic = convert(input_latex, evaluate=False,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    
    input_symbolic = parentheses_minus_re.sub(r'\1',str(input_symbolic))
    simplified = str(input_symbolic) ==\
                 str(expand(simplify(convert(input_latex,
                                     thousand_sep=getThousandsSeparator(options),
                                     decimal_sep=getDecimalSeparator(options),
                                     euler_number=options.get('allowEulersNumber',False),
                                     complex_number=options.get('complexType',False)))))
    return result(xor(simplified, 'inverseResult' in options))

def is_expanded(input_latex, expected_latex=None, options={}):
    ''' check isExpanded
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    expanded = input_symbolic - expand(simplify(input_symbolic)) == 0
    return result(xor(expanded, 'inverseResult' in options))

def is_factorised(input_latex, expected_latex=None, options={}):
    ''' check isFactorised
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    
    if re.search('^\(.*[\)\)].*\)$', str(input_symbolic)):
        factorised = bool( re.search('^\(.*[\)\)].*\)$', str(input_symbolic)) )
    else:
        factorised = str(input_symbolic) == str(factor(input_symbolic, gaussian=True))

    return result(xor(factorised, 'inverseResult' in options))

def set_evaluation(input_latex, expected_latex=None, options={}):
    ''' check setEvaluation
    '''
    input_symbolic = list(map(int, input_latex.split(',')))
    expected_latex = list(map(int, expected_latex.split(',')))

    if input_symbolic is None:
        return ERROR

    input_symbolic.sort()
    expected_latex.sort()

    evaluation = input_symbolic == expected_latex
    return result(xor(evaluation, 'inverseResult' in options))

def is_true(input_latex, expected_latex=None, options={}):
    ''' check isTrue
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             euler_number=options.get('allowEulersNumber',False),
                             complex_number=options.get('complexType',False))
    if input_symbolic is None:
        return ERROR
    true = bool(simplify(input_symbolic))
    return result(xor(true, 'inverseResult' in options))

def is_unit(input_latex, expected_latex=None, options={}):
    ''' check isUnit
    '''
    input_latex = preprocess_latex(input_latex,
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   euler_number=options.get('allowEulersNumber',False),
                                   complex_number=options.get('complexType',False))
    if input_latex is None or input_latex.count('.') > 1:
        return ERROR
    is_unit_re = re.compile(r'^(.*?) *(?:\\text\{)?(' +
                            '|'.join(options['allowedUnits']) + ')\}?$')
    unit = is_unit_re.match(input_latex)
    return result(xor(unit, 'inverseResult' in options))

# regular expressions for pattern checks for equivSyntax
coeff = r'([A-Wa-w]|\d+(\.\d+)?|-?\d+/-?\d+|\\frac\{-?\d+\}\{-?\d+\}|\d+ *(\d+/\d+|\\frac\{\d+\}\{\d+\})|)'
decimal_re_pattern = r'^\d+\.\d{{{}}}$'
simple_frac_re = re.compile(r'^(-?\d+/-?\d+|-?\d+\\div-?\d+|-?\\frac\{-?\d+\}\{-?\d+\})$')
exp_re = re.compile(r'^(([A-Wa-w]+|\d+(\.\d+)?)\^(\{.*[x-z].*\}|[x-z])|exp\(.*[x-z].*\))$')
standard_form_linear_re = re.compile(r'^-?{} *{} *x *[+-] *{} *{} *y *= *-?{}$'.format(coeff, times, coeff, times, coeff))
standard_form_quadratic_re = re.compile(r'^-?{} *{} *x\^(2|[{{]2[}}]) *[+-] *{} *{} *x *[+-] *{} *= *0$'.format(coeff, times, coeff, times, coeff))
slope_intercept_form_re = re.compile(r'^y *= *-?{} *{} *x *[+-] *{}$'.format(coeff, times, coeff))
point_slope_form_re = re.compile(r'^(\(y *[+-] *{}\)|y *([+-] *{})?) *= *(-?{} *{} *\(x *[+-] *{}\)|x *([+-] *{})?)$'.format(coeff, coeff, coeff, times, coeff, coeff))

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
    precision = options.get('isDecimal', None)
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
    input_latex = input_latex.replace('\\left', '').replace('\\right', '')
    equiv = bool(pattern_re.match(input_latex.strip()))
    return result(xor(equiv, 'inverseResult' in options))

def calculate(input_latex, expected_latex, options):
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

    formula = replace_variables(formula, variables)
    return equiv_symbolic(formula, expected_latex, options)
    
# end of check functions block ------------------------------------------------

# helper functions, dictionaries, and regexes for parsing options -------------

# a dictionary mapping option names to functions performing the checks
check_func = {
    'equivSymbolic': equiv_symbolic,
    'equivSymbolicEqn': equiv_symbolic_eqn,
    'equivLiteral': equiv_literal,
    'equivValue': equiv_value,
    'stringMatch': string_match,
    'isSimplified': is_simplified,
    'isExpanded': is_expanded,
    'isFactorised': is_factorised,
    'isTrue': is_true,
    'isUnit': is_unit,
    'equivSyntax': equiv_syntax,
    'setEvaluation': set_evaluation,
    'calculate': calculate,
}

# a dictionary of possible main options and their respective
# sets of suboptions; will be used to check validity
# of option combinations passed to the script
allowed_options = {
    'equivSymbolic': {
        'allowEulersNumber',
        'isMixedFraction',
        'isSimplified',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreText',
        'significantDecimalPlaces',
        'complexType'},
    'equivSymbolicEqn': {
        'compareSides',
        'allowEulersNumber',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'complexType'},
    'equivLiteral': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreTrailingZeros',
        'ignoreOrder',
        'ignoreCoefficientOfOne',
        'allowEulersNumber',
        'complexType'},
    'equivValue': {
        'tolerance',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'compareSides',
        'inverseResult',
        'significantDecimalPlaces',
        'allowEulersNumber',
        'complexType'},
    'isSimplified': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'isFactorised': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'realType',
        'integerType',
        'complexType',
        'allowEulersNumber'},
    'isExpanded': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'complexType'},
    'isTrue': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'significantDecimalPlaces',
        'allowEulersNumber',
        'complexType'},
    'isUnit': {
        'allowedUnits',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'complexType'},
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
        'isPointSlopeForm'},
    'setEvaluation': {
        'inverseResult'},
    'calculate': {},
}

no_set_decimal_separator = {main for main in allowed_options 
                            if 'setDecimalSeparator' not in allowed_options[main]}

set_thousand_separator_re = re.compile(r"(?<=setThousandsSeparator=)?\[([ ,.']+)\]")
thousand_separator_re = re.compile(r"'([ .,])'")
set_decimal_separator_re = re.compile(r"(?<=setDecimalSeparator=)?'([,.])'")

tolerance_re = re.compile(r"(?<=tolerance=)?'([,.])'")
allowed_units_re = re.compile(r"(?<=allowedUnits=)?\[(.+?)\]")
unit_re = re.compile(r"'(.+?)'")
non_boolean_suboption_re = re.compile(r'^(setThousandsSeparator|setDecimalSeparator|tolerance|allowedUnits)=')
equiv_syntax_option_re_list = [re.compile(r'(isDecimal)=(\d+)')]

def sub_thousand_separator(matchobj):
    return ''.join(thousand_separator_re.findall(matchobj.group(1))).replace(',', '<COMMA>')

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
            check_string = set_thousand_separator_re.sub(sub_thousand_separator, check_string)
            check_string = set_decimal_separator_re.sub(sub_comma, check_string)
            check_string = allowed_units_re.sub(sub_comma, check_string)

            main, add_string = check_string.split(':', maxsplit=1)
            add_list = add_string.split(',')
            for add in add_list:
                if '=' not in add:
                    add_dict[add] = True
                else:
                    add, sep = add.split('=')
                    sep = sep.replace('<COMMA>', ',')
                    if add == 'allowedUnits':
                        units = []
                        sep_tmp = []
                        for unit in sep.split(','):
                            unplurar_units = str(re.sub('([a-z]+?)(?:es|s)?',r'\1',unit.strip().strip("'").lower()))
                            divide_split = re.split(r'\/',unplurar_units)
                            for split_i,split in enumerate(divide_split):
                                units += re.split('\*',split)
                            sep_tmp += [unit]
                        # sanity check for allowed units
                        for unit in units:
                            if unit not in units_list:
                                raise Exception('{} is not a valid SI or US Customary unit'.format(unit))
                        sep = sep_tmp
                    elif add == 'tolerance':
                        try:
                            sep = float(sep)
                        except ValueError:
                            raise Exception('{} is not a valid float value for tolerance'.format(sep))
                    elif add == 'significantDecimalPlaces':
                        try:
                            sep = int(sep)
                        except ValueError:
                            raise Exception('{} is not a valid int value for significantDecimalPlaces'.format(sep))
                    add_dict[add] = sep
        else:
            main = check_string
        if main in no_set_decimal_separator:
            add_dict.pop('setDecimalSeparator')

        if main not in allowed_options:
            raise Exception('Option "{}" not allowed'.format(main))

        for add in add_dict:
            if add not in allowed_options[main]:
                raise Exception('Suboption "{}" '.format(add) + 'not allowed for option "{}"'.format(main))

        if 'setDecimalSeparator' in add_dict and\
           'setThousandsSeparator' in add_dict and\
           add_dict['setDecimalSeparator'] in add_dict['setThousandsSeparator']:
                raise Exception('Same decimal and thousand separators for option "{}"'.format(main))
                

        check_dict[main] = add_dict
    return check_dict

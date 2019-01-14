#!/usr/bin/env python3

import re
import os
import sys
from collections import OrderedDict
import decimal
decimal.getcontext().rounding = decimal.ROUND_HALF_UP

from sympy import sympify
from sympy import simplify
from sympy import expand, factor
from sympy import srepr
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

# end of default values and dictionaries block --------------------------------

# several functions and regexes for LaTeX-to-sympy conversions ----------------
# and LaTeX-to-LaTeX preprocessing 
percent_re = re.compile(r'([0-9.]+)\s*\\%')
log_re = re.compile(r'\\log_([^{])')
multiple_spaces_re = re.compile(' {2,}')
variable_before_parentheses_re = re.compile(r'\b([abcdxyz])\(')
trailing_zeros_re = re.compile(r'(\.[0-9]*?)(0+)\b')
trailing_decimal_sep_re = re.compile(r'(\.)(?![0-9])')
neg_fraction_re = re.compile(r'-\\frac\{(.*?)\}\{(.*?)\}')
closing_text_decorated_re = re.compile(r'\\text\{.*?\}$')
closing_text_re = re.compile(r'[^0-9.}]*$')

mixed_fraction_error_re = re.compile(r'[0-9] *\( *[0-9]+ */ *[0-9]+ *\)')

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
                     ignore_text=False):
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

    # percent sign (\%)
    input_latex = percent_re.sub(convert_percent, input_latex)
    # \log_a -> \log_{a}
    input_latex = log_re.sub(r'\\log_{\1}', input_latex)
    # a(x+1) -> x*(x+1)
    input_latex = variable_before_parentheses_re.sub(r'\1*(', input_latex)
    # trailing zeros
    if ignore_trailing_zeros:
        input_latex = trailing_zeros_re.sub(r'\1', input_latex)
        input_latex = trailing_decimal_sep_re.sub('', input_latex)

    # fix fractions so that -\frac{1}{2} is not converted into -1/2
    if keep_neg_fraction_form:
        input_latex = neg_fraction_re.sub(convert_frac, input_latex)

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
        input_symbolic = sympify(str(process_sympy(input_latex)),
                                 evaluate=evaluate)
    except:
        return None
    return input_symbolic

def convert(input_latex, evaluate=None,
            ignore_trailing_zeros=False,
            keep_neg_fraction_form=False,
            thousand_sep=None,
            decimal_sep=DEFAULT_DECIMAL_SEP,
            preprocess_sep=True,
            ignore_text=False):
    ''' All preprocessing in one function
    '''
    input_latex = preprocess_latex(input_latex,
                                   ignore_trailing_zeros=ignore_trailing_zeros,
                                   keep_neg_fraction_form=keep_neg_fraction_form,
                                   thousand_sep=thousand_sep,
                                   decimal_sep=decimal_sep,
                                   preprocess_sep=preprocess_sep,
                                   ignore_text=ignore_text)
    if input_latex is None:
        return None
    input_symbolic = sympify_latex(input_latex, evaluate=evaluate)
    return input_symbolic
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
    input_latex = preprocess_latex(input_latex.strip(),
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options),
                                   ignore_text=options.get('ignoreText', False))
    if input_latex is None:
        return ERROR

    expected_latex = preprocess_latex(expected_latex.strip(),
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      preprocess_sep=False)

    # if suboption 'compareSides' is used,
    # we expect the expressions to be equalities
    if 'compareSides' in options:
        input_latex, input_result_latex = input_latex.split('=', maxsplit=1)
        input_symbolic = sympify_latex(input_latex)
        input_result_symbolic = sympify_latex(input_result_latex)
        if input_symbolic is None or input_result_symbolic is None:
            return ERROR

        expected_latex, expected_result_latex = expected_latex.split('=', maxsplit=1)
        expected_symbolic = sympify_latex(expected_latex)
        expected_result_symbolic = sympify_latex(expected_result_latex)

        decimal_places = options.get('significantDecimalPlaces', None)
        if decimal_places is not None:
            equiv = expand(simplify(input_symbolic)) ==\
                    expand(simplify(expected_symbolic)) and\
                    round(decimal.Decimal(str(float(simplify(input_result_symbolic))))) ==\
                    round(decimal.Decimal(str(float(simplify(expected_result_symbolic)))))
        else:
            equiv = expand(simplify(input_symbolic)) ==\
                    expand(simplify(expected_symbolic)) and\
                    simplify(input_result_symbolic) ==\
                    simplify(expected_result_symbolic)

        return result(xor(equiv, 'inverseResult' in options))

    input_symbolic = sympify_latex(input_latex)
    if input_symbolic is None:
        return ERROR

    expected_symbolic = sympify_latex(expected_latex)

    # if expected answer evaluates to boolean
    # (most prominent case is when it's an equality),
    # evaluate if input evaluates to the same value
    if type(expected_symbolic) == bool:
        equiv = expected_symbolic == input_symbolic
        return result(xor(equiv, 'inverseResult' in options))

    decimal_places = options.get('significantDecimalPlaces', None)
    if decimal_places is not None:
        equiv = round(decimal.Decimal(str(float(simplify(input_symbolic)))), decimal_places) ==\
                round(decimal.Decimal(str(float(simplify(expected_symbolic)))), decimal_places)
    else:
        try:
            equiv = expand(simplify(input_symbolic)) -\
                    expand(simplify(expected_symbolic)) == 0
        except TypeError:
            return ERROR

    return result(xor(equiv, 'inverseResult' in options))

coefficient_of_one_re = re.compile(r'(?<![0-9].)1' + times + r'(?=[a-z(\\])', flags=re.IGNORECASE)
constituent_parts_re = re.compile(r'[^\s()*+-]')
leading_zero_re = re.compile(r'\b0(?=\.)')
trailing_zeros_re = re.compile(r'(?<=\.)([1-9]*)0+\b')

def equiv_literal(input_latex, expected_latex, options):
    ''' check equivLiteral
    '''
    if 'allowInterval' in options:
        input_latex = preprocess_latex(input_latex,
                                       thousand_sep=getThousandsSeparator(options),
                                       decimal_sep=getDecimalSeparator(options))
        if input_latex is None:
            return ERROR
        expected_latex = preprocess_latex(expected_latex,
                                        thousand_sep=getThousandsSeparator(options),
                                        decimal_sep=getDecimalSeparator(options),
                                        preprocess_sep=False)

        equiv = str(input_latex) == str(expected_latex)
    else:
        ignore_trailing_zeros = 'ignoreTrailingZeros' in options

        input_symbolic = convert(input_latex.strip(), evaluate=False,
                                 ignore_trailing_zeros=ignore_trailing_zeros,
                                 keep_neg_fraction_form=True,
                                 thousand_sep=getThousandsSeparator(options),
                                 decimal_sep=getDecimalSeparator(options))
        if input_symbolic is None:
            return ERROR

        expected_symbolic = convert(expected_latex.strip(), evaluate=False,
                                    ignore_trailing_zeros=ignore_trailing_zeros,
                                    keep_neg_fraction_form=True,
                                    thousand_sep=getThousandsSeparator(options),
                                    decimal_sep=getDecimalSeparator(options),
                                    preprocess_sep=False)

        preprocessed_input_latex = preprocess_latex(input_latex,
                                                    thousand_sep=getThousandsSeparator(options),
                                                    decimal_sep=getDecimalSeparator(options))

        preprocessed_expected_latex = preprocess_latex(expected_latex,
                                                       thousand_sep=getThousandsSeparator(options),
                                                       decimal_sep=getDecimalSeparator(options),
                                                       preprocess_sep=False)

        preprocessed_input_latex = leading_zero_re.sub('', preprocessed_input_latex)
        preprocessed_expected_latex = leading_zero_re.sub('', preprocessed_expected_latex)

        if 'ignoreTrailingZeros' in options:
            preprocessed_input_latex = trailing_zeros_re.sub(r'\1', preprocessed_input_latex)
            preprocessed_input_latex = trailing_decimal_sep_re.sub(r'\1', preprocessed_input_latex)
            preprocessed_expected_latex = trailing_zeros_re.sub(r'\1', preprocessed_expected_latex)
            preprocessed_expected_latex = trailing_decimal_sep_re.sub(r'\1', preprocessed_expected_latex)

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
    unit_re = re.compile(r'^(.*?) *\\text\{(' +\
                         '|'.join(sorted(UNITS, key=len, reverse=True)) +\
                         ')\}$')

    input_latex = preprocess_latex(input_latex,
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options))
    if input_latex is None:
        return ERROR
    expected_latex = preprocess_latex(expected_latex,
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      preprocess_sep=False)

    expected_unit_match = unit_re.match(expected_latex)
    if expected_unit_match is not None:
        input_unit_match = unit_re.match(input_latex)
        if input_unit_match is not None:
            try:
                input_converted_value = float(simplify(sympify_latex(input_unit_match.group(1)))) *\
                                        UNITS[input_unit_match.group(2)][2]
                input_converted_unit = UNITS[input_unit_match.group(2)][1]
                expected_converted_value = float(simplify(sympify_latex(expected_unit_match.group(1)))) *\
                                           UNITS[expected_unit_match.group(2)][2]
                expected_converted_unit = UNITS[expected_unit_match.group(2)][1]
            except ValueError:
                return ERROR

            equiv = input_converted_value == expected_converted_value and\
                    input_converted_unit == expected_converted_unit

            return result(xor(equiv, 'inverseResult' in options))
        else:
            return 'false'

    if 'compareSides' in options:
        input_latex, input_result_latex = input_latex.split('=', maxsplit=1)
        input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False))
        input_result_symblic = convert(input_result_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False))
        if input_symbolic is None or input_result_symblic is None:
            return ERROR

        expected_latex, expected_result_latex = expected_latex.split('=', maxsplit=1)
        expected_symbolic = convert(expected_latex,
                                    thousand_sep=getThousandsSeparator(options),
                                    decimal_sep=getDecimalSeparator(options),
                                    preprocess_sep=False)
        expected_result_symbolic = convert(expected_result_latex,
                                    thousand_sep=getThousandsSeparator(options),
                                    decimal_sep=getDecimalSeparator(options),
                                    preprocess_sep=False)      

        decimal_places = options.get('significantDecimalPlaces', None)
        if decimal_places is not None:
            input_numeric = expand(simplify(input_symbolic))
            input_result_numeric = round(decimal.Decimal(str(float(simplify(input_result_symblic)))), decimal_places)
            expected_numeric = expand(simplify(expected_symbolic))
            expected_result_numeric = round(decimal.Decimal(str(float(simplify(expected_result_symbolic)))), decimal_places)
        else:
            input_numeric = expand(simplify(input_symbolic))
            input_result_numeric = simplify(input_symbolic)
            expected_numeric = expand(simplify(expected_symbolic))
            expected_result_numeric = simplify(expected_symbolic)

        equiv = input_numeric == expected_numeric and\
                abs(input_result_numeric - expected_result_numeric) <= options.get('tolerance', 0.0)
        return result(xor(equiv, 'inverseResult' in options))

    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             preprocess_sep=False,
                             ignore_text=options.get('ignoreText', False))
    if input_symbolic is None:
        return ERROR

    expected_symbolic = convert(expected_latex,
                                thousand_sep=getThousandsSeparator(options),
                                decimal_sep=getDecimalSeparator(options),
                                preprocess_sep=False)

    decimal_places = options.get('significantDecimalPlaces', None)
    if decimal_places is not None:
        input_numeric = round(decimal.Decimal(str(float(simplify(input_symbolic)))), decimal_places)
        expected_numeric = round(decimal.Decimal(str(float(simplify(expected_symbolic)))), decimal_places)
    else:
        input_numeric = simplify(input_symbolic)
        expected_numeric = simplify(expected_symbolic)

    equiv = abs(input_numeric - expected_numeric) <= options.get('tolerance', 0.0)
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

def is_simplified(input_latex, expected_latex=None, options={}):
    ''' check isSimplified
    '''
    input_symbolic = convert(input_latex, evaluate=False,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options))
    if input_symbolic is None:
        return ERROR
    simplified = str(input_symbolic) ==\
                 str(expand(simplify(convert(input_latex,
                                     thousand_sep=getThousandsSeparator(options),
                                     decimal_sep=getDecimalSeparator(options)))))
    return result(xor(simplified, 'inverseResult' in options))

def is_expanded(input_latex, expected_latex=None, options={}):
    ''' check isExpanded
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options))
    if input_symbolic is None:
        return ERROR
    expanded = input_symbolic - expand(simplify(input_symbolic)) == 0
    return result(xor(expanded, 'inverseResult' in options))

def is_factorised(input_latex, expected_latex=None, options={}):
    ''' check isFactorised
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options))
    if input_symbolic is None:
        return ERROR
    factorised = input_symbolic == factor(input_symbolic)
    return result(xor(factorised, 'inverseResult' in options))

def is_true(input_latex, expected_latex=None, options={}):
    ''' check isTrue
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options))
    if input_symbolic is None:
        return ERROR
    true = bool(simplify(input_symbolic))
    return result(xor(true, 'inverseResult' in options))

def is_unit(input_latex, expected_latex=None, options={}):
    ''' check isUnit
    '''
    input_latex = preprocess_latex(input_latex,
                                   thousand_sep=getThousandsSeparator(options),
                                   decimal_sep=getDecimalSeparator(options))
    if input_latex is None or input_latex.count('.') > 1:
        return ERROR
    is_unit_re = re.compile(r'^(.*?) *\\text\{(' +
                            '|'.join(options['allowedUnits']) + ')\}$')
    unit = is_unit_re.match(input_latex) is not None
    return result(xor(unit, 'inverseResult' in options))

# regular expressions for pattern checks for equivSyntax
coeff = r'([A-Wa-w]|\d+(\.\d+)?|-?\d+/-?\d+|\\frac\{-?\d+\}\{-?\d+\}|\d+ *(\d+/\d+|\\frac\{\d+\}\{\d+\})|)'
decimal_re_pattern = r'^\d+\.\d{{{}}}$'
simple_frac_re = re.compile(r'^(-?\d+/-?\d+|-?\\frac\{-?\d+\}\{-?\d+\})$')
mixed_frac_re = re.compile(r'^-?\d+ *(\d+/\d+|\\frac\{\d+\}\{\d+\})$')
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

    equiv = pattern_re.match(input_latex.strip()) is not None
    return result(xor(equiv, 'inverseResult' in options))

# end of check functions block ------------------------------------------------

# helper functions, dictionaries, and regexes for parsing options -------------

# a dictionary mapping option names to functions performing the checks
check_func = {
    'equivSymbolic': equiv_symbolic,
    'equivLiteral': equiv_literal,
    'equivValue': equiv_value,
    'stringMatch': string_match,
    'isSimplified': is_simplified,
    'isExpanded': is_expanded,
    'isFactorised': is_factorised,
    'isTrue': is_true,
    'isUnit': is_unit,
    'equivSyntax': equiv_syntax,
}

# a dictionary of possible main options and their respective
# sets of suboptions; will be used to check validity
# of option combinations passed to the script
allowed_options = {
    'equivSymbolic': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreText',
        'compareSides',
        'significantDecimalPlaces',
        'useEulerNumber'},
    'equivLiteral': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreTrailingZeros',
        'ignoreOrder',
        'ignoreCoefficientOfOne',
        'allowInterval'},
    'equivValue': {
        'tolerance',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'compareSides',
        'inverseResult',
        'significantDecimalPlaces'},
    'isSimplified': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'isFactorised': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'isExpanded': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'isTrue': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'isUnit': {
        'allowedUnits',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
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
                        sep = sorted(unit.strip().strip("'").lower() for unit in sep.split(','))
                        # sanity check for allowed units
                        if any(unit not in UNITS for unit in sep):
                            raise Exception('{} is not a valid SI or US Customary unit'.format(unit))
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

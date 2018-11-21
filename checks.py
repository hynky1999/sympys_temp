import re
import sys

from sympy import sympify
from sympy import simplify
from sympy import expand, factor
from sympy import srepr
from latex2sympy.process_latex import process_sympy

# several functions and regexes for latex to sympy conversions
percent_re = re.compile(r'([0-9.]+)\s*\\%')
log_re = re.compile(r'\\log_([^{])')
multiple_spaces_re = re.compile(' {2,}')
variable_before_parentheses_re = re.compile(r'\b([abcdxyz])\(')
trailing_zeros_re = re.compile(r'(\.[0-9]*?)(0+)\b')
neg_fraction_re = re.compile(r'-\\frac\{(.*?)\}\{(.*?)\}')

DEFAULT_THOUSANDS_SEP = ','
DEFAULT_DECIMAL_SEP = '.'
POSSIBLE_THOUSANDS_SEP = ',. '
POSSIBLE_DECIMAL_SEP = ',.'
THOUSANDS_SEP_PLACEHOLDER = '<THOUSANDSEP>'
DECIMAL_SEP_PLACEHOLDER = '<DECIMALSEP>'
SEP_ERROR_PLACEHOLDER = '<SEPERROR>'

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
    #input_latex = input_latex.replace(THOUSANDS_SEP_PLACEHOLDER, ',')
    input_latex = input_latex.replace(DECIMAL_SEP_PLACEHOLDER, '.')
    return input_latex

def preprocess_latex(input_latex,
                     ignore_trailing_zeros=False,
                     keep_neg_fraction_form=False,
                     thousand_sep=None,
                     decimal_sep=DEFAULT_DECIMAL_SEP,
                     preprocess_sep=True):
    ''' Convert anything that latex2sympy can't handle,
        e.g., percentages and logarithms
    '''
    # replace decimal separators from allowed to appropriate,
    # report errors if there are separators that are not allowed
    if preprocess_sep:
        input_latex = replace_separators(input_latex,
                                         thousand=thousand_sep,
                                         decimal=decimal_sep)
        if SEP_ERROR_PLACEHOLDER in input_latex:
            return None

    # percent sign (\%)
    input_latex = percent_re.sub(convert_percent, input_latex)
    # \log_a -> \log_{a}
    input_latex = log_re.sub(r'\\log_{\1}', input_latex)
    # a(x+1) -> x*(x+1)
    input_latex = variable_before_parentheses_re.sub(r'\1*(', input_latex)
    # trailing zeros
    if ignore_trailing_zeros:
        input_latex = trailing_zeros_re.sub(r'\1', input_latex)
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
            preprocess_sep=True):
    ''' All preprocessing in one function
    '''
    input_latex = preprocess_latex(input_latex,
                                   ignore_trailing_zeros=ignore_trailing_zeros,
                                   keep_neg_fraction_form=keep_neg_fraction_form,
                                   thousand_sep=thousand_sep,
                                   decimal_sep=decimal_sep,
                                   preprocess_sep=preprocess_sep)
    if input_latex is None:
        return None
    input_symbolic = sympify_latex(input_latex, evaluate=evaluate)
    return input_symbolic

# a couple of helper functions to wrap the return
# results in a more neat form
def xor(a, b):
    ''' Logical xor one-liner
    '''
    return a and not b or not a and b

def result(bool_result):
    ''' Convert bool value to lowercase str
    ''' 
    return str(bool_result).lower()


# check functions corresponding to main option
def equiv_symbolic(input_latex, expected_latex, options):
    ''' check equivSymbolic
    '''
    input_latex = preprocess_latex(input_latex,
                                   thousand_sep=options.get('setThousandsSeparator', ','),
                                   decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_latex is None:
        return 'error'
    expected_latex = preprocess_latex(expected_latex,
                                      thousand_sep=options.get('setThousandsSeparator', ','),
                                      decimal_sep=options.get('setDecimalSeparator', '.'),
                                      preprocess_sep=False)

    if 'compareSides' in options:
        input_latex, input_result_latex = input_latex.split('=')
        input_symbolic = sympify_latex(input_latex)
        input_result_symbolic = sympify_latex(input_result_latex)
        if input_symbolic is None or input_result_symbolic is None:
            return 'error'

        expected_latex, expected_result_latex = expected_latex.split('=')
        expected_symbolic = sympify_latex(expected_latex)
        expected_result_symbolic = sympify_latex(expected_result_latex)

        equiv = expand(simplify(input_symbolic)) ==\
                expand(simplify(expected_symbolic)) and\
                simplify(input_result_symbolic) ==\
                simplify(expected_result_symbolic)
        return result(xor(equiv, 'inverseResult' in options))

    input_symbolic = sympify_latex(input_latex)
    if input_symbolic is None:
        return 'error'
    expected_symbolic = sympify_latex(expected_latex)

    equiv = expand(simplify(input_symbolic)) -\
            expand(simplify(expected_symbolic)) == 0

    return result(xor(equiv, 'inverseResult' in options))

def equiv_literal(input_latex, expected_latex, options):
    ''' check equivLiteral
    '''
    ignore_trailing_zeros = 'ignoreTrailingZeros' in options
    input_symbolic = convert(input_latex, evaluate=False,
                             ignore_trailing_zeros=ignore_trailing_zeros,
                             keep_neg_fraction_form=True,
                             thousand_sep=options.get('setThousandsSeparator', ','),
                             decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_symbolic is None:
        return 'error'
    expected_symbolic = convert(expected_latex, evaluate=False,
                                ignore_trailing_zeros=ignore_trailing_zeros,
                                keep_neg_fraction_form=True,
                                thousand_sep=options.get('setThousandsSeparator', ','),
                                decimal_sep=options.get('setDecimalSeparator', '.'),
                                preprocess_sep=False)

    equiv = str(input_symbolic) == str(expected_symbolic)
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
                             thousand_sep=options.get('setThousandsSeparator', ','),
                             decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_symbolic is None:
        return 'error'
    simplified = str(input_symbolic) ==\
                 str(simplify(convert(input_latex,
                              thousand_sep=options.get('setThousandsSeparator', ','),
                              decimal_sep=options.get('setDecimalSeparator', '.'))))
    return result(xor(simplified, 'inverseResult' in options))

def is_expanded(input_latex, expected_latex=None, options={}):
    ''' check isExpanded
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=options.get('setThousandsSeparator', ','),
                             decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_symbolic is None:
        return 'error'
    expanded = input_symbolic - expand(simplify(input_symbolic)) == 0
    return result(xor(expanded, 'inverseResult' in options))

def is_factorised(input_latex, expected_latex=None, options={}):
    ''' check isFactorised
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=options.get('setThousandsSeparator', ','),
                             decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_symbolic is None:
        return 'error'
    factorised = input_symbolic == factor(input_symbolic)
    return result(xor(factorised, 'inverseResult' in options))

def is_true(input_latex, expected_latex=None, options={}):
    ''' check isTrue
    '''
    input_symbolic = convert(input_latex,
                             thousand_sep=options.get('setThousandsSeparator', ','),
                             decimal_sep=options.get('setDecimalSeparator', '.'))
    if input_symbolic is None:
        return 'error'
    true = bool(simplify(input_symbolic))
    return result(xor(true, 'inverseResult' in options))

# a dictionary for mapping an option name
# to the function that performs that check
check_func = {
    'equivSymbolic': equiv_symbolic,
    'equivLiteral': equiv_literal,
    'stringMatch': string_match,
    'isSimplified': is_simplified,
    'isExpanded': is_expanded,
    'isFactorised': is_factorised,
    'isTrue': is_true,
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
        'significantDecimalPlaces'},
    'equivLiteral': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreTrailingZeros'},
    'equivValue': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
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
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult'},
    'stringMatch': {
        'ignoreLeadingAndTrailingSpaces',
        'treatMultipleSpacesAsOne',
        'inverseResult'},
    'equivSyntax': {},
}

no_set_decimal_separator = {main for main in allowed_options 
                            if 'setDecimalSeparator' not in allowed_options[main]}

set_thousand_separator_re = re.compile(r"(?<=setThousandsSeparator): ?\[([ ,.']+)\]")
thousand_separator_re = re.compile(r"'([ .,])'")
set_decimal_separator_re = re.compile(r"(?<=setDecimalSeparator): ?'([,.])'")

def sub_thousand_separator(matchobj):
    return '_' + ''.join(thousand_separator_re.findall(matchobj.group(1))).replace(',', '<COMMA>')

def sub_decimal_separator(matchobj):
    return '_' + matchobj.group(1).replace(',', '<COMMA>')

def parse_checks(options_str):
    # first, split groups of options
    check_list = options_str.split(';')
    # second, split each 
    check_dict = {}
    for check_string in check_list:
        add_dict = {'setDecimalSeparator': '.'}
        if ':' in check_string:
            check_string = set_thousand_separator_re.sub(sub_thousand_separator, check_string)
            check_string = set_decimal_separator_re.sub(sub_decimal_separator, check_string)
            main, add_string = check_string.split(':')
            add_list = add_string.split(',')
            for add in add_list:
                if not (add.startswith('setThousandsSeparator') or
                   add.startswith('setDecimalSeparator')):
                    add_dict[add] = True
                else:
                    add, sep = add.split('_')
                    add_dict[add] = sep.replace('<COMMA>', ',')
        else:
            main = check_string
        if main in no_set_decimal_separator:
            add_dict.pop('setDecimalSeparator')

        if main not in allowed_options:
            print('Option "{}" not allowed'.format(main))
            sys.exit(0)
        for add in add_dict:
            if add not in allowed_options[main]:
                print('Suboption "{}" '.format(add) +
                      'not allowed for option "{}"'.format(main))
                sys.exit(0)
        if 'setDecimalSeparator' in add_dict and\
           'setThousandsSeparator' in add_dict and\
           add_dict['setDecimalSeparator'] in add_dict['setThousandsSeparator']:
                print('Same decimal and thousand separators for option "{}"'.format(main))
                sys.exit(0)

        check_dict[main] = add_dict
    return check_dict

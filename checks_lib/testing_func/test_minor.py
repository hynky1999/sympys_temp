import re
from sympy import (expand,simplify,factor,nsimplify)
from sympy.simplify.radsimp import fraction
from sympy.assumptions import register_handler, ask, Q
from checks_lib.regexes import (factorised_re,parentheses_minus_re,
    eq_form_re,multiple_spaces_re,simple_frac_re,mixed_frac_re,exp_re,
    slope_intercept_form_re,point_slope_form_re,standard_form_linear_re,
    standard_form_quadratic_re,decimal_re_pattern)

from checks_lib.default_values import (allowed_options,check_func)
from checks_lib.utils.test_utils import (result,xor,
     getThousandsSeparator,getDecimalSeparator)
from checks_lib.utils.latex_process import (convert,preprocess_latex,
    sympify_latex)
from checks_lib.utils.test_minor_utils import *
register_handler('rational_2', AskRationalHandler2)

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
    if factorised_re.search(str(input_symbolic)):
        factorised = (equiv
                    and bool(factorised_re.search(str(input_symbolic))))
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

def string_match(input_latex, expected_latex, options):
    ''' check stringMatch
    '''
    #print(input_latex,expected_latex)
    if 'ignoreLeadingAndTrailingSpaces' in options:
        input_latex = input_latex.strip()
    if 'treatMultipleSpacesAsOne' in options:
        input_latex = multiple_spaces_re.sub(' ', input_latex)
    match = input_latex == expected_latex
    return result(xor(match, 'inverseResult' in options))

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
            if globals()[check_func[option]](input,options) == 'false':
                equiv = False
            collisions[2] = 1
            
    return equiv

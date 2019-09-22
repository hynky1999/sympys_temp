from checks_lib.regexes import integral_der_re
from checks_lib.utils.test_utils import (result,xor,
     getThousandsSeparator,getDecimalSeparator)
from checks_lib.utils.latex_process import (convert,preprocess_latex,
     sympify_latex)
from checks_lib.utils.test_major_utils import (identify_expected,
     format_sym_expression,parse_tolerance,equation_parts)
from checks_lib.testing_func.test_minor import checkOptions
from checks_lib.utils.unit_conversion import swap_units
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanAtom

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
    if integral_der_re.search(input_latex):
        options['integral'] = True
    
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

    try:
        input_latex,expected_latex = swap_units(input_latex,expected_latex)
    except ValueError:
        return result(False)

    expected_symbolic = sympify_latex(expected_latex,evaluate=False)
    if expected_symbolic is None:
        return 'Sympy_Parsing_Error'
    
    input_symbolic = sympify_latex(input_latex,evaluate=False)
    if input_symbolic is None:
        return 'false'
    if (type(expected_symbolic) == bool
        or isinstance(expected_symbolic,BooleanAtom)):
        equiv = expected_symbolic == input_symbolic
        return result(xor(equiv, 'inverseResult' in options))

    #Detection of equation signs in expected_latex
    if (isinstance(expected_symbolic,Relational)
        or 'compareSides' in options):
        try:
            (input_symbolic
            ,input_result_symbolic
            ,expected_symbolic
            ,expected_result_symbolic
            ,equiv
            ,a_sep) = equation_parts(input_symbolic,expected_symbolic,options)
            
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
    input_numeric = format_sym_expression(input_symbolic,options)
    expected_numeric = format_sym_expression(expected_symbolic,options)
    
    tolerance = parse_tolerance(str(options.get('tolerance', 0.0))
                                ,expected_numeric)
    try:
        if options.get('integral'):
            if format_sym_expression(input_symbolic-expected_symbolic,options).free_symbols:
                tolerance_check = True

        if tolerance == 0.0:
            tolerance_check = input_numeric == expected_numeric
        else:
            tolerance_check = abs(input_numeric - expected_numeric)\
                                        <= float(tolerance)
        equiv = equiv and bool(tolerance_check)
        
    except:
        return 'Compare_Error'
        
    return result(xor(equiv, 'inverseResult' in options))

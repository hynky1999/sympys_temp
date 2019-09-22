from checks_lib.regexes import (separator_re,integral_der_re)
from checks_lib.utils.test_utils import (result,xor,
     getThousandsSeparator,getDecimalSeparator)
from checks_lib.utils.test_major_utils import (identify_expected,
     format_sym_expression,parse_tolerance,equation_parts)
from checks_lib.utils.latex_process import (preprocess_latex,
     sympify_latex,derivateExpected)
from checks_lib.testing_func.test_minor import checkOptions
from checks_lib.utils.unit_conversion import swap_units
from sympy.core.relational import Relational
from sympy.logic.boolalg import BooleanAtom
from sympy import simplify

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
    
    #Swap of units to numbers

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
        
        #Split latexes by a sign
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
        '''if compareSides are set on both sides in student input
           and expected input must be the same
           if not can must have same numbers on different sides
           but with different signs - and +
        '''
        try:
            tolerance = parse_tolerance(str(options.get('tolerance', 0.0))
                                                ,expected_result_symbolic)
        except ValueError as e:
            return e.args[0]
        
        if tolerance != 0.0:
            La = format_sym_expression(input_symbolic,options)
            Ra = format_sym_expression(input_result_symbolic
                                                    ,options)
            Ls = format_sym_expression(expected_symbolic,options)
            Rs = format_sym_expression(expected_result_symbolic
                                                    ,options)
            tolerance_check = abs(input_result_numeric - expected_result_numeric)\
                                <= float(tolerance)
            try:
                equiv = (equiv
                    and input_numeric == expected_numeric
                    and bool(tolerance_check))
            except ValueError as e:
                return e.args[0]
        
        elif options.get('compareSides'):
            La = format_sym_expression(input_symbolic,options)
            Ra = format_sym_expression(input_result_symbolic
                                                    ,options)
            Ls = format_sym_expression(expected_symbolic,options)
            Rs = format_sym_expression(expected_result_symbolic
                                                    ,options)
            # if equal sign --> sides can be swapped
            if tolerance == 0.0: 
                if a_sep == '==':
                    equiv = (equiv and ((La == Rs and Ra == Ls)
                             or (La == Ls and Ra == Rs)))
                
                else:
                    equiv = (equiv and (La == Ls and Ra == Rs))
            else:
                tolerance_check = abs(Ra - Rs)\
                                <= float(tolerance)
                equiv = (equiv
                    and La == Ls
                    and bool(tolerance_check)) 
                
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
            if a_sep == '==':
                equiv = (equiv
                        and (input_one_side_2 == expected_one_side
                        or input_one_side_1 == expected_one_side))
                        
            else:
                equiv = (equiv
                        and (input_one_side_1 == expected_one_side))

        return result(xor(equiv, 'inverseResult' in options))
    equiv = checkOptions(input_latex,options)
        
    # if expected answer evaluates to boolean
    # (most prominent case is when it's an equality),
    # evaluate if input evaluates to the same value

    input_symbolic = format_sym_expression(input_symbolic,options)
    expected_symbolic = format_sym_expression(expected_symbolic,options)

    tolerance = parse_tolerance(str(options.get('tolerance', 0.0))
                                ,expected_symbolic)
    print(input_symbolic,expected_symbolic)
    try:
        if options.get('integral'):
            if simplify(input_symbolic-expected_symbolic).free_symbols:
                equiv = True
        if tolerance == 0.0:
            tolerance_check = input_symbolic == expected_symbolic
        else:
            tolerance_check = abs(input_symbolic - expected_symbolic)\
                                        <= float(tolerance)
        equiv = bool(tolerance_check) and equiv

    except TypeError:
        return 'Compare_Error'
   
    return result(xor(equiv, 'inverseResult' in options))

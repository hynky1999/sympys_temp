from checks_lib.utils.test_utils import (result,xor,
     getThousandsSeparator,getDecimalSeparator)
from checks_lib.utils.test_major_utils import identify_expected
from checks_lib.testing_func.test_minor import checkOptions
from checks_lib.regexes import (leading_zero_re,constituent_parts_re,
     coefficient_of_one_re,integral_der_re)
from checks_lib.utils.latex_process import (convert,preprocess_latex)

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
    if integral_der_re.search(input_latex):
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

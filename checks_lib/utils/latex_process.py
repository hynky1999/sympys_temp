from latex2sympy.process_latex import process_sympy
from sympy.core.singleton import S
from sympy import sympify

from checks_lib.default_values import *
from checks_lib.regexes import *
from checks_lib.utils.test_utils import (balance_check,
     replaceNonEffective)
#Math to Sympy conversion of signs

def convert_percent(matchobj):
    percent_str = (r'NotLatex:Format:convert_percent_final({})'
    + r'Format:convert_percent_final')
    percent_str = percent_str.format(matchobj.group(2))
    return percent_str

def derivateExpected(inp,exp):
    parts = integral_der_re.search(inp)
    inp = r'\frac{{d}}{{{}}}{}'.format(parts.group(2),exp)
    exp = parts.group(1)
    return inp,exp

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

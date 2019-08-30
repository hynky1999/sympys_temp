from sympy import (expand,simplify,logcombine,expand_log)
from sympy.sets.sets import Interval
from checks_lib.regexes import (set_res,set_re_error,separator_pairs,
     separator_re)
from checks_lib.testing_func.equiv_set import equiv_set
from checks_lib.utils.test_utils import (replaceNonEffective,
     balance_check)
from checks_lib.testing_func.test_minor import checkOptions
from checks_lib.utils.latex_process import convert,sympify_latex
import decimal
decimal.getcontext().rounding = decimal.ROUND_HALF_UP

def identify_expected(input_latex,expected_latex,options):
    '''
    Identification of expected and calling set_evaluation properly
    '''
    expected_tmp = replaceNonEffective(expected_latex)
    if ('setEvaluation' in options
        or 'orderedElements' in options
        or 'orderedPair' in options):
        return equiv_set(input_latex,expected_latex,options)
    
    if 'interpretAsList' in options:
        options['orderedPair'] = True
        return equiv_set(input_latex,expected_latex,options)
        
    if 'interpretAsSet' in options:
        return equiv_set(input_latex,expected_latex,options)
        
    for set_re in set_res:
        search = set_re.match(expected_tmp)
        if search and balance_check(search.group(2)):
            break
            
        else:
            search = ''
            
    if search:
        if (search.group(1) == '(' and search.group(3) == ')'):
            try:
                if (not isinstance(convert(expected_latex,evaluate=True),
                                                         Interval)
                                                         or
                    not isinstance(convert(input_latex,evaluate=True),
                                                         Interval)):
                    options['orderedPair'] = True
                    return equiv_set(input_latex,expected_latex,options)
            except:
                pass
            
        elif search.group(1) == '{' and search.group(3) == '}':
            return equiv_set(input_latex,expected_latex,options)
            
    if (set_re_error.search(input_latex)
        and getThousandsSeparator(options)) == ',':
        return 'Undefined_Expected_Error'
    else:
        return None

def equation_parts(input_latex,expected_latex,options):
    ''' Function splits input and expected into 2 parts
        by sign
    '''
    try:
        a_sep = separator_re.search(input_latex).group(0)
        s_sep = separator_re.search(expected_latex).group(0)
    except IndexError:
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

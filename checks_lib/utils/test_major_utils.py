from sympy.simplify.hyperexpand import expand
from sympy.simplify.simplify import simplify,logcombine,expand_log
from sympy.sets.sets import Interval
from sympy.core.relational import Lt,Gt,Ge,Le
from checks_lib.regexes import (set_res,set_re_error,separator_pairs,
     separator_re)
from checks_lib.testing_func.equiv_set import equiv_set
from checks_lib.utils.test_utils import (replaceNonEffective,
     balance_check)
from checks_lib.testing_func.test_minor import checkOptions
from checks_lib.utils.latex_process import convert,sympify_latex

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
        
        input_latex = input_latex.replace(',','~')

def equation_parts(eq1,eq2,options):
    ''' Function splits input and expected into 2 parts
        by sign
    '''
    print(eq1,eq2,1111)
    if isinstance(eq1,Ge) or isinstance(eq1,Gt):
        eq1 = eq1.reversed

    if isinstance(eq2,Ge) or isinstance(eq2,Gt):
        eq2 = eq2.reversed
    
    if eq1.rel_op != eq2.rel_op:
        raise ValueError('Error_Sign')
    #Must add equivCheck
    return (eq1.lhs,eq1.rhs,
                eq2.lhs,eq2.rhs,True,eq1.rel_op)


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
    decimal_places = options.get('significantDecimalPlaces',15)
    try:
        exp = exp.round(decimal_places)
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

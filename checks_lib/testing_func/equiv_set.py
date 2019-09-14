from checks_lib.utils.test_utils import (balance_check,result,xor,
     getThousandsSeparator,getDecimalSeparator)

from checks_lib.utils.latex_process import (convert,replaceNonEffective)
from latex2sympy.process_latex import process_set
import re

def sort_struct(struct):
    for i in range(1,len(struct)):
        try:
            struct[i] = [struct[i][0]] +\
                        sorted(struct[i][1:-1],key=str) +\
                        [struct[i][-1]]
        except TypeError:
            pass

def equiv_set(input_latex, expected_latex=None, options={}):
    ''' check setEvaluation
        checking type and also if sets/list are the same
    '''
    if not balance_check(expected_latex):
        return 'Parenthesis_Error'
    
    expected_latex = replaceNonEffective(expected_latex)
    expected_latex = re.sub(',','~',expected_latex)
    if not balance_check(input_latex):
        return result(False)

    input_latex = replaceNonEffective(input_latex)
    input_latex = re.sub(',','~',input_latex)
    #Parse sets
    try:
        input_symbolic = process_set(input_latex)
    except ValueError:
        return 'false'

    try:
        expected_symbolic = process_set(expected_latex)
    except ValueError:
        return 'Unreadable_List_Error'
    if not isinstance(input_symbolic,list):
        if isinstance(expected_symbolic,list) and\
           len(expected_symbolic) == 3:
            return result(expected_symbolic[1] == input_symbolic)
        else:
            return result(expected_symbolic == input_symbolic)
        return result(False)
    #Sort sets according to options\
    if not 'orderedElements' in options:
        sort_struct(input_symbolic)
        sort_struct(expected_symbolic)

    if not 'orderedPair' in options:
        input_symbolic = [input_symbolic[0]] +\
                         sorted(input_symbolic[1:-1],key=str) +\
                         [input_symbolic[-1]]
        expected_symbolic = [expected_symbolic[0]] +\
                         sorted(expected_symbolic[1:-1],key=str) +\
                         [expected_symbolic[-1]]
        
    #Compare lists and type
    if input_symbolic[0] == 'any' or expected_symbolic[0] == 'any' or\
       'interpretAsList' in options or 'interpretAsSet' in options:
        evaluation = input_symbolic[1:-1] == expected_symbolic[1:-1]
    else:
        evaluation = input_symbolic == expected_symbolic
    return result(xor(evaluation, 'inverseResult' in options))

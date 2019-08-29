from checks_lib.utils.test_utils import (balance_check,result,xor,
     getThousandsSeparator,getDecimalSeparator)
from checks_lib.regexes import (escaped_par_re,set_res,set_re_par,
     set_re_par2)
from checks_lib.utils.latex_process import (convert,replaceNonEffective)

def transform_set(set_latex
                ,par_open=['(','[','{']
                ,par_close=[')',']','}']
                ,options={}):
    ''' Transform string set into list and return type of set
        any == type does not matter - default
        list == type matters and order matters
        set == type matters and order does not matter
    '''
    #Parsing of list
    #Try to match string using set regex and then perform balance check
    type = 'any'
    search_set = set_latex
    for set_re in set_res:
        search = set_re.match(set_latex)
        if search and balance_check(search.group(2)):
            if set_re == set_re_par:
                type = 'list'
            elif set_re == set_re_par2:
                type = 'set'
            search_set = search.group(2)
            break
    opening = []
    set_symbolic = []
    last_char = 0
    quoted = False
    closed = False
    for i,char in enumerate(search_set):
        if char in par_open and len(opening) == 0 and not quoted:
            if closed:
                raise ValueError

            opening.append(char)
            set_symbolic.append([char])
            last_char = i+1
            
        elif char in par_close and len(opening) == 1 and not quoted:
            element = str(convert(search_set[last_char:i],
                             thousand_sep=getThousandsSeparator(options),
                             decimal_sep=getDecimalSeparator(options),
                             ignore_text=options.get('ignoreText', False),
                             ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                             euler_number=options.get('allowEulersNumber',False),
                             evaluate=True))
                             
            if element == None:
                raise ValueError
                
            set_symbolic[-1].append(str(element))
            set_symbolic[-1].append(char)
            char2 = opening.pop()
            if char2 == '{' and char == '}':
                set_symbolic[-1] = [[set_symbolic[-1][0]]
                                  + sorted(set_symbolic[-1][1:-1])
                                  + [set_symbolic[-1][-1]]]
                                  
            last_char = i+1
            if closed:
                raise ValueError
                
            closed = True
        elif char == '"':
            if quoted:
                quoted = False
                
            else:
                quoted = True
                last_char = i+1 
                
        elif char == ',' and not quoted:
            if opening:
                element = str(convert(search_set[last_char:i],
                                  thousand_sep=getThousandsSeparator(options),
                                  decimal_sep=getDecimalSeparator(options),
                                  ignore_text=options.get('ignoreText', False),
                                  ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                                  euler_number=options.get('allowEulersNumber',False),
                                  evaluate=True))
                if element is None:
                    raise ValueError
                set_symbolic[-1].append(str(element))
                last_char = i+1
            else:
                if closed:
                    last_char = i+1
                    closed = False
                    
                else:
                    element = str(convert(search_set[last_char:i],
                                      thousand_sep=getThousandsSeparator(options),
                                      decimal_sep=getDecimalSeparator(options),
                                      ignore_text=options.get('ignoreText', False),
                                      ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                                      euler_number=options.get('allowEulersNumber',False),
                                      evaluate=True))
                    
                    if element is None:
                        raise ValueError
                        
                    set_symbolic.append([str(element)])
                    last_char = i+1
                    
    if last_char != len(search_set) and not closed:
        element = str(convert(search_set[last_char:],
                          thousand_sep=getThousandsSeparator(options),
                          decimal_sep=getDecimalSeparator(options),
                          ignore_text=options.get('ignoreText', False),
                          ignore_alpha=options.get('ignoreAlphabeticCharacters',False),
                          euler_number=options.get('allowEulersNumber',False),
                          evaluate=True))
        if element is None:
            raise ValueError
            
        set_symbolic.append([str(element)])
    return set_symbolic,type

def equiv_set(input_latex, expected_latex=None, options={}):
    ''' check setEvaluation
        checking type and also if sets/list are the same
    '''
    if not balance_check(expected_latex):
        return 'Parenthesis_Error'

    expected_latex = replaceNonEffective(expected_latex)
    if not balance_check(input_latex):
        return result(False)

    input_latex = replaceNonEffective(input_latex)
    #Parse sets
    try:
        input_symbolic,type1 = transform_set(input_latex)
    except ValueError:
        return 'false'

    try:
        expected_symbolic,type2 = transform_set(expected_latex)  
    except ValueError:
        return 'Unreadable_List_Error'

    if 'interpretAsList' in options or 'interpretAsSet' in options:
        type1 = 'any'
        
    #Sort sets according to options
    if not 'orderedElements' in options:
        input_symbolic = [sorted(x) for x in input_symbolic]
        expected_symbolic = [sorted(x) for x in expected_symbolic]
        
    if not 'orderedPair' in options:
        input_symbolic.sort()
        expected_symbolic.sort()
        
    #Compare lists and type
    if type1 == 'any' or type2 == 'any' or type2 == type1:
        evaluation = input_symbolic == expected_symbolic
    else:
        evaluation = False
    return result(xor(evaluation, 'inverseResult' in options))

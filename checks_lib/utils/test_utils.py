from checks_lib.regexes import (escaped_par_re,left_par_re,right_par_re,
    times_re)

def getThousandsSeparator(options):
    thousand_sep = options.get('setThousandsSeparator', None)
    decimal_sep = options.get('setDecimalSeparator', None)

    if thousand_sep is None and decimal_sep is None:
        thousand_sep = ','
        
    elif thousand_sep is None and decimal_sep is not None:
        thousand_sep = '.' if decimal_sep == ',' else ','
        
    return thousand_sep

def getDecimalSeparator(options):
    thousand_sep = options.get('setThousandsSeparator', None)
    decimal_sep = options.get('setDecimalSeparator', None)

    if thousand_sep is None and decimal_sep is None:
        decimal_sep = '.'
        
    elif thousand_sep is not None and decimal_sep is None:
        decimal_sep = ',' if thousand_sep == '.' else '.'
        
    return decimal_sep

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

def balance_check(str_input,par_open=['(','[','{'],par_close=[')',']','}']):
    str_input = escaped_par_re.sub(r'\1',str_input)
    opening = []
    for i,char in enumerate(str_input):
            if char in par_open:
                par_index = par_open.index(char)
                if i >= 6 and str_input[i-6:i] == r'\\left':
                    par_index = par_index*-1
                if i >= 6 and str_input[i-6:i] == r'\\right':
                    raise ValueError('Not_Supported_Error')
                    
                opening.append(par_index)

            elif char in par_close:
                par_index = par_close.index(char)
                if len(opening) <= 0:
                    return False
                last_par = opening.pop()
                if i >= 6 and str_input[i-6:i] == r'\\right':
                    par_index = par_index*-1
                    
                if i >= 6 and str_input[i-6:i] == r'\\left':
                    raise ValueError('Not_Supported_Error')    
                if par_index != last_par:
                    return False
    return not opening

def xor(a, b):
    ''' Logical xor one-liner
    '''
    return a and not b or not a and b

def result(bool_result):
    ''' Convert bool value to lowercase str
    ''' 
    return str(bool_result).lower()

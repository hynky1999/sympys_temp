import re
from sympy.simplify.simplify import simplify
from checks_lib.utils.latex_process import (preprocess_latex,
     sympify_latex)
from checks_lib.testing_func.equiv_symbolic import equiv_symbolic

# Replace variables in the input_latex
# # input_latex: normal latex string
# # variables: [
# #     { id: 'x', type: 'value', value: 3 },
# #     { id: 'y', type: 'value', value: 5 },
# #     { id: 'z', type: 'formula', value: 'x+y' }
# # ]
def replace_variables(input_latex,
                      variables):
    input_latex = preprocess_latex(str(input_latex))
    for x in range(len(variables)):
        variables[x]['value'] = preprocess_latex(str(variables[x]['value']))
    # Replace variables first deeply until fixed times
    for i in range(0, 10):
        prev_latex = input_latex
        for variable in variables:
            variable_re = re.compile(re.escape(variable['id']) + r'\b')    
            input_latex = re.sub(
                        variable_re
                        , '(' + str(variable['value']) + ')'
                        , input_latex)
                        
        if prev_latex == input_latex:
            break
            
    return input_latex

def calculate_expression(input_latex):
    input_latex = preprocess_latex(input_latex.strip(), ',', '.')
    input_symbolic = sympify_latex(input_latex)
    return simplify(input_symbolic)

def calculate(input_latex, expected_latex, options):
    '''Caluculation of expressions using substitute of variables
    '''
    input_str, formula = input_latex.split('formula:', maxsplit=1)
    input_str = input_str.split('input:')[1]
    var_strs = input_str.split(',')

    variables = []
    for var_str in var_strs:
        if '=' in var_str:
            variable, variable_value = var_str.split('=', 1)
            variables.append({
                "id": variable,
                "value": variable_value,
            })
    #Replacing of variables
    try:
        formula = replace_variables(formula, variables)
        return equiv_symbolic(formula, expected_latex, options)
    except ValueError as e:
        return e.args

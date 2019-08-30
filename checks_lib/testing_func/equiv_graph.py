import re
from checks_lib.utils.latex_process import convert
from checks_lib.regexes import no_solution_re
from checks_lib.utils.test_utils import result
from checks_lib.utils.graph_utils import *

def strToList(s):
    s = s.strip()
    level = 0
    list_temp = []
    esc1,esc2 = [False]*2
    last_char = 0
    flag = 0
    for i,char in enumerate(s):

        if not esc1 and not esc2:

            if char in ('(','['):
                level+= 1
                flag = 1

                if level == 1:
                    last_char = i+1

            elif char in (')',']'):
                if level == 1:
                    element = strToList(s[last_char:i])

                    if element is not None:
                        list_temp.append(element)

                    last_char = i+1
                level-= 1
            elif char == ',' and level == 1:
                    element = strToList(s[last_char:i])
                    if element is not None:
                        list_temp.append(element)

                    last_char = i+1
        if char == '"':
            esc1 = not esc1

        elif char == "'":
            esc2 = not esc2

    if not flag:
        s = s.replace("'",'').replace('"','')
        return s if s else None

    else:
        return list_temp

def formatGraphList(graph_list):
    graph_list = strToList('('+graph_list+')')
    if len(graph_list) == 1:
        shapeEqn = graph_list[0]

        if (isinstance(shapeEqn,str)
            and no_solution_re.match(shapeEqn)):
            shapeEqn = []
        shapeStyle = ['']*len(shapeEqn)
        regionPoints = []

    elif len(graph_list) == 2:
        shapeEqn,regionPoints = graph_list
        shapeStyle = ['']*len(shapeEqn)

    elif len(graph_list) == 3:
        shapeEqn,shapeStyle,regionPoints = graph_list

    else:
        raise ValueError('Could not format')

    shapeStyle = formatShapeStyle(shapeStyle,len(shapeEqn))
    return shapeEqn,shapeStyle,regionPoints
    
def formatShapeStyle(shapes,len_eqs):
    if len(shapes) == 0:
        shapes = [''] * len_eqs
        
    else:
        shapes = [x for x in shapes]
        
    if len(shapes) != len_eqs:
        raise ValueError('Error_graph')
    
    return shapes
        
    
    return shapes


def equiv_graph(input_latex,expected_latex,options={}):
    '''
    Function which compares input equations against expected equations
    Equations can be either standar equations or JSXGraph objects
    If we encounter object it is converted to equation with = sign.
    All equations signs are then formated using points provided as
    region points to include these points.
    Then we compare these equations
    '''
    try:
        expectedShapeEqn,expectedShapeStyle,expectedRegionPoints =\
                                    formatGraphList(expected_latex)
        expectedRegionPoints = [list(map(convert,x)) for
                                    x in expectedRegionPoints]

        eq_expected = formatEquations(expectedShapeEqn,
                                      expectedRegionPoints,
                                      expectedShapeStyle)

    except ValueError as e:
        return 'Error_Graph'

    try:
        answerShapeEqn,answerShapeStyle,answerRegionPoints =\
                                 formatGraphList(input_latex)
        answerRegionPoints = [list(map(convert,x)) for
                                    x in answerRegionPoints]
        eq_answer = formatEquations(answerShapeEqn,
                                    answerRegionPoints,
                                    answerShapeStyle)
    except ValueError as e:
        return result(False)

    if (len(expectedRegionPoints) < 1
        or len(expectedRegionPoints) != len(answerRegionPoints)):
        return 'Error_Point'

    #print(eq_expected,eq_answer)
    for a in eq_answer:
        for eq in eq_expected:
            if checkEquations(eq,a):
                eq_expected.remove(eq)
                break
        else:
            return result(False)

    if len(eq_expected) == 0:
        return result(True)

    else:
        return result(False)


from sympy.core.relational import Lt,Gt,Ge,Le,Eq
from sympy import (symbols,simplify,Matrix,linsolve,solveset,expand)
from checks_lib.utils.latex_process import convert
from checks_lib.utils.test_utils import (getThousandsSeparator,getDecimalSeparator)

def formatEquation(equation,options={},evaluate=False):
    equation = convert(equation, evaluate,
                        thousand_sep=getThousandsSeparator(options),
                        decimal_sep=getDecimalSeparator(options),
                        euler_number=True)
    if equation is None:
        raise ValueError('Error')
    return equation

def formatLine(params):
    point1,point2 = [list(map(convert,x)) for x in params]
    a, b, x, y = symbols('a b x y')
    if simplify(point1[0] - point2[0]) == 0:

        if point1[1] == point2[1]:
            raise ValueError('Point')

        else:
            return Eq(x,point1[0])

    if simplify(point1[1] - point2[1]) == 0:
        return Eq(y,point1[1])

    A = Matrix([[point1[0],1],
                [point2[0],1]])
    B = Matrix([[point1[1]],
                [point2[1]]])
    a,b = linsolve((A,B),[a,b]).args[0]
    return Eq(y,a*x+b)

def formatCircle(params):
    x, y = symbols('x y')
    center,point1 = [list(map(convert,x)) for x in params]
    if center == point1:
        raise ValueError('Point')

    e = (point1[0]-center[0])**2+(point1[1]-center[1])**2
    return Eq((x-center[0])**2+(y-center[1])**2,e)

def formatEllipse(params):
    x, y = symbols('x y')
    center,point1,point2 = [list(map(convert,x)) for x in params]
    a_2 = (center[0]-point1[0])**2 
    b_2 = (center[1]-point2[1])**2
    if simplify(a_2) == 0 or simplify(b_2) == 0:
        raise ValueError('Invalid Elipse')

    return Eq(((x-center[0])**2)/a_2+((y-center[1])**2)/b_2,1)

def formatParabola(params):
    x, y = symbols('x y')
    apex,point1,point2 = [list(map(convert,x)) for x in params]
    if ((apex[1] < point1[1] and apex[1] < point2[1])#X-centric
        or (apex[1] > point1[1] and apex[1] > point2[1])):
        p1 = (point1[0]-apex[0])**2/(point1[1]-apex[1])
        p2 = (point2[0]-apex[0])**2/(point2[1]-apex[1])
        if point1[1] == apex[1] or point2[1] == apex[1]:
            raise ValueError('Invalid Parabola')
        if simplify(p1-p2) == 0:
            return Eq((x-apex[0])**2,p1*(y-apex[1]))

        else:
            raise ValueError('Invalid Parabola')

    else:
        if point1[0] == apex[0] or point2[0] == apex[0]:
            raise ValueError('Invalid Parabola')

        p1 = (point1[1]-apex[1])**2/(point1[0]-apex[0])
        p2 = (point2[1]-apex[1])**2/(point2[0]-apex[0])

        if point1[0] == apex[0] or point2[0] == apex[0]:
            raise ValueError('Invalid Parabola')
        if simplify(p1-p2) == 0:
            return Eq((y-apex[1])**2,p1*(x-apex[0]))

        else:
            raise ValueError('Invalid Parabola')

    raise ValueError('Invalid Prabola')

def formatHyperbola(params):
    x, y, a_2, b_2 = symbols('x y a b')
    foci1,foci2,point1 = [list(map(convert,x)) for x in params]
    if foci1[1] == foci2[1]: 
        e = (foci1[0]-foci2[0])/2
        center = (foci2[0]+e,foci1[1])
        a_2 = solveset(
              Eq(((point1[0]-center[0])**2)/a_2\
              -((point1[1]-center[1])**2)/(e**2-a_2),1),a_2).args[0]
        b_2 = e**2 - a_2
        if simplify(a_2) == 0 or simplify(b_2) ==0:
            raise ValueError('Invalid Hyperbola')

        else:
            return Eq(((x-center[0])**2)/a_2-((y-center[1])**2)/b_2,1)

    elif foci1[0] == foci2[0]:
        e = (foci1[1]-foci2[1])/2
        center = (foci1[0],foci2[1]+e)
        b_2 = solveset(
              Eq((((point1[1]-center[1])**2)/b_2-\
                (point1[0]-center[0])**2)/(e**2-b_2),1),b_2).args[0]
        a_2 = e**2 - b_2
        if simplify(a_2) == 0 or simplify(b_2) ==0:
            raise ValueError('Invalid Hyperbola')

        else:
            return Eq(((y-center[1])**2)/b_2-((x-center[0])**2)/a_2,1)

    else:
        raise ValueError('Invalid Hyperbola')

def formatOp(eq,points,shapeStyle,eq_type=False):
    equality,higher,lower = [False]*3
    if shapeStyle == '' and eq_type:
        if isinstance(eq,(Lt,Gt)):
            shapeStyle = 'dashed'
        else:
            shapeStyle = 'solid'
    
        
    for p in points:
        if subPoint(p,Eq(eq.lhs,eq.rhs)):
            equality = True

        elif subPoint(p,Lt(eq.lhs,eq.rhs)):
            lower = True
                
        elif subPoint(p,Gt(eq.lhs,eq.rhs)):
            higher = True
    if higher and lower:
        raise ValueError('Wrong Points')
    
    elif equality and shapeStyle == 'dashed':
        raise ValueError('Wrong shapeStyle')

    elif higher:
        if shapeStyle == 'dashed':
            op = Gt

        else:
            op = Ge

    elif lower:
        if shapeStyle == 'dashed':
            op = Lt
        
        else:
            op = Le

    elif equality:
        op = Eq

    else:
        raise ValueError()

    if eq_type:
        eq_expected = type(eq)
        if shapeStyle == 'dashed':
            if isinstance(eq,Le):
                eq_expected = Lt
            elif isinstance(eq,Ge):
                eq_expected = Gt
        else:
            if isinstance(eq,Lt):
                eq_expected = Le
            elif isinstance(eq,Gt):
                eq_expected = Ge
        
        if eq_expected is op:
            return (op(eq.lhs,eq.rhs),True)
        else:
            return (op(eq.lhs,eq.rhs),False)

    return (op(eq.lhs,eq.rhs),'any')

def formatEquations(equations,points,shapeStyle):
    eqs = []
    for i,eq in enumerate(equations):
        eq_type = False
        object_type = eq[0]
        if object_type == 'eqn':
            formated_eqn = formatEquation(eq[1])
            eq_type = True

        elif object_type == 'line':
            formated_eqn = formatLine(eq[1])

        elif object_type == 'circle':
            formated_eqn = formatCircle(eq[1])

        elif object_type == 'ellipse':
            formated_eqn = formatEllipse(eq[1])

        elif object_type == 'parabola':
            formated_eqn = formatParabola(eq[1])

        elif object_type == 'hyperbola':
            formated_eqn = formatHyperbola(eq[1])

        else:
            raise ValueError('Not Defined object')

        formated_eqn = formatOp(formated_eqn,
                                points,
                                shapeStyle[i],
                                eq_type=eq_type)
        eqs.append(formated_eqn)
    return eqs

def checkEquations(eq1,eq2):
    eq1,b1 = eq1
    eq2,b2 = eq2
    if b1 != b2 and b1 != 'any' and b2 != 'any':
        return False

    if isinstance(eq1,Ge) or isinstance(eq1,Gt):
        eq1 = eq1.reversed

    if isinstance(eq2,Ge) or isinstance(eq2,Gt):
        eq2 = eq2.reversed

    if isinstance(eq1,type(eq2)):
        division = simplify(expand((eq1.lhs-eq1.rhs)/(eq2.lhs-eq2.rhs)))
        if (division.is_number and
            (division.is_positive or isinstance(eq1,Eq))):
            return True
    return False
        
def checkRegionPoints(points,equations):
    for e in equations:
        for p in points:
            e = subPoint(p,e)
            if e != True:
                raise ValueError('Error_graph')

    return True
    
def subPoint(point,eq):
    x,y = symbols('x y')
    a = eq.subs([[x,point[0]],[y,point[1]]])
    return eq.subs([[x,point[0]],[y,point[1]]])

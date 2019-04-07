#!/usr/bin/env python3

import csv,sys,csv,os,re
from checks import check_func, UNITS,ERROR,POSSIBLE_THOUSANDS_SEP,POSSIBLE_DECIMAL_SEP,DEFAULT_THOUSANDS_SEP,DEFAULT_DECIMAL_SEP
import lxml.html
import decimal
from lxml import etree


#Dictionary For Swapping Unsuported characters
swap_dict = {'÷':'/','≤':'<=','≥':'>=',':':'/','·':'*'}
swap_multiplier_re = re.compile('(?<=\\S)×(?=\\S)')
swap_variable_re = re.compile('(?<!\\S)×(?!\\S)|(?<=\\S)×(?!\\S)|(?<!\\S)×(?=\\S)')
#Separators re
separator_thousands_re = re.compile(r'\d(['+''.join(POSSIBLE_THOUSANDS_SEP) + r'])\d{3}(?!\d)')
separator_decimal_re = re.compile(r'\d(['+''.join(POSSIBLE_DECIMAL_SEP) + r'])(?!\d{3}(\D|$))\d+')

#Unit tests
latex_units_re = re.compile('\d\s+('+'|'.join(['{}'.format(text) for text in UNITS])+ ')(/[a-z]*)?$',flags=re.IGNORECASE)

#Inequation tests
inequation_re = re.compile(r'[<>≠]')
    
#Equation tests
equation_re = re.compile('[^<>]=(?!\s*$)')

#Literal tests
intervals_re = re.compile(r'^\s*[([]\s*-?(\\infty|[0-9∞]+)\s*,\s*-?(\\infty|[0-9∞]+)\s*[])]\s*$')
trailing_zeros_re = re.compile(r'(?<=\.)([1-9]*)0+\b')

#Symbolic tests
times = r'(\*|\\cdot ?|\\times ?)?'
coefficient_of_one_re = re.compile(r'(?<![0-9].)1' + times + r'(?=[a-z(\\])', flags=re.IGNORECASE)
closing_text_re = re.compile(r'\d\s+[a-zA-Z]+$')

#String tests
multiple_spaces_re = re.compile(r' {2,}')

class CheckError(Exception):
    def __init__(self,rule,option,inl,oul):
        self.rule = rule
        self.option = option
        self.inl = inl
        self.oul = oul


def mathml_to_latex(eq):
    if not eq:
        return '$$'
    
    xslt_file = os.path.join(os.path.dirname(__file__),'xsl_yarosh', 'mmltex.xsl')
    dom = etree.fromstring(eq)
    xslt = etree.parse(xslt_file)
    transform = etree.XSLT(xslt)
    transform.set_global_max_depth(120000)
    newdom = transform(dom)
    return str(newdom)

def get_separators(connected_string,iteration):
    separators = {}
    thous = ''
    decimal = ''
    if not intervals_re.search(connected_string):
        thous = separator_thousands_re.search(connected_string)
        decimal = separator_decimal_re.search(connected_string)
    if thous:
        if iteration == 0:
            if thous.group(1) != DEFAULT_DECIMAL_SEP:
                separators['setDecimalSeparator'] = thous.group(1)
        elif iteration == 1:
            if thous.group(1) != DEFAULT_THOUSANDS_SEP:
                separators['setThousandSeparator'] = thous.group(1)
            if decimal:
                if decimal.group(1) != DEFAULT_DECIMAL_SEP and decimal.group(1) != thous.group(1):
                    separators['setDecimalSeparator'] = decimal.group(1) 
        else:
            return None
        return separators
    elif decimal:
        if decimal.group(1) != DEFAULT_DECIMAL_SEP:
            separators['setDecimalSeparator'] = decimal.group(1)
    if iteration == 1:
        return None
    return separators
        
        
        
    
def parse_rules(rules,options):
    final_string = ''
    for i,rule in enumerate(rules):
        options_rules = []
        ops = ','.join([x + ('={}'.format(options[i][x]) if x == 'significantDecimalPlaces' else ("=['{}']".format(options[i][x]) if options[i][x] is not True else '')) for x in options[i].keys()])
        if ops:
            final_string += rule + ':' + ops
        else:
            final_string += rule
        final_string += ';'
    if final_string:
        return final_string[:-1]
    else:
        return final_string
            
        
        
def test_rules(inl,oul,rules,options):
    for index in range(len(rules)):
        check = check_func[rules[index]](inl,expected_latex=oul,options = options[index])
        if check == 'false' or not check:
            return False
        if check == ERROR:
            raise CheckError(rules[index],options[index],inl,oul)
    return True


def process_units(inl,oul,cor,rules,options,unit,separators):
    rules.append('isUnit')
    options.append({'allowedUnits':unit.group(1),**separators})
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            if test_rules(inl,oul,['equivValue'],[separators]):
                return parse_rules(rules+['equivValue'],options+[separators])
            else:
                return parse_rules(rules,options)
        elif not cor and output:
            rules.append('equivValue')
            options.append(separators[:])
            if not test_rules(inl,oul,['equivValue'],[separators]):
                return parse_rules(rules,options)
            else:
                for x in options:
                    x['inverseResult'] = True
                if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
                for x in options:
                    del[x['inverseResult']]
            rules.pop()
            options.pop()
        elif not cor and not output:
            return parse_rules(rules,options)
    except CheckError as e:
        pass
    options.pop()
    rules.pop()
    return None


def process_inequation(inl,oul,cor,rules,options,separators):
    rules.append('isTrue')
    options.append(separators)
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                return parse_rules(rules,options)
            for x in options:
                del[x['inverseResult']]
        elif not cor and not output:
            return parse_rules(rules,options)
    except (CheckError,TypeError):
        pass
    return None


def process_equation(inl,oul,cor,rules,options,separators):
    rules.append('equivSymbolic')
    text_test = bool(closing_text_re.search(inl))
    if text_test:
        options[-1]['ignoreText'] = True
    options.append({'compareSides':True,**separators})
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
            for x in options:
                del[x['inverseResult']]
        elif not cor and not output:
            return parse_rules(rules,options)
    except (CheckError,AttributeError,ValueError,TypeError):
        pass
    options.pop()
    rules.pop()
    return None


def process_literal(inl,oul,cor,rules,options,separators,connected_string):
    rules.append('equivLiteral')
    options.append({**separators})
    intervals_test = intervals_re.search(inl) or intervals_re.search(oul)
    coef_test = coefficient_of_one_re.search(connected_string)
    trailing_test = trailing_zeros_re.search(connected_string)
    if intervals_test:
        options[-1]['allowInterval'] = True
    if coef_test:
        options[-1]['ignoreCoefficientOfOne'] = True
    if trailing_test:
        options[-1]['ignoreTrailingZeros'] = True
    
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
            for x in options:
                del[x['inverseResult']]
        
        elif cor and not output:
            options[-1]['ignoreOrder'] = True
            if test_rules(inl,oul,['equivLiteral'],[options[-1]]):
                return parse_rules(rules,options)
            
            
        elif not cor and not output:
            return parse_rules(rules,options)
    except (CheckError,TypeError):
        pass
        
    options.pop()
    rules.pop()
    return None


def process_text(inl,oul,cor,rules,options,connected_string):
    rules.append('stringMatch')
    options.append({})
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
            for x in options:
                del[x['inverseResult']]
        
        elif cor and not output:
            multiple_spaces = multiple_spaces_re.search(connected_string)
            if multiple_spaces:
                options[-1]['treatMultipleSpacesAsOne'] = True
                if test_rules(inl,oul,['stringMatch'],[options[-1]]):
                    return parse_rules(rules,options)
            options[-1]['ignoreLeadingAndTrailingSpaces'] = True
            if test_rules(inl,oul,['stringMatch'],[options[-1]]):
                    return parse_rules(rules,options)
        else:
            return parse_rules(rules,options)
    except (CheckError,TypeError):
        pass
    options.pop()
    rules.pop()
    return None


def process_symbolic(inl,oul,cor,rules,options,separators):
    rules.append('equivSymbolic')
    options.append({**separators})
    text_test = bool(closing_text_re.search(inl))
    if text_test:
        options[-1]['ignoreText'] = True
    
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
            for x in options:
                del[x['inverseResult']]
        
        elif cor and not output:
            for decimal_place in range(10):
                options[-1]['significantDecimalPlaces'] = decimal_place+1
                if test_rules(inl,oul,['equivSymbolic'],[options[-1]]):
                    return parse_rules(rules,options)
            
            
        else:
            return parse_rules(rules,options)
    except (CheckError,TypeError,AttributeError,decimal.DecimalException):
        pass
    options.pop()
    rules.pop()
    return None
        
    
        
def get_rule(inl,oul,cor,add_info,iteration):
    connected_string = inl+'~'+oul
    rules = []
    options = []
    separators = get_separators(connected_string,iteration)
    if separators is None:
        return 'Undefined'
    if add_info[0] == 'Yes':
        rules.append('isFactorised')
        options.append(separators.copy())
    if add_info[1] == 'Yes':
        rules.append('isExpanded')
        options.append(separators.copy())
    if add_info[2] == 'Yes':
        return 'Error_NoMatchingRuleForRationalized'
    if add_info[3] == 'Yes':
        rules.append('isSimplified')
        options.append(separators.copy())
    unit = latex_units_re.search(oul)
    if unit:
        tmp = process_units(inl,oul,cor,rules,options,unit,separators.copy())
        if tmp:
            return tmp
    inequation_test = inequation_re.search(connected_string)
    if inequation_test:
        tmp = process_inequation(inl,oul,cor,rules,options,separators.copy())
        if tmp:
            return tmp

    equation_test_in = len(equation_re.findall(inl))
    equation_test_out = len(equation_re.findall(oul))
    if equation_test_in == 1 and equation_test_out == 1:
        tmp = process_equation(inl,oul,cor,rules,options,separators.copy())
        if tmp:
            return tmp             
    tmp = process_literal(inl,oul,cor,rules,options,separators.copy(),connected_string)
    if tmp:
        return tmp
    
    tmp = process_symbolic(inl,oul,cor,rules,options,separators.copy())
    if tmp:
        return tmp
    tmp = process_text(inl,oul,cor,rules,options,connected_string)
    if tmp:
        return tmp
    return get_rule(inl,oul,cor,add_info,iteration+1)

                 
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Invalid number of arguments')
    else:
        test_file_name = sys.argv[1]
        out_file_name = sys.argv[2]
        errors_file_name = os.path.splitext(out_file_name)[0] + '_errors' + os.path.splitext(out_file_name)[1]
    with open(test_file_name, 'r', encoding='utf-8') as test_file, open(out_file_name,'w',encoding='utf-8') as out_file, open(errors_file_name,'w',encoding='utf-8') as errors_file :
        writer = csv.writer(out_file, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer_error = csv.writer(errors_file, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        success = 0
        last_id = -1
        input_latexes = []
        last_output_latex = ''
        errors = 0
        for row in csv.reader(test_file):
            try:
                test_id = row[0]
                try:
                    input_latex = mathml_to_latex(re.sub(r'&nbsp;','&#32;',row[4]))[1:-1].translate(str.maketrans(swap_dict))
                except (lxml.etree.XMLSyntaxError,lxml.etree.XSLTApplyError) as e:
                    writer_error.writerow([test_id,row[4],'BAD XML SYNTAX: INPUT'])
                    errors += 1
                    last_id = test_id
                    continue
                    
                    
                if last_id == test_id:
                    if input_latex in input_latexes:
                        continue
                    input_latexes += [input_latex]
                    output_latex = last_output_latex
                    
                else:
                    try:
                        output_latex = mathml_to_latex(re.sub(r'&nbsp;','&#32;',row[3]))[1:-1].translate(str.maketrans(swap_dict))
                        last_output_latex = output_latex
                        input_latexes = [input_latex]
                    except (lxml.etree.XMLSyntaxError,lxml.etree.XSLTApplyError) as e:
                        writer_error.writerow([test_id,row[3],'BAD XML SYNTAX: OUTPUT'])
                        last_id = test_id
                        errors+= 1
                        continue
                        
                correctness = False if row[2] == 'false' else True
                rule = get_rule(input_latex,output_latex,correctness, row[5:9],0)
                if re.search(r'(Undefined|Error)',rule):
                    writer_error.writerow([test_id,rule,input_latex,output_latex,rule,row[2]])
                    errors += 1
                else:
                    writer.writerow([test_id,rule,input_latex,output_latex,rule,row[2]])
                    success += 1
                #LC print('{}:{} | {}, rule={}'.format(test_id,input_latex,output_latex,rule))
                last_id = test_id
            except IndexError:
                errors += 1
        print('Successfully converted {} and encountered {} that were not able to convert or failed'.format(success,errors))

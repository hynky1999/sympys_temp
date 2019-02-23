#!/usr/bin/env python3

import csv
import sys
from lxml import etree
from checks import check_func, UNITS,POSSIBLE_DECIMAL_SEP,POSSIBLE_THOUSANDS_SEP,DEFAULT_DECIMAL_SEP,DEFAULT_THOUSANDS_SEP
import lxml.html
import os
import re

#Unit tests
latex_units_re = re.compile('|'.join(['{\\text{('+text+')}' for text in UNITS]))

#Inequation tests
inequation_re = re.compile(r'[<>≥≤≠]')

#Equation tests
equation_re = re.compile(r'=')

#Literal tests
intervals_re = re.compile(r'[([]\s*-?[0-9∞]+,\s*-?[0-9∞]+[])]')
decimal_re = re.compile(r'\d+\.\d')
special_latex_re = re.compile(r'\\')
variables_re = re.compile(r'[^a-z][a-z]{1,3}[^a-z]',flags=re.IGNORECASE)
trailing_zeros_re = re.compile(r'(?<=\.)([1-9]*)0+\b')

literals_tests = [intervals_re,decimal_re,special_latex_re,variables_re,trailing_zeros_re]

#Symbolic tests
times = r'(\*|\\cdot ?|\\times ?)?'
coefficient_of_one_re = re.compile(r'(?<![0-9].)1' + times + r'(?=[a-z(\\])', flags=re.IGNORECASE)
text_re = re.compile(r'[a-z]', flags=re.IGNORECASE)

#String tests
multiple_spaces_re = re.compile(r' {2,}')


def mathml_to_latex(eq):
    xslt_file = os.path.join(os.path.dirname(__file__),'xsl_yarosh', 'mmltex.xsl')
    try:
        dom = lxml.html.fromstring(eq)
        xslt = etree.parse(xslt_file)
        transform = etree.XSLT(xslt)
        newdom = transform(dom)
        return str(newdom)
    except lxml.etree.ParserError:
        return ''
    
    return {}
def parse_rules(rules,options):
    final_string = ''
    for i,rule in enumerate(rules):
        ops = ','.join(list([x+("=['{}']".format(options[i][x]) if options[i][x] is not True else '') for x in options[i].keys()]))
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
        if  check_func[rules[index]](inl,expected_latex=oul,options = options[index]) == 'false':
            return False
    return True
def process_units(inl,oul,cor,rules,options,units_list,separators):
    rules.append('isUnit')
    options.append({'allowedUnits':list(map(lambda x: x.group(1),units_list)),**separators})
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            if check_func['equivValue'](inl,oul,separators):
                return parse_rules(rules+['equivValue'],options+[separators])
            else:
                return parse_rules(rules,options)
        elif not cor and output:
            rules.append('equivValue')
            options.append(separators)
            if not check_func['equivValue'](inl,oul,separators):
                return parse_rules(rules,options)
            else:
                for x in options:
                    x['inverseResult'] = True
                if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
        elif not cor and not output:
            return parse_rules(rules,options)
    except (ValueError,AttributeError,TypeError):
        return 'Error_Units'
        pass
    return 'isUnit'
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
        elif not cor and not output:
            return parse_rules(rules,options)
    except (ValueError,AttributeError,TypeError):
        return 'Error_Inequation'
    return 'isTrue'



def process_equation(inl,oul,cor,rules,options,separators):
    rules.append('equivSymbolic')
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
        
        elif cor and not output:
            options[-1]['ignoreText'] = True
            if check_func['equivSymbolic'](inl,expected_latex=oul,options = options[-1]):
                return parse_rules(rules,options)
        else:
            return parse_rules(rules,options)
    except (ValueError,AttributeError,TypeError):
        return 'Error_Equation'
    options.pop()
    rules.pop()
    return None


def process_literal(inl,oul,cor,rules,options,separators,connected_string):
    rules.append('equivLiteral')
    options.append({**separators})
    intervals_test = intervals_re.search(connected_string)
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
        
        elif cor and not output:
            options[-1]['ignoreOrder'] = True
            if check_func['equivLiteral'](inl,expected_latex=oul,options = options[-1]):
                return parse_rules(rules,options)
            
            
        else:
            return parse_rules(rules,options)
    except (ValueError,AttributeError,TypeError):
        return 'Error_Literal'
        
    
    options.pop()
    rules.pop()
    
    return None

def process_text(inl,oul,cor,rules,options,separators,connected_string):
    rules.append('stringMatch')
    options.append({**separators})
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
        
        elif cor and not output:
            multiple_spaces = multiple_spaces_re.search(connected_string)
            if multiple_spaces:
                options[-1]['treatMultipleSpacesAsOne'] = True
                if check_func['equivSymbolic'](inl,expected_latex=oul,options = options[-1]):
                    return parse_rules(rules,options)
            options[-1]['ignoreLeadingAndTrailingSpaces'] = True
            if check_func['equivSymbolic'](inl,expected_latex=oul,options = options[-1]):
                    return parse_rules(rules,options)
        else:
            return parse_rules(rules,options)

        
    except (ValueError,AttributeError,TypeError):
        return 'Error_String'
    
    options.pop()
    rules.pop()
    
    return None


def process_symbolic(inl,oul,cor,rules,options,separators,connected_string):
    rules.append('equivSymbolic')
    options.append({**separators})
    text_test = text_re.search(connected_string)
    try:
        output = test_rules(inl,oul,rules,options)
        if cor and output:
            return parse_rules(rules,options)
        elif not cor and output:
            for x in options:
                x['inverseResult'] = True
            if not test_rules(inl,oul,rules,options):
                    return parse_rules(rules,options)
        
        elif cor and not output:
            options[-1]['ignoreText'] = True
            if check_func['equivSymbolic'](inl,expected_latex=oul,options = options[-1]):
                return parse_rules(rules,options)
            for decimal_place in range(10):
                options[-1]['significantDecimalPlaces'] = decimal_place+1
                if check_func['equivSymbolic'](inl,expected_latex=oul,options = options[-1]):
                    return parse_rules(rules,options)
            
            
        else:
            return parse_rules(rules,options)
    except (ValueError,AttributeError,TypeError):
        return 'Error_Symbolic'
    
    options.pop()
    rules.pop()
    
    return None
        
    
        
def get_rule(inl,oul,cor,add_info):
    connected_string = inl+'~'+oul
    rules = []
    options = []
    separators = {}
    if add_info[0] == 'Yes':
        rules.append('isFactorised')
        options.append(separators)
    if add_info[1] == 'Yes':
        rules.append('isExpanded')
        options.append(separators)
    if add_info[2] == 'Yes':
        return 'Error_NoMatchingRuleForRationalized'
    if add_info[3] == 'Yes':
        rules.append('isSimplified')
        options.append(separators)
    units_list = latex_units_re.findall(oul)
    if units_list:
        return process_units(inl,oul,cor,rules,options,units_list,separators)
    
    inequation_test = inequation_re.search(connected_string)
    if inequation_test:
        return process_inequation(inl,oul,cor,rules,options,separators)

    equation_test = equation_re.search(connected_string)
    if equation_test:
        tmp = process_equation(inl,oul,cor,rules,options,separators)
        if tmp:
            return tmp
    
    if any([reg.search(connected_string) for reg in literals_tests]):                
        tmp = process_literal(inl,oul,cor,rules,options,separators,connected_string)
        if tmp:
            return tmp
    
    tmp = process_symbolic(inl,oul,cor,rules,options,separators,connected_string)
    if tmp:
        return tmp
    tmp = process_text(inl,oul,cor,rules,options,separators,connected_string)
    if tmp:
        return tmp
    
    return 'Undefined'

                 
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Invalid number of arguments')
    else:
        test_file_name = sys.argv[1]
        out_file_name = sys.argv[2]
        errors_file_name = os.path.splitext(out_file_name)[0] + '_errors' + os.path.splitext(out_file_name)[1]
    with open(test_file_name, 'r', encoding='utf-8') as test_file, open(out_file_name,'w',newline='',encoding='utf-8') as out_file, open(errors_file_name,'w',newline='',encoding='utf-8') as errors_file :
        writer = csv.writer(out_file, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer_error = csv.writer(errors_file, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        success = 0
        last_id = -1
        input_latexes = []
        errors = 0
        for row in csv.reader(test_file):
            try:
                test_id = row[0]
                input_latex = mathml_to_latex(row[3]).strip('$')
                if last_id == test_id:
                    if input_latex in input_latexes:
                        continue
                    input_latexes += [input_latex]
                else:
                    input_latexes = [input_latex]
                correctness = False if row[2] == 'false' else True
                output_latex = mathml_to_latex(row[4]).strip('$')
                rule = get_rule(input_latex,output_latex,correctness, row[5:9])
                if re.search(r'(Undefined|Error)',rule):
                    writer_error.writerow([test_id,rule,input_latex,output_latex,rule,correctness])
                    errors += 1
                else:
                    writer.writerow([test_id,rule,input_latex,output_latex,rule,row[2]])
                    success += 1
                print('{}:{} | {}, rule={}'.format(test_id,input_latex,output_latex,rule))
                last_id = test_id
            except IndexError:
                errors += 1
        print('Successfully ruled {} and encountered {} errors'.format(success,errors))

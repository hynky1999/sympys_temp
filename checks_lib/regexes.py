import re
from checks_lib.default_values import (interval_opening,
                                       interval_closing,
                                       separator_functions,
                                       latex_separators,
                                       separator_pairs)

curl_br = '(?:[^{}]*?(?:\{[^{}]+?\})?)*?'

times = r'(\* ?|\\cdot ?|\\times ?)?'

times_re = re.compile(r'(\*|\\cdot ?|\\times)')

#Regexes preprocess latex
percent_re = re.compile(
r'(^|[+-/* ])(.+)\\%')

log_re = re.compile(
r'\\log_([^{])')

multiple_spaces_re = re.compile(
' {2,}')

variable_before_parentheses_re = re.compile(
r'\b([abcdxyz])\(')

trailing_zeros_re = re.compile(
r'(\.[0-9]*?)0+\b')

neg_fraction_re = re.compile(
r'-\\frac\{(.*?)\}\{(.*?)\}')

closing_text_re = re.compile(
r'(^|[^\\a-zA-Z])[a-zA-Z]+')

closing_text_decorated_re = re.compile(
r'(\\text\{.*?\})')

closed_to_normal_text_re = re.compile(
r'\\text\{(.*?)\}')

mixed_frac_re = re.compile(
r'-?\s*[0-9]+(\s*\\frac{[^-]+?}{[^-]+?}|\s+\(?\d+\)?/\(?\d+\)?)')

mixed_fraction_error_re = re.compile(
r'[0-9] *\( *[0-9]+ */ *[0-9]+ *\)')

parenthesis_re = re.compile(
r'\((-?[a-z]|\d+(?:.\d+)?)\)')

matrix_form_re = re.compile(
r'\\begin\{bmatrix\}(.*?)\\end{bmatrix}')

interval_form_re = re.compile(
r'\s*([{}])([^,]*?),([^,]*?)([{}])\s*'
.format(
re.escape(''.join(interval_opening.keys())),
re.escape(''.join(interval_closing.keys()))))

set_form_re = re.compile(
(r'\{{\s*(?P<var>[a-zA-Z])\s*\|\s*(?:(?P<num1>\d*)\s*(?P<sign1>{0}))'
+ r'?\s*\1\s*(?:(?P<sign2>{0})\s*(?P<num2>\d*))?\s*\}}')
.format(
'|'.join(separator_functions.keys())))

eq_form_re = re.compile(
r'^(?P<l>.*?)(?P<sign>{})(?P<r>.*)$'
.format(
'|'.join(separator_functions.keys())))

integral_re = re.compile(
r'\\int(_(?P<down>{0})\^\{{(?P<up>{0})\}})?\s*(?P<expr>.*?)d(?P<symbol>[a-z])'
.format(curl_br))

sums_re = re.compile(
r'\\sum_\{{([a-z])\=({0})\}}\^\{{({0})\}}(.*)'
.format(curl_br))

limits_re = re.compile(
r'\\lim_\{{({0})\\to({0})\}}(.*)'
.format(curl_br))

#Regexes sympify latex

not_latex_re = re.compile(
r'NotLatex:')

format_latex_re = re.compile(
r'Format\((.*?)\)Format')

format_func_re = re.compile(
r'Format:(?P<func>.+?)\((.*?)\)Format:(?P=func)')

latex_sign_re = re.compile(
'|'.join(map(re.escape,latex_separators.keys())))
 
scientific_re = re.compile(
r'e(-?\d+)',re.IGNORECASE)


#Other
diffentiation_re = re.compile(
r'\\frac\{d\}\{d([a-z]+)\}(.*)')

integral_der_re = re.compile(
r'\\int(?!_)(.*?)(d[a-z])')

separator_re = re.compile(
'|'.join(separator_pairs.keys()))

parentheses_minus_re = re.compile(r'\((-?\d*?)\)')

coefficient_of_one_re = re.compile(
                        r'(?<![0-9].)1'
                        + times
                        + r'(?=[a-z(\\])'
                        , flags=re.IGNORECASE)
                        
constituent_parts_re = re.compile(
r'[^\s()*+-]')

leading_zero_re = re.compile(
r'\b0(?=\.)')

escaped_par_re = re.compile(
r'\\([\{\[\(\}\]\)])'
)
left_par_re = re.compile(
r'\\left([\{\(\[])'
)
right_par_re = re.compile(
r'\\right([\}\)\]])'
)
trailing_zeros_re = re.compile(
r'(\.[0-9]*?)0+\b')

preceding_zeroes_re = re.compile(
r'(?<![\d\.])(0+)(\d+?)')

no_solution_re = re.compile(r'\s*no\s*solution\s*$')

JS_support = re.compile(
'Not supported in Javascript')

#Regexes for sets
set_re_brackets = re.compile(
r'(\[)([^|]*?)(\])$')

set_re_par = re.compile(
r'(\()([^|]*?)(\))$')

set_re_par2 = re.compile(
r'(\{)([^|]*?)(\})$')

set_re_error = re.compile(
r'^\s*[({].*?\d{1,3},\d{1,2}[^\d].*?[})]\s*$')

set_res = [set_re_brackets,set_re_par,set_re_par2]

#Regexes for equivSyntax
coeff = r'([A-Wa-w]|\d+(\.\d+)?|-?\d+/-?\d+|\\frac\{-?\d+\}\{-?\d+\}|'\
    + r'\d+ *(\d+/\d+|\\frac\{\d+\}\{\d+\})|)'
        
decimal_re_pattern = r'^\d+\.\d{{{}}}$'

simple_frac_re = re.compile(
r'^(-?\d+/-?\d+|-?\d+\\div-?\d+|-?\\frac\{-?\d+\}\{-?\d+\})$')

exp_re = re.compile(
r'^(([A-Wa-w]+|\d+(\.\d+)?)\^(\{.*[x-z].*\}|[x-z])|exp\(.*[x-z].*\))$')

standard_form_linear_re = re.compile(
r'^-?{} *{} *x *[+-] *{} *{} *y *= *-?{}$'.format(
coeff, times, coeff, times, coeff))

standard_form_quadratic_re = re.compile(
r'^-?{} *{} *x\^(2|[{{]2[}}]) *[+-] *{} *{} *x *[+-] *{} *= *0$'.format(
coeff, times, coeff, times, coeff))

slope_intercept_form_re = re.compile(
r'^y *= *-?{} *{} *x *[+-] *{}$'.format(
coeff, times, coeff))

point_slope_form_re = re.compile(
(r'^(\(y *[+-] *{}\)|y *([+-] *{})?)'
+ r'*= *(-?{} *{} *\(x *[+-] *{}\)|x *([+-] *{})?)$').format(
coeff, coeff, coeff, times, coeff, coeff))

#Factorised
factorised_re = re.compile(
'^\(.*[\)\)].*\)$')

#Number checking
integer = r'\s*-?\s*\d+\s*'
number = r'\s*-?\s*\d+(\.\d+)?\s*'

sci_num_type_re = re.compile(r'\s*-?\s*(?P<number>\d+(\.\d+)?)\s*'
+ times + r'\s*10\s*\^\s*(' + number + r'|\{' + number + r'})\s*$')

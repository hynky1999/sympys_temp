DEFAULT_THOUSANDS_SEP = ','
DEFAULT_DECIMAL_SEP = '.'
POSSIBLE_THOUSANDS_SEP = ',. '
POSSIBLE_DECIMAL_SEP = ',.'
THOUSANDS_SEP_PLACEHOLDER = '<THOUSANDSEP>'
DECIMAL_SEP_PLACEHOLDER = '<DECIMALSEP>'
SEP_ERROR_PLACEHOLDER = '<SEPERROR>'
DEFAULT_PRECISION = 10
ERROR = 'error'

interval_opening = {
    '(': True,
    '[': False
}

interval_closing = {
    ')': True,
    ']': False
}

#Signs that must be used in both expected and student input
separator_pairs = {
    '>=':'<=',
    '<=':'>=',
    '>':'<',
    '<':'>',
    '=':'='
}

separator_functions = {
    '>=': 'GreaterThan(Format({})Format,Format({})Format)',
    '<=':'LessThan(Format({})Format,Format({})Format)',
    '>':'StrictGreaterThan(Format({})Format,Format({})Format)',
    '<':'StrictLessThan(Format({})Format,Format({})Format)',
    '=':'Equality(Format({})Format,Format({})Format)',
    '≠':'Unequality(Format({})Format,Format({})Format)'
}

#Latex to math conversion of signs
latex_separators = {
    r'\geq':'>=',
    r'\ge':'>=',
    r'\gt':'>',
    r'\leq':'<=',
    r'\le':'<=',
    r'\lt':'<',
    r'\eq':'=',
    r'\neq':'≠'
}

check_func = {
    'evaluateGraphEquations': 'equiv_graph',
    'equivSymbolic': 'equiv_symbolic',
    'equivLiteral': 'equiv_literal',
    'equivValue': 'equiv_value',
    'stringMatch': 'string_match',
    'isSimplified': 'is_simplified',
    'isExpanded': 'is_expanded',
    'isFactorised': 'is_factorised',
    'isRationalized': 'is_rationalized',
    'isRational': 'is_rational',
    'isTrue': 'is_true',
    'isUnit': 'is_unit',
    'equivSyntax': 'equiv_syntax',
    'setEvaluation': 'equiv_set',
    'calculate': 'calculate',
    'convertLatex2Js': 'convert_JS'
}


# a dictionary of possible main options and their respective
# sets of suboptions; will be used to check validity
# of option combinations passed to the script
allowed_options = {
    'convertLatex2Js':{},
    'evaluateGraphEquations':{},
    'equivSymbolic': {
        'allowEulersNumber',
        'setThousandsSeparator',
        'tolerance',
        'setDecimalSeparator',
        'inverseResult',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'significantDecimalPlaces',
        'compareSides',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'equivLiteral': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'inverseResult',
        'ignoreTrailingZeros',
        'ignoreOrder',
        'ignoreCoefficientOfOne',
        'allowEulersNumber',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'equivValue': {
        'tolerance',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'ignoreText',
        'ignoreAlphabeticCharacters',
        'compareSides',
        'inverseResult',
        'significantDecimalPlaces',
        'allowEulersNumber',
        'complexType',
        'integerType',
        'realType',
        'isFactorised',
        'isExpanded',
        'isSimplified',
        'isRationalized',
        'isRational',
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'setEvaluation',
        'orderedElements',
        'orderedPair',
        'interpretAsList',
        'interpretAsSet'},
    'isSimplified': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isFactorised': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isExpanded': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isRationalized': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isRational': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber',
        'realType',
        'integerType',
        'complexType'},
    'isTrue': {
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber'},
    'isUnit': {
        'allowedUnits',
        'setThousandsSeparator',
        'setDecimalSeparator',
        'inverseResult',
        'allowEulersNumber'},
    'stringMatch': {
        'ignoreLeadingAndTrailingSpaces',
        'treatMultipleSpacesAsOne',
        'inverseResult'},
    'equivSyntax': {
        'isDecimal',
        'isSimpleFraction',
        'isMixedFraction',
        'isExponent',
        'isStandardForm',
        'isSlopeInterceptForm',
        'isPointSlopeForm',
        'realType',
        'integerType',
        'numberType',
        'scientificType',
        'variableType',
        'complexType'},
    'setEvaluation': {
        'inverseResult',
        'orderedElements',
        'orderedPair'},
    'calculate': {},
}

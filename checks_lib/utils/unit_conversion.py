import re
import os
import csv

UNITS = {
    # Unit, Description, ConvertTo, Coefficient
    # SI
    'g':  ('gram', 'g', 1),
    'cg': ('centigram', 'g', 0.01),
    'kg': ('kilogram', 'g', 1000),
    'mg': ('milligram', 'g', 0.001),
    'ng': ('nanogram', 'g', 0.000000001),
    'm':  ('meter', 'm', 1),
    'cm': ('centimeter', 'm', 0.01),
    'km': ('kilometer', 'm', 1000),
    'mm': ('millimeter', 'm', 0.001),
    'nm': ('nanometer', 'm', 0.000000001),
    's':  ('second', 's', 1),
    'cs': ('centisecond', 's', 0.01),
    'ks': ('kilosecond', 's', 1000),
    'ms': ('millisecond', 's', 0.001),
    'ns': ('nanosecond', 's', 0.000000001),
    'L':  ('liter', 'L', 1),
    'mL': ('milliliter', 'L', 0.01),
    # US
    'in':  ('inch', 'in', 1),
    'ft':  ('foot', 'in', 12),
    'mi':  ('mile', 'in', 63360),
    'fl':  ('fluid ounce', 'fl', 1),
    'cup': ('cup', 'fl', 8),
    'pt':  ('pint', 'fl', 16),
    'qt':  ('quart', 'fl', 32),
    'gal': ('gallon', 'fl', 128),
    'oz':  ('ounce', 'oz', 1),
    'lb':  ('pound', 'oz', 16),
    r'\\degree': (r'\degree', r'\degree', r'2*\pi'),
    r'\\\$': (r'\$', r'\$', '1')
}

UNIT_FOLDER = 'units'
SI_CSV = 'si.csv'
US_CSV = 'us.csv'
si_csv_path = os.path.join(UNIT_FOLDER, SI_CSV)
us_csv_path = os.path.join(UNIT_FOLDER, US_CSV)

#List containing all units both long and short names
units_list = [v[0] for v in UNITS.values()] + [k for k in UNITS.keys()]

units = [r'({})(?:\^{{?(-?\d*)}}?)?(\*)?'
.format(u) for u in sorted(units_list,key=len,reverse=True)]

unit_text_re = re.compile(
r'(?<=[^a-zA-Z\\])(?:\\text{{)?(?P<up>(?:{0})+)(?P<down>\/(?:{0})+)?(?:}})?(?:(?=\=)|$)'
.format('|'.join(units)))


def swap_units(input_latex,expected_latex):
    expected_unit_search = unit_text_re.search(expected_latex)
    if expected_unit_search:
        if not unit_text_re.search(input_latex):
            raise ValueError('No unit in input')
        expected_unit = convertComplexUnit(expected_unit_search)
        expected_latex = unit_text_re.sub(lambda x:'('
                                        + convertComplexUnit(x)
                                        + '/'
                                        + expected_unit
                                        + ')'
                                        ,expected_latex)
        input_latex = unit_text_re.sub(lambda x:'('
                                        + convertComplexUnit(x)
                                        + '/'
                                        + expected_unit
                                        + ')'
                                        ,input_latex)

    else:
        if unit_text_re.search(input_latex):
            raise ValueError('No unit in expected')
        
    return input_latex,expected_latex

def load_units(units_csv_path):
    ''' Load conversion tables for SI/US units
    '''
    conversion_table = {}
    with open(units_csv_path, 'r', encoding='utf-8') as csv_file:
        csv_file.readline()


def convertComplexUnit(unit_latex):
    units_dict = dict(zip(units_list,[v[2] for v in UNITS.values()]*2))
    
    def convertUnits(unit):
        output=''
        g = unit.groups()
        for u_i,unit_mark in enumerate(g[::3]):
            if not unit_mark:
                continue
                
            output += str(units_dict[unit_mark])
            if g[3*u_i+1]:
                output = '({})^{{{}}}'.format(output,str(g[3*u_i+1]))
                
            output = r'*' + output
            break
            
        return output
    
    units_re = re.compile('|'.join(units))
    output = '({})'.format(
        units_re.sub(convertUnits,unit_latex.group('up'))[1:])
    if unit_latex.group(2):
        output += r'/({})'.format(
        units_re.sub(convertUnits,unit_latex.group('down'))[2:])
    
    return output

if __name__ == '__main__':
    print(swap_units('1s','2s') == swap_units('1((1)/(1))', '2((1)/(1))'))

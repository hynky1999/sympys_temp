import re
from checks_lib.default_values import allowed_options
from checks_lib.utils.unit_conversion import units_list
from collections import OrderedDict
no_set_decimal_separator = {main for main in allowed_options 
                            if 'setDecimalSeparator' not in allowed_options[main]}

set_thousand_separator_re = re.compile(
r"(?<=setThousandsSeparator=)?\[([ ,.']+)\]")

thousand_separator_re = re.compile(
r"'([ .,])'")

set_decimal_separator_re = re.compile(
r"(?<=setDecimalSeparator=)?'([,.])'")

tolerance_re = re.compile(
r"(?<=tolerance=)?'([,.])'")

allowed_units_re = re.compile(
r"(?<=allowedUnits=)?\[(.+?)\]")

unit_re = re.compile(
r"'(.+?)'")

non_boolean_suboption_re = re.compile(
r'^(setThousandsSeparator|setDecimalSeparator|tolerance|allowedUnits)=')

equiv_syntax_option_re_list = [re.compile(r'(isDecimal)=(\d+)')]

def sub_thousand_separator(matchobj):
    return ''.join(thousand_separator_re.findall(matchobj.group(1))
                   ).replace(',', '<COMMA>')

def sub_comma(matchobj):
    return matchobj.group(1).replace(',', '<COMMA>')

def parse_checks(options_str):
    ''' Parse option string
    '''
    # first, split groups of options
    check_list = options_str.split(';')
    # second, split each 
    check_dict = OrderedDict()
    for check_string in check_list:
        add_dict = {'setDecimalSeparator': '.'}
        if ':' in check_string:
            check_string = set_thousand_separator_re.sub(
                        sub_thousand_separator
                        ,check_string)
            check_string = set_decimal_separator_re.sub(
                        sub_comma
                        ,check_string)
            check_string = allowed_units_re.sub(
                        sub_comma,
                        check_string)

            main, add_string = check_string.split(':', maxsplit=1)
            add_list = add_string.split(',')
            for add in add_list:
                if '=' not in add:
                    add_dict[add] = True
                else:
                    add, sep = add.split('=')
                    sep = sep.replace('<COMMA>', ',')
                    if add == 'allowedUnits':
                        #Checking of allowed units
                        units = []
                        sep_tmp = []
                        for unit in sep.split(','):
                            unplurar_units = str(re.sub('([a-z]+?)(?:es|s)?',r'\1'
                                                ,unit.strip().strip("'").lower()))
                            divide_split = re.split(r'\/',unplurar_units)
                            for split_i,split in enumerate(divide_split):
                                units += re.split('\*',split)
                            sep_tmp += [unit]
                        # sanity check for allowed units
                        for unit in units:
                            if unit not in units_list:
                                raise Exception(
                                '{} is not a valid SI or US Customary unit'.format(
                                                                              unit))
                        sep = sep_tmp
                    elif add == 'tolerance':
                        if '%' not in sep:   
                            try:
                                sep = float(sep)
                            except ValueError:
                                raise Exception(
                                '{} is not a valid float value for tolerance'.format(
                                                                                sep))
                    elif add == 'significantDecimalPlaces':
                        try:
                            sep = int(sep)
                        except ValueError:
                            raise Exception(
                            '{} is not a valid int value for significantDecimalPlaces'.format(
                                                                                          sep))
                    add_dict[add] = sep
        else:
            main = check_string
        if main in no_set_decimal_separator:
            add_dict.pop('setDecimalSeparator')
        if main not in allowed_options:
            
            raise Exception(
            'Option "{}" not allowed'.format(
                                        main))

        for add in add_dict:
            if add not in allowed_options[main]:
                raise Exception(
                        'Suboption "{}" '.format(add)
                        + 'not allowed for option "{}"'.format(
                                                         main))

        if 'setDecimalSeparator' in add_dict and\
           'setThousandsSeparator' in add_dict and\
           add_dict['setDecimalSeparator'] in add_dict['setThousandsSeparator']:
                raise Exception(
                'Same decimal and thousand separators for option "{}"'.format(
                                                                         main))
                

        check_dict[main] = add_dict
    return check_dict

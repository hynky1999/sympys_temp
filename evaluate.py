#!/usr/bin/env python3.6

import sys
from argparse import ArgumentParser

from checks import equiv_symbolic, string_match, is_expanded
from checks import parse_checks, check_func

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-i', dest='input',
                        action='store', type=str, default=None,
                        help="input LaTeX string (a student's answer)")
    parser.add_argument('-e', dest='expected',
                        action='store', type=str, default=None,
                        help='expected string against which the comparison '
                             'is being done (the correct answer)')
    parser.add_argument('-s', dest='checks',
                        action='store', type=str, default=None,
                        help='check options with suboptions')
    args = parser.parse_args()

    if args.input is None or\
       args.expected is None or\
       args.checks is None:
        parser.print_help()
        sys.exit(0)

    check_list = parse_checks(args.checks)
        
    return args.input, args.expected, check_list

if __name__ == '__main__':
    input_latex, expected_latex, checks = parse_args()

    # perform all checks
    for check in checks:
        result = check_func[check](input_latex, expected_latex, checks[check])
        if result != 'true':
            print(result)
            break
    else:
        print('true')

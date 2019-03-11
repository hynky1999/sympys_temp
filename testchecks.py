#!/usr/bin/env python3.6

import csv
import sys

from checks import parse_checks, check_func, is_simplified

def test_case(input_latex, expected_latex, options):
    checks = parse_checks(options)

    # perform all checks
    for check in checks:
        result = check_func[check](input_latex.strip('$'),
                                   expected_latex=expected_latex.strip('$'),
                                   options=checks[check])
        if result != 'true':
            test_result = result
            break
        else:
            test_result = 'true'
    return test_result

if __name__ == '__main__':
    if len(sys.argv) == 2:
        test_file_name = sys.argv[1]
    else:
        test_file_name = 'tests.csv'

    test_count, fail_count, fails = 0, 0, []
    with open(test_file_name, 'r', encoding='utf-8') as test_file:
        for row in csv.reader(test_file):
            testno, desc, input_latex, expected_latex, options, expected_result = row
            test_result = test_case(input_latex, expected_latex, options)
            if test_result != expected_result:
                fails.append(row + [test_result])
                fail_count += 1
            test_count += 1

    print('{} checks passed, {} failed'.format(test_count - fail_count, fail_count))
    for testno, desc, input_latex, expected_latex, options, expected_result, result in fails:
        print(testno, desc, sep='\t', end=': ')
        print('expected "{}", got "{}"'.format(expected_result, result))

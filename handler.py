import csv
import sys
import json

from checks import equiv_symbolic, equiv_literal, string_match
from checks import is_simplified, is_expanded, is_factorised
from checks import is_true
from checks import parse_checks, check_func

def handle(event, context):
    body = json.loads(event["body"])
    if body["input"] is None or\
       body["expected"] is None or\
       body["checks"] is None:
        return {
            "statusCode": 400,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": {
                "message": "Bad Request"
            }
        }
    try:
        checks = parse_checks(body["checks"])
        result = "true"
        for check in checks:
            value = check_func[check](body["input"], body["expected"], checks[check])
            if value != "true":
                result = value
                break

        response = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "result": result
            })
        }

        return response
    except Exception as e:
        response = {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Error occured",
                "message": e
            })
        }
        return response

def test(event, context):
    test_file_name = 'tests.csv'

    test_count, fail_count, fails = 0, 0, []
    with open(test_file_name, 'r', encoding='utf-8') as test_file:
        for row in csv.reader(test_file):
            testno, desc, input_latex, expected_latex, options, expected_result = row
            main, add = parse_checks(options).popitem()

            #print(testno, expected_result, sep='\t')
            test_result = check_func[main](input_latex, expected_latex=expected_latex, options=add)
            if test_result != expected_result:
                fails.append(row + [test_result])
                fail_count += 1
            test_count += 1
    
    report_str = '{} checks passed, {} failed\n'.format(test_count - fail_count, fail_count)
    for testno, desc, input_latex, expected_latex, options, expected_result, result in fails:
        report_str += '{}\t{}: '.format(testno, desc)
        report_str += 'expected "{}", got "{}"\n'.format(expected_result, result)

    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*"
        },
        "body": report_str
    }

    return response

import csv
import sys
import json

from checks import parse_checks, check_func, replace_variables, calculate_expression

def handle(event, context):
    print("Request Body: ")
    print(event["body"])
    try:
        body = json.loads(event["body"])
    except Exception as e:
        response = {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Error occured",
                "message": str(e)
            })
        }
        return response

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
                "error": "Internal Server Error",
                "message": str(e)
            })
        }
        return response

def calculate(event, context):
    try:
        body = json.loads(event["body"])
    except Exception as e:
        response = {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Error occured",
                "message": str(e)
            })
        }
        return response

    if body["latex"] is None or\
       body["variables"] is None:
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
        input_latex = body["latex"]
        variables = body["variables"]

        input_latex = replace_variables(input_latex, variables)
        result = calculate_expression(input_latex)

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
        print(e)
        response = {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal Server Error",
                "message": str(e)
            })
        }
        return response

def test(event, context):
    test_file_name = 'tests.csv'

    try:
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
    except Exception as e:
        response = {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal Server Error",
                "message": str(e)
            })
        }
        return response

# res = handle({
#     "body": "{\"input\": \"\\\\frac{1}{2}\", \"expected\": \"0.5\", \"checks\": \"equivLiteral:\"}"
# }, {})
# print(res)

# res = test({}, {})
# print(res)

# res = calculate({
#     "body": "{ \
#         \"latex\": \"x+y+z+w\", \
#         \"variables\": [ \
#             { \"id\": \"x\", \"type\": \"value\", \"value\": 3 }, \
#             { \"id\": \"y\", \"type\": \"value\", \"value\": 5 }, \
#             { \"id\": \"z\", \"type\": \"formula\", \"value\": \"x+y\" } \
#         ] \
#     }"
# }, {})
# print(res)
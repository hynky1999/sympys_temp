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
        print(e)
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

    if body["latexes"] is None or\
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
        objs = body
        if isinstance(body, dict):
            objs = [body]

        resp_objs = []
        for obj in objs:
            latexes = obj["latexes"]
            variables = obj["variables"]

            result = {}
            for latex in latexes:
                input_latex = latex["formula"]
                
                input_latex = replace_variables(input_latex, variables)
                value = calculate_expression(input_latex)
                result[latex["id"]] = str(value)
            
            resp_objs.append({
                "id": obj["id"],
                "values": result
            })

        response = {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(resp_objs)
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
                checks = parse_checks(options)
                result = 'true'
                for check in checks:
                    test_result = check_func[check](input_latex, expected_latex=expected_latex, options=checks[check])
                    if test_result != 'true':
                        result = test_result
                        break
                    
                if result != expected_result:
                    fails.append(row + [test_result])
                    fail_count += 1
                    break
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
#x = json.dumps({"input":"1 6/8","expected" : "1 #3/4","checks":"equivSymbolic;isSimplified;equivSyntax:isMixedFraction"}
#)
#res = handle({"body":x},{})
#print(res)

# res = calculate({
#     "body": "{ \
#         \"id\": \"example\", \
#         \"latexes\": [ \
#             { \"id\": \"w\", \"formula\": \"x+y+z\" }, \
#             { \"id\": \"k\", \"formula\": \"y+z\" } \
#         ], \
#         \"variables\": [ \
#             { \"id\": \"x\", \"value\": 3 }, \
#             { \"id\": \"y\", \"value\": 5 }, \
#             { \"id\": \"z\", \"value\": \"x+y\" } \
#         ] \
#     }"
# }, {})
# print(res)

# res = test({}, {})
# print(res)

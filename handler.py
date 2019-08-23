import csv
import sys
import json

from checks import parse_checks, check_func, replace_variables, calculate_expression, convert_JS

# Main handler:
#  FrontEnd Endpoint /evaluate
#    body: { "input":"x + 1", "expected":"x+1", "checks":"equivSymbolic" }
#  Incoming:
#     expected:  from teacher,  eg. x+1
#     input:  from student, e.g. x + 1
#     checks: type of check e.g. equivSymbolic
#  Outgoing:
#      value: true/false, in this case true
# 
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

# latex conversion :
#  FrontEnd Endpoint /convertLatex2Js
#    body: { "latex":"y-\\sin{x}=0"}
#  Incoming:
#         latex that needs to be converted into something that can be plotted, .eg. "y-\sin{x}=0"
#  Outgoing:
#      value: the converted input, in this case it will be "y-sin(x)=0"
# 
def convertLatex2Js(event, context):
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

    if body["latex"] is None:
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
        latex = body["latex"]
        result = convert_JS(latex)

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

# Graph handler:
#  FrontEnd Endpoint /graphEvaluate
#    body: { "input":"[['line', [(2.0,2.0),(0.0,4.0)]]],['solid'],[(4.0,0.0)]", "expected":"[['eqn','x+y \gt 4']],[(5,0)]", "checks":"equivSymbolic" }
#  Incoming:
#     expected:  from teacher, Two fields separated by a comma, first the equations, and then the points for shading/selecting the regions
#          eg. [['eqn','x+y \gt 4']],[(5,0)], here it is a line and a point to identify the region
#          Note that the teacher can also enter a JSXGraph object
#
#     input:  from student, Three fields separated by a comma, first the shapes, then the shape line pattern, then the points for shading
#      a shading type for the line, dashed or solid where dashed is for < or > cases. Lastline
#        e.g. [['line', [(2.0,2.0),(0.0,4.0)]]],['solid'],[(4.0,0.0)], here it is a JSXGraph line object, 
#     checks: type of check e.g. equivSymbolic
#  Outgoing:
#      value: true/false, in this case true
# 
def evaluateGraphEquations(event, context):
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

# Endpoint /calculate
#  Incoming:
# [{"id":"1a","latexes":[{"id":"z","formula":"x+y"},{"id":"z2","formula":"x+y^2"}],"variables":[{"id":"x","value":1},{"id":"y","value":2}]}]
#  Outgoing:
#   computes z and z2  based on the variables 
# "[{"id":"1a","values": {"z":"3","z2":"5"}}]"


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

    try:
        objs = body
        if isinstance(body, dict):
            objs = [body]

        resp_objs = []
        for obj in objs:
            if obj["latexes"] is None or\
               obj["variables"] is None:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": {
                        "message": "Bad Request"
                    }
                }

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

#  backend tester
#  takes test cases from a file in the format of:
#   
#    testId,description,input,expected,check,result
#    
#    where "input" is from the student, and "result" is the expected result (true/false) for the given check, input and expected.
#    This returns pass/fail and counts of fails for each test
#
def test(event, context):
    test_file_name = 'tests.csv'

    try:
        test_count, fail_count, fails = 0, 0, []
        with open(test_file_name, 'r', encoding='utf-8') as test_file:
            for row in csv.reader(test_file):
                try:
                    if row == [] or row[0][0] == '#':
                        continue
                except IndexError:
                    pass
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
#x = json.dumps({"input":"1 6/8","expected" : "1 3/4","checks":"equivSymbolic;isSimplified;equivSyntax:isMixedFraction"}
#)
#res = handle({"body":x},{})
#print(res)

# res = calculate({
#     "body": "[{ \
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
#     }]"
# }, {})
# print(res)

res = test({}, {})
print(res)

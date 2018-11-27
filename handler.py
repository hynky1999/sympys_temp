import sys
import json
from checks import equiv_symbolic, string_match, is_expanded
from checks import parse_checks, check_func

def handle(event, context):
    body = json.loads(event["body"])
    if body["input"] is None or\
       body["expected"] is None or\
       body["checks"] is None:
        return {
            "statusCode": 400,
            "body": {
                "message": "Bad Request"
            }
        }
    
    checks = parse_checks(body["checks"])
    result = "true"
    for check in checks:
        value = check_func[check](body["input"], body["expected"], checks[check])
        if value != "true":
            result = value
            break

    response = {
        "statusCode": 200,
        "body": json.dumps({
            "result": result
        })
    }

    return response

# res = handle({
#     "body": "{\"input\": \"\\\\frac{1}{2}\", \"expected\": \"0.5\", \"checks\": \"equivLiteral\"}"
# }, {})
# print(res)

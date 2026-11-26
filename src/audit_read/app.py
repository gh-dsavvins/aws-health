import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ["AUDIT_TABLE"])


def to_json(value):
    if isinstance(value, Decimal):
        return int(value)
    raise TypeError(type(value))


def handler(event, context):
    result = table.query(
        KeyConditionExpression=Key("patient_id").eq(event["pathParameters"]["patient_id"]),
        ScanIndexForward=False,
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result["Items"], default=to_json),
    }
import json
import os
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
TABLES = {
    "a": dynamodb.Table(os.environ["TABLE_A"]),
    "b": dynamodb.Table(os.environ["TABLE_B"]),
}

def source_ip(event):
    return event["requestContext"]["http"]["sourceIp"]

def to_json(value):
    if isinstance(value, Decimal):
        return int(value)
    raise TypeError(type(value))


def response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=to_json),
    }


def create_bill(event):
    params = event["pathParameters"]
    data = json.loads(event["body"])
    item = {
        "patient_id": params["patient_id"],
        "bill_id": str(uuid.uuid4()),
        "amount_cents": data["amount_cents"],
        "description": data["description"],
        "version": 1,
        "modified_by_ip": source_ip(event),
    }
    TABLES[params["table"]].put_item(Item=item)
    return response(201, item)

def update_bill(event):
    params = event["pathParameters"]
    data = json.loads(event["body"])
    try:
        result = TABLES[params["table"]].update_item(
            Key={"patient_id": params["patient_id"], "bill_id": params["bill_id"]},
            UpdateExpression="SET amount_cents = :amount, #d = :description, #v = :new, modified_by_ip = :ip",
            ConditionExpression="#v = :expected",
            ExpressionAttributeNames={"#d": "description", "#v": "version"},
            ExpressionAttributeValues={
                ":amount": data["amount_cents"],
                ":description": data["description"],
                ":expected": data["version"],
                ":new": data["version"] + 1,
                ":ip": source_ip(event),
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(409, {"error": "version conflict"})
        raise
    return response(200, result["Attributes"])

def list_bills(event):
    params = event["pathParameters"]
    result = TABLES[params["table"]].query(
        KeyConditionExpression=Key("patient_id").eq(params["patient_id"])
    )
    return response(200, result["Items"])


def delete_bill(event):
    params = event["pathParameters"]
    TABLES[params["table"]].delete_item(
        Key={"patient_id": params["patient_id"], "bill_id": params["bill_id"]}
    )
    return response(200, {"deleted": params["bill_id"]})


ROUTES = {
    "POST /bills/{table}/{patient_id}": create_bill,
    "PUT /bills/{table}/{patient_id}/{bill_id}": update_bill,
    "GET /bills/{table}/{patient_id}": list_bills,
    "DELETE /bills/{table}/{patient_id}/{bill_id}": delete_bill,
}


def handler(event, context):
    return ROUTES[event["routeKey"]](event)
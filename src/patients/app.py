import json
import os
import uuid
from decimal import Decimal
from botocore.exceptions import ClientError
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

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


def create_patient(event):
    data = json.loads(event["body"])
    item = {
        "patient_id": str(uuid.uuid4()),
        "name": data["name"],
        "date_of_birth": data["date_of_birth"],
        "version": 1,
        "modified_by_ip": source_ip(event),
    }
    table.put_item(Item=item)
    return response(201, item)

def update_patient(event):
    patient_id = event["pathParameters"]["id"]
    data = json.loads(event["body"])
    try:
        result = table.update_item(
            Key={"patient_id": patient_id},
            UpdateExpression="SET #n = :name, date_of_birth = :dob, #v = :new, modified_by_ip = :ip",
            ConditionExpression="#v = :expected",
            ExpressionAttributeNames={"#n": "name", "#v": "version"},
            ExpressionAttributeValues={
                ":name": data["name"],
                ":dob": data["date_of_birth"],
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

def get_patient(event):
    patient_id = event["pathParameters"]["id"]
    result = table.get_item(Key={"patient_id": patient_id}, ConsistentRead=True)
    if "Item" not in result:
        return response(404, {"error": "not found"})
    return response(200, result["Item"])

def list_patients(event):
    return response(200, table.scan()["Items"])


def delete_patient(event):
    patient_id = event["pathParameters"]["id"]
    table.delete_item(Key={"patient_id": patient_id})
    return response(200, {"deleted": patient_id})

ROUTES = {
    "GET /health": lambda event: response(200, {"status": "ok"}),
    "POST /patients": create_patient,
    "GET /patients/{id}": get_patient,
    "PUT /patients/{id}": update_patient,
    "GET /patients": list_patients,
    "DELETE /patients/{id}": delete_patient,
}


def handler(event, context):
    return ROUTES[event["routeKey"]](event)
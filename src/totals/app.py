import os
import time

import boto3
from botocore.exceptions import ClientError

client = boto3.client("dynamodb")
PATIENTS_TABLE = os.environ["PATIENTS_TABLE"]
EVENTS_TABLE = os.environ["EVENTS_TABLE"]


def amount(image):
    return int(image["amount_cents"]["N"])


def handler(event, context):
    for record in event["Records"]:
        data = record["dynamodb"]
        if record["eventName"] == "INSERT":
            count, cents = 1, amount(data["NewImage"])
        elif record["eventName"] == "MODIFY":
            count, cents = 0, amount(data["NewImage"]) - amount(data["OldImage"])
        else:
            count, cents = -1, -amount(data["OldImage"])
        try:
            client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": EVENTS_TABLE,
                            "Item": {
                                "event_id": {"S": record["eventID"]},
                                "expires_at": {"N": str(int(time.time()) + 7 * 86400)},
                            },
                            "ConditionExpression": "attribute_not_exists(event_id)",
                        }
                    },
                    {
                        "Update": {
                            "TableName": PATIENTS_TABLE,
                            "Key": {"patient_id": data["Keys"]["patient_id"]},
                            "UpdateExpression": "SET modified_by_ip = :who ADD bill_count :count, billed_sum_cents :cents",
                            "ExpressionAttributeValues": {
                                ":who": {"S": "system:totals"},
                                ":count": {"N": str(count)},
                                ":cents": {"N": str(cents)},
                            },
                        }
                    },
                ]
            )
        except ClientError as e:
            reasons = e.response.get("CancellationReasons", [])
            if not reasons or reasons[0].get("Code") != "ConditionalCheckFailed":
                raise
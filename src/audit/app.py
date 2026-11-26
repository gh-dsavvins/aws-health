import os

import boto3

client = boto3.client("dynamodb")
AUDIT_TABLE = os.environ["AUDIT_TABLE"]


def handler(event, context):
    for record in event["Records"]:
        data = record["dynamodb"]
        event_key = f"{int(data['ApproximateCreationDateTime'])}#{data['SequenceNumber']}"
        item = {
            "patient_id": data["Keys"]["patient_id"],
            "event_key": {"S": event_key},
            "source_table": {"S": record["eventSourceARN"].split("/")[1]},
            "action": {"S": record["eventName"]},
        }
        if "OldImage" in data:
            item["old_image"] = {"M": data["OldImage"]}
        if "NewImage" in data:
            item["new_image"] = {"M": data["NewImage"]}
        client.put_item(TableName=AUDIT_TABLE, Item=item)
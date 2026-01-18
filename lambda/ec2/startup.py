import boto3
import json
import os
import urllib3

http = urllib3.PoolManager()

def send_slack_notification(message):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    payload = {"text": message}
    http.request(
        "POST",
        webhook_url,
        body=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )

def lambda_handler(event, context):
    ec2_client = boto3.client("ec2")
    regions = [r["RegionName"] for r in ec2_client.describe_regions()["Regions"]]
    
    total_started = {}
    
    for region in regions:
        ec2 = boto3.client("ec2", region_name=region)
        instances = ec2.describe_instances(
            Filters=[
                {"Name": "tag:AutoShutdown", "Values": ["true"]},
                {"Name": "instance-state-name", "Values": ["stopped"]}
            ]
        )
        ids = [
            i["InstanceId"]
            for r in instances["Reservations"]
            for i in r["Instances"]
        ]
        if ids:
            ec2.start_instances(InstanceIds=ids)
            total_started[region] = ids
            
    if total_started:
        summary = "\n".join([f"- {reg}: {', '.join(ids)}" for reg, ids in total_started.items()])
        send_slack_notification(f"☀️ *Auto-Resume (EC2)*: Started instances in the following regions:\n{summary}")
            
    return {"started_ec2": total_started}

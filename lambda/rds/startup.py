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
    ec2 = boto3.client("ec2")
    regions = [r["RegionName"] for r in ec2.describe_regions()["Regions"]]
    
    total_started = {}
    
    for region in regions:
        rds = boto3.client("rds", region_name=region)
        dbs = rds.describe_db_instances()["DBInstances"]
        started = []
        for db in dbs:
            tags = rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])["TagList"]
            if any(t["Key"] == "AutoShutdown" and t["Value"] == "true" for t in tags):
                if db["DBInstanceStatus"] == "stopped":
                    rds.start_db_instance(DBInstanceIdentifier=db["DBInstanceIdentifier"])
                    started.append(db["DBInstanceIdentifier"])
        if started:
            total_started[region] = started
            
    if total_started:
        summary = "\n".join([f"- {reg}: {', '.join(ids)}" for reg, ids in total_started.items()])
        send_slack_notification(f"☀️ *Auto-Resume (RDS)*: Started databases in the following regions:\n{summary}")
            
    return {"started_rds": total_started}

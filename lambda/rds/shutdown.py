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
    
    total_stopped = {}
    total_savings = 0.0
    
    # Simple hourly price mapping (on-demand estimation)
    PRICE_MAP = {
        "db.t3.micro": 0.017, "db.t3.small": 0.034, "db.t3.medium": 0.068,
        "db.m5.large": 0.171
    }
    
    for region in regions:
        rds = boto3.client("rds", region_name=region)
        dbs = rds.describe_db_instances()["DBInstances"]
        stopped = []
        for db in dbs:
            tags = rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])["TagList"]
            if any(t["Key"] == "AutoShutdown" and t["Value"] == "true" for t in tags):
                if db["DBInstanceStatus"] == "available":
                    rds.stop_db_instance(DBInstanceIdentifier=db["DBInstanceIdentifier"])
                    stopped.append(db["DBInstanceIdentifier"])
                    total_savings += PRICE_MAP.get(db["DBInstanceClass"], 0.1) # Default to $0.10/hr
        if stopped:
            total_stopped[region] = stopped
            
    if total_stopped:
        daily_savings = total_savings * 12 # Assume 12 hours off per night
        summary = "\n".join([f"- {reg}: {', '.join(ids)}" for reg, ids in total_stopped.items()])
        msg = (f"⏰ *Auto-Shutdown (RDS)*: Stopped {sum(len(v) for v in total_stopped.values())} databases.\n"
               f"💰 *Est. Savings*: ${daily_savings:.2f}/day (based on 12h off)\n"
               f"{summary}")
        send_slack_notification(msg)
            
    return {"stopped_rds": total_stopped, "savings": total_savings}
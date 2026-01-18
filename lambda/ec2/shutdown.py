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
    
    total_stopped = {}
    total_savings = 0.0
    
    # Simple hourly price mapping (on-demand estimation)
    PRICE_MAP = {
        "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208,
        "t3.medium": 0.0416, "t2.micro": 0.0116, "m5.large": 0.096
    }
    
    for region in regions:
        ec2 = boto3.client("ec2", region_name=region)
        instances = ec2.describe_instances(
            Filters=[
                {"Name": "tag:AutoShutdown", "Values": ["true"]},
                {"Name": "instance-state-name", "Values": ["running"]}
            ]
        )
        for r in instances["Reservations"]:
            for i in r["Instances"]:
                iid = i["InstanceId"]
                itype = i["InstanceType"]
                ec2.stop_instances(InstanceIds=[iid])
                
                if region not in total_stopped:
                    total_stopped[region] = []
                total_stopped[region].append(iid)
                total_savings += PRICE_MAP.get(itype, 0.05) # Default to $0.05/hr
            
    if total_stopped:
        daily_savings = total_savings * 12 # Assume 12 hours off per night
        summary = "\n".join([f"- {reg}: {', '.join(ids)}" for reg, ids in total_stopped.items()])
        msg = (f"⏰ *Auto-Shutdown (EC2)*: Stopped {sum(len(v) for v in total_stopped.values())} instances.\n"
               f"💰 *Est. Savings*: ${daily_savings:.2f}/day (based on 12h off)\n"
               f"{summary}")
        send_slack_notification(msg)
            
    return {"stopped_ec2": total_stopped, "savings": total_savings}
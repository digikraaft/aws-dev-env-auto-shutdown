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
    ec2_regions = boto3.client("ec2").describe_regions()["Regions"]
    regions = [r["RegionName"] for r in ec2_regions]
    
    total_started = []
    
    for region in regions:
        ecs = boto3.client("ecs", region_name=region)
        clusters = ecs.list_clusters()["clusterArns"]
        
        for cluster in clusters:
            services = ecs.list_services(cluster=cluster)["serviceArns"]
            if not services:
                continue
                
            for service in services:
                tags = ecs.list_tags_for_resource(resourceArn=service)["tags"]
                if any(t["key"] == "AutoShutdown" and t["value"] == "true" for t in tags):
                    # For ECS resume, we set desiredCount to 1 as a baseline
                    # More advanced logic could store the previous desiredCount in a DynamoDB table
                    ecs.update_service(cluster=cluster, service=service, desiredCount=1)
                    total_started.append(f"{region}:{service}")
                    
    if total_started:
        summary = "\n".join([f"- {s}" for s in total_started])
        send_slack_notification(f"☀️ *Auto-Resume (ECS)*: Started services (Desired Count: 1):\n{summary}")
                    
    return {"started_ecs_services": total_started}

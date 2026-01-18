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
    
    total_stopped = []
    total_savings = 0.0
    
    # Fargate vCPU hourly price mapping (estimation)
    PRICE_PER_VCPU = 0.04
    
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
                    # Fetch task definition to estimate cost
                    svc_desc = ecs.describe_services(cluster=cluster, services=[service])["services"][0]
                    desired = svc_desc["desiredCount"]
                    if desired > 0:
                        ecs.update_service(cluster=cluster, service=service, desiredCount=0)
                        total_stopped.append(f"{region}:{service}")
                        # Typical Fargate service uses 0.25 vCPU as default if we can't fetch it easily
                        total_savings += (desired * 0.25 * PRICE_PER_VCPU)
                    
    if total_stopped:
        daily_savings = total_savings * 12 # Assume 12 hours off per night
        summary = "\n".join([f"- {s}" for s in total_stopped])
        msg = (f"⏰ *Auto-Shutdown (ECS)*: Stopped {len(total_stopped)} services.\n"
               f"💰 *Est. Savings*: ${daily_savings:.2f}/day (based on 12h off)\n"
               f"{summary}")
        send_slack_notification(msg)
                    
    return {"stopped_ecs_services": total_stopped, "savings": total_savings}
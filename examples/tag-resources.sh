#!/bin/bash

# 🏷️ AWS Resource Tagger for Auto-Shutdown
# This script tags EC2, RDS, and ECS resources with AutoShutdown=true

REGION=${1:-"us-east-1"}

echo "🚀 Tagging resources in $REGION..."

# 1. Tag EC2 Instances (that are not already tagged)
echo "🔹 Tagging EC2 instances..."
INSTANCE_IDS=$(aws ec2 describe_instances --region $REGION --query 'Reservations[].Instances[].InstanceId' --output text)
if [ ! -z "$INSTANCE_IDS" ]; then
    aws ec2 create-tags --region $REGION --resources $INSTANCE_IDS --tags Key=AutoShutdown,Value=true
    echo "✅ Tagged instances: $INSTANCE_IDS"
else
    echo "ℹ️ No EC2 instances found."
fi

# 2. Tag RDS Instances
echo "🔹 Tagging RDS instances..."
RDS_ARNS=$(aws rds describe_db_instances --region $REGION --query 'DBInstances[].DBInstanceArn' --output text)
for arn in $RDS_ARNS; do
    aws rds add-tags-to-resource --region $REGION --resource-name $arn --tags Key=AutoShutdown,Value=true
    echo "✅ Tagged RDS: $arn"
done

# 3. Tag ECS Services (requires cluster name)
echo "🔹 Tagging ECS services..."
CLUSTERS=$(aws ecs list_clusters --region $REGION --query 'clusterArns' --output text)
for cluster in $CLUSTERS; do
    SERVICES=$(aws ecs list_services --region $REGION --cluster $cluster --query 'serviceArns' --output text)
    for service in $SERVICES; do
        aws ecs tag-resource --region $REGION --resource-arn $service --tags key=AutoShutdown,value=true
        echo "✅ Tagged ECS service: $service"
    done
done

echo "🎉 Done!"

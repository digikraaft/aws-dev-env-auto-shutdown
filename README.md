# ⏰ Dev Environment Auto Shutdown (AWS)

**Automatically stop non-production AWS resources to eliminate wasted cloud spend.**

This repository provides **tag-based, schedule-driven shutdown automation**
for dev and test environments across common AWS services.

## ✨ Key Features
- **Multi-Region Support**: Automatically scans all AWS regions in your account.
- **Tag-Driven**: Only stops resources with `AutoShutdown=true`.
- **Auto-Resume**: Automatically starts resources back up in the morning (8 AM).
- **Slack Notifications**: Sends a summary of shutdown/startup actions to a Slack channel.
- **Service Wide**: Supports EC2, RDS, and ECS (Services).
- **Cost Effective**: Runs as Lambda functions with EventBridge triggers.

## 🚀 Getting Started

### 1. Deploy the Infrastructure
Check out the [Terraform example](/examples/terraform-deploy/main.tf) to deploy the Lambda functions and CloudWatch rules. 
> [!TIP]
> Provide a `slack_webhook_url` variable to enable notifications.


### 2. Tag Your Resources
Resources must be tagged with `AutoShutdown=true` to be included in the shutdown cycle.
You can use the [tagging helper script](/examples/tag-resources.sh):
```bash
./examples/tag-resources.sh us-east-1
```

## 🛠️ How It Works
1. **Scans All Regions**: The Lambda functions fetch all available regions.
2. **Filters by Tag**: Looks for instances/services with `AutoShutdown=true`.
3. **Graceful Shutdown**: Stops EC2/RDS instances and sets ECS desired count to 0.

## 📂 Examples
- [Terraform Deployment](/examples/terraform-deploy/): Deploy the entire stack.
- [Tagging Script](/examples/tag-resources.sh): Quick way to onboard existing resources.

## 🤝 Philosophy
> If it’s not production, it shouldn’t run forever.
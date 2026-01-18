# How Auto Shutdown Works

1. EventBridge triggers Lambda on schedule
2. Lambda scans for tagged resources
3. Matching resources are stopped
4. Logs recorded in CloudWatch
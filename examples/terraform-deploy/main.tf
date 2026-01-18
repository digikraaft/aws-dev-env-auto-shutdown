variable "slack_webhook_url" {
  description = "Slack Webhook URL for notifications"
  type        = string
  default     = "" # Optional
}

resource "aws_iam_role" "lambda_role" {
  name = "dev_auto_shutdown_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws_iam:aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "shutdown_policy" {
  name        = "DevAutoShutdownPolicy"
  description = "Policy for shutting down and starting EC2, RDS, and ECS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:DescribeRegions",
          "rds:DescribeDBInstances",
          "rds:StopDBInstance",
          "rds:StartDBInstance",
          "rds:ListTagsForResource",
          "ecs:ListClusters",
          "ecs:ListServices",
          "ecs:UpdateService",
          "ecs:ListTagsForResource"
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "shutdown_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.shutdown_policy.arn
}

# Archive for Shutdown
data "archive_file" "shutdown_zip" {
  for_each    = toset(["ec2", "rds", "ecs"])
  type        = "zip"
  source_file = "${path.module}/../../lambda/${each.value}/shutdown.py"
  output_path = "${path.module}/shutdown_${each.value}.zip"
}

# Archive for Startup
data "archive_file" "startup_zip" {
  for_each    = toset(["ec2", "rds", "ecs"])
  type        = "zip"
  source_file = "${path.module}/../../lambda/${each.value}/startup.py"
  output_path = "${path.module}/startup_${each.value}.zip"
}

resource "aws_lambda_function" "shutdown_lambda" {
  for_each      = toset(["ec2", "rds", "ecs"])
  filename      = data.archive_file.shutdown_zip[each.value].output_path
  function_name = "dev_auto_shutdown_${each.value}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "shutdown.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  source_code_hash = data.archive_file.shutdown_zip[each.value].output_base64sha256
}

resource "aws_lambda_function" "startup_lambda" {
  for_each      = toset(["ec2", "rds", "ecs"])
  filename      = data.archive_file.startup_zip[each.value].output_path
  function_name = "dev_auto_resume_${each.value}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "startup.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  source_code_hash = data.archive_file.startup_zip[each.value].output_base64sha256
}

# EventBridge Rules
resource "aws_cloudwatch_event_rule" "nightly_shutdown" {
  name                = "dev_nightly_shutdown"
  description         = "Shut down dev resources at 8 PM"
  schedule_expression = "cron(0 20 * * ? *)"
}

resource "aws_cloudwatch_event_rule" "morning_startup" {
  name                = "dev_morning_startup"
  description         = "Start dev resources at 8 AM"
  schedule_expression = "cron(0 8 ? * MON-FRI *)"
}

# Targets for Shutdown
resource "aws_cloudwatch_event_target" "shutdown_target" {
  for_each  = aws_lambda_function.shutdown_lambda
  rule      = aws_cloudwatch_event_rule.nightly_shutdown.name
  target_id = "Shutdown${each.key}"
  arn       = each.value.arn
}

# Targets for Startup
resource "aws_cloudwatch_event_target" "startup_target" {
  for_each  = aws_lambda_function.startup_lambda
  rule      = aws_cloudwatch_event_rule.morning_startup.name
  target_id = "Startup${each.key}"
  arn       = each.value.arn
}

# Permissions
resource "aws_lambda_permission" "allow_shutdown" {
  for_each      = aws_lambda_function.shutdown_lambda
  statement_id  = "AllowShutdownFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nightly_shutdown.arn
}

resource "aws_lambda_permission" "allow_startup" {
  for_each      = aws_lambda_function.startup_lambda
  statement_id  = "AllowStartupFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.morning_startup.arn
}


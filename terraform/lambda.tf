data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_policy" "lambda_logging" {
  name        = "lambda_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy      = data.aws_iam_policy_document.lambda_logging.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_role" "iam_for_lambda" {
  name               = "iam_for_lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda_function.py"
  output_path = "lambda_function_payload.zip"
}

resource "aws_lambda_function" "guardian_api_lambda" {
  filename         = "lambda_function_payload.zip"
  function_name    = var.lambda_name
  role             = aws_iam_role.iam_for_lambda.arn
  handler          = "lambda_function.lambda_handler"
  layers           = [aws_lambda_layer_version.lambda_layer.arn]
  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime = "python3.12"

  environment {
    variables = {
      api_key       = var.guardian_api_key
      sqs_queue_url = aws_sqs_queue.retrieved_guardian_articles.url
    }
  }
  depends_on = [aws_sqs_queue.retrieved_guardian_articles]
}

output "lambda_function_arn" {
  description = "ARN of Guardian API Lambda"
  value       = try(aws_lambda_function.guardian_api_lambda.arn)
  sensitive   = true
}

resource "aws_lambda_layer_version" "lambda_layer" {
  filename   = "${path.module}/../layer.zip"
  layer_name = "lambda_layer_name"

  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("${path.module}/../layer.zip")
}
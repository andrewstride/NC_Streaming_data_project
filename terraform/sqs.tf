resource "aws_sqs_queue" "retrieved_guardian_articles" {
  name                        = "${var.sqs_queue_name}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  message_retention_seconds = 259200
}

data "aws_iam_policy_document" "sqs_policy_doc" {
  statement {
    sid = "__sender_statement"
    effect = "Allow"

    principals {
      type = "*"
      identifiers = ["*"]
    }

    actions = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.retrieved_guardian_articles.arn]

    condition {
      test = "ArnEquals"
      variable = "aws:SourceArn"
      values = [aws_lambda_function.guardian_api_lambda.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "sqs_policy" {
  queue_url = aws_sqs_queue.retrieved_guardian_articles.id
  policy = data.aws_iam_policy_document.sqs_policy_doc.json
}
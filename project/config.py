import os

class Config():

  app_name = os.environ.get('APP_NAME')
  app_version = os.environ.get('APP_VERSION')
  app_dist = os.environ.get('APP_DIST')

  vpc_id = os.environ.get('APP_VPC_ID')
  subnet_id = os.environ.get('APP_SUBNET_ID')
  sec_group_id = os.environ.get('APP_SEC_GROUP')

  region_name = os.environ.get('APP_AWS_REGION','eu-west-1')

  # SQS
  queue_name = os.environ.get('APP_SQS_QUEUE_NAME','LAMBDA_DEPLOY')
  sqs_url = os.environ.get("APP_SQS_URL")
  sqs_queue_arn = os.environ.get("APP_SQS_ARN")

  # REDIS
  redis = os.environ.get('APP_REDIS')
  redis_port = os.environ.get('APP_REDIS_PORT')
  
  # Lambda function
  lambda_default_role = os.environ.get('APP_LAMBDA_DEFAULT_ROLE_EXECUTION')

  lambda_deploy = os.environ.get('APP_LAMBDA_DEPLOY_NAME')
  lambda_deploy_handler = os.environ.get('APP_LAMBDA_DEPLOY_HANDLE')

  # AWS KEY
  aws_key = os.environ.get('APP_AWS_KEY', '1234')
  aws_secret = os.environ.get('APP_AWS_SECRET', '123456789')

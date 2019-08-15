import sys
import os
import json
import argparse
import boto3
import uuid
import base64
from .config import Config
import redis
from tabulate import tabulate
import time
from .constants import TASK_CREATED
from .constants import TASK_END

class AppDeploy:
    """
    Main app class deploy a multi container ECS with cluster containter name
    and image and tag
    """

    def __init__(self, argv):
        # parse arguments --interactive and resource file
        self.argv = argv
        self.parse_args()
        return None

    def run(self):
        try:
            # pack_lambda
            self.pack_lambda()

            # pre-requisit is lambda function packed first
            self.check_if_lambda_packed()
            
            # read resource file json into python dict
            self.parse_json()

            # --------------------------------------
            # WE ARE READY TO GO - pre-requisits ok
            # 1.-Args ok
            # 2.-Lambda is packed with script as a pre-requisit
            # 3.-Json structure from resource is ok
            # --------------------------------------
            # NEXT STEPS
            # 1.-Connect to aws services
            # 2.-Deploy new lambda versison to aws
            # 3.-Send one message task to SQS for each row in resources.json
            # 4.-Lisen and wait for all task unitl all task done

            # conect to aws services first (sqs and redis)
            self.init_aws_services()

            # if lambda is packed then we can deploy this current version
            self.deploy_lambda_first()

            # program ends when all message are processed
            # we send one message for each cluster to deploy
            self.all_message_send_key = []

            # self.data have all cluster specs with cluster id and image:tag
            for data in self.data:
                # send message and save key for check in redis
                self.all_message_send_key.append(self.launch_cluster_deploy(data))

            # Wait for all task done and print screen with status
            count = 0
            while not self.all_task_done():
                if self.interactive:
                    # if interactive mode we can see a table with progress
                    # for each cluster deploy each 100 ms
                    os.system('clear')
                    print("SHOW ALL TASK STATUS", count, "seconds form start")
                    count+=1
                    show_table = []
                    for task in self.all_message_send_key:
                        task_status = self.redis.get(task["task_id"])
                        task_result = self.redis.get("{}-{}".format(task["task_id"],'result'))

                        row = [task['task_data']['cluster'],
                               task['task_data']['service'],
                               task['task_data']['container'],
                               task['task_data']['image'],
                               task['task_data']['tag'],
                               task_status,
                               task_result]
                        show_table.append(row)

                    print(tabulate(show_table, 
                                   headers=['Cluster',
                                            'Service',
                                            'Container',
                                            'Image',
                                            'Tag',
                                            'Status',
                                            'result']))
                    time.sleep(1)

            self.send_stats_message('OK')
        except Exception as e:
            print(e)
            self.send_stats_message(e)

    def deploy_lambda_first(self):
        # delete lambda function if exist and source mapping if any
        try:
            print("Remove actual mappings")
            response = self._lambda.list_event_source_mappings(
                                    EventSourceArn=Config.sqs_queue_arn,
                                    FunctionName=Config.lambda_deploy
                    )

            for event in response['EventSourceMappings']:
                resp = self._lambda.delete_event_source_mapping(
                                    UUID=event['UUID']
                    )
        except Exception as e:
            print("error removing mapping", e)
            pass

        try:
            print("Removing old version function")
            response = self._lambda.delete_function(
                FunctionName=Config.lambda_deploy
            )

        except Exception as e:
            print("error reomving", e)
            pass

        # create lambda function
        print("Deploying new lambda")
        app_enviroment = {k: v for k, v in dict(os.environ).items() if k.startswith('APP_')}
        self._lambda.create_function(
                FunctionName=Config.lambda_deploy,
                Handler=Config.lambda_deploy_handler,
                Timeout=30,
                Runtime='python3.7',
                Role=Config.lambda_default_role,
                MemorySize=512,
                Code={"ZipFile":self.zip_to_base64(Config.app_dist)},
                Environment=json.loads(('{"Variables":'+json.dumps(app_enviroment)+'}')),
                Publish=True,
                VpcConfig={
                  'SubnetIds': [
                     Config.subnet_id,
                  ],
                  'SecurityGroupIds': [
                     Config.sec_group_id,
                  ]
                }
                )

        # connect to sqs source events
        print("Mapping SQS queue to lambda function")
        self._lambda.create_event_source_mapping(
                EventSourceArn=Config.sqs_queue_arn,
                FunctionName=Config.lambda_deploy,
                Enabled=True,
                BatchSize=1
                )

        return True

    def launch_cluster_deploy(self, data):
        rediskey = str(uuid.uuid4())
        data["task_id"] = rediskey
        response = self.sqs.send_message(
                    QueueUrl="{}{}".format(Config.sqs_url,Config.queue_name),
                    MessageBody=json.dumps(data))

        self.redis.set(rediskey, TASK_CREATED)
        self.redis.expire(rediskey, 60*60*24)
        # return redis key to get update status and responses"
        return {'task_id':rediskey, 'task_data': data}

    def all_task_done(self):
        for task in self.all_message_send_key:
            if self.redis.get(task["task_id"]) != TASK_END:
                return False
        # all task end
        return True


    def parse_json(self):

        with open(self.file_specs) as json_file:
          self.data = json.load(json_file)

        return self.data

    def pack_lambda(self):
        print("Packing lambda librarys and dependencies")
        os.system('./pack_lambda > /dev/null')
        pass

    def check_if_lambda_packed(self):

        if not os.path.exists(Config.app_dist):
            raise RuntimeError('Please pack lamda function first follow README.md instrucctions')

        return True

    def zip_to_base64(self, zip_file):
        # return 'file:package/project.zip'
        data = open(zip_file, "rb").read()
        return data

    def parse_args(self):

        self.interactive = False
        self.file_specs = "resources/default.json"
        parser = argparse.ArgumentParser(description='Deploy multi container ECS with lambda.')

        parser.add_argument('-i', '--interactive', action='store_true',
                     help='interactive mode (default: False)')

        parser.add_argument('--file_specs', dest='resource', default = self.file_specs,
                     help='Json file with all cluster to deploy (default: resource/default.json)')

        args = parser.parse_args()
        if args.interactive == True:
            self.interactive = True

        if args.resource:
            self.file_specs = args.resource

        return self.file_specs, self.interactive

    def init_aws_services(self):
        """
        init sqs and redis services
        TODO we can create the queue if not exist and create ElastiCache
        if not exist
        for now a conection is ok
        """
        self.sqs = boto3.client('sqs',
                                region_name=Config.region_name,
                                aws_access_key_id=Config.aws_key,
                                aws_secret_access_key=Config.aws_secret
        )
        self._lambda = boto3.client('lambda',
                                    region_name=Config.region_name,
                                    aws_access_key_id=Config.aws_key,
                                    aws_secret_access_key=Config.aws_secret
        )
        self.redis = redis.Redis(host=Config.redis, port=Config.redis_port)
        pass


    def send_stats_message(self, message):
        """
        Send message to a defined list of manager etc..

        """
        # TODO implement

        pass

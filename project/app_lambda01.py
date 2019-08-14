import json
import redis
import boto3
from .config import Config
from .constants import TASK_CREATED
from .constants import TASK_END
from .constants import TASK_RECIVED_LAMBDA
from .constants import TASK_RETRIVING_TASKDEF_NAME
from .constants import TASK_RETRIVING_TASKDEF_DESC

def lambda_function_01(event, context):

    my_redis = redis.Redis(host=Config.redis, port=Config.redis_port)
    new_deploy_data = []
    try:
        new_deploy_data = json.loads(event['Records'][0]['body'])
        sqs = boto3.client('sqs',
                            region_name=Config.region_name,
                            aws_access_key_id=Config.aws_key,
                            aws_secret_access_key=Config.aws_secret
        )
        # update task status to start
        task_id = new_deploy_data['task_id']
        new_image = "{}:{}".format(new_deploy_data['image'], new_deploy_data['tag'])
        current_cluster = new_deploy_data['cluster']
        current_service = new_deploy_data['service']
        current_container = new_deploy_data['container']

        my_redis.set(task_id, TASK_RECIVED_LAMBDA)

        newkey = "{}-{}".format(task_id,'result')
        my_redis.set(newkey,'Start processing...')
        my_redis.expire(newkey, 60*60*24)
       
        ecs = boto3.client('ecs',
                            region_name=Config.region_name,
                            aws_access_key_id=Config.aws_key,
                            aws_secret_access_key=Config.aws_secret
                )

        # 1.- retrive task definition name for current_cluster and current_service
        my_redis.set(task_id, TASK_RETRIVING_TASKDEF_NAME)
        my_redis.set(newkey,'Retriving task definition name')

        response = ecs.describe_services(
            cluster=current_cluster,
            services=[
                current_service,
            ],
        )

        print("describe_services-->", response)

        current_task_definition = response['services'][0]['taskDefinition']

        # 2.- retriving task definition description 
        my_redis.set(task_id, TASK_RETRIVING_TASKDEF_DESC)
        my_redis.set(newkey,'Retriving task definition description')

        response = ecs.describe_task_definition(
            taskDefinition=current_task_definition,
            include=[
                'TAGS',
            ]
        )

        print("describe_task_def", response)

        # 3.- define a new task definition based on actual
        my_redis.set(task_id, TASK_DEFINING_TASKDEF)
        my_redis.set(newkey,'Defining new task definition')
        newtask_def = response['taskDefinition']
        for idx, container in enumerate(newtask_def['containerDefinitions']):
            if container['name'] == current_container:
                newtask_def['containerDefinitions'][idx] = new_image
                newtask_def['containerDefinitions'][idx].remove('taskDefinitionArn')

        revision = int(newtask_def['revision'])+1
        newtask_def.pop('revision')
        # newtask_def.pop('status')
        # newtask_def.pop('requiresAttributes')
        # newtask_def.pop('compatibilities')

        # 4.- register e a new task definition
        my_redis.set(task_id, TASK_REGISTER_NEW_TASKDEF)
        my_redis.set(newkey,'Registering new task definition')
        list_containers = []
        if isinstance(newtask_def['containerDefinitions'], dict):
            for container in newtask_def['containerDefinitions']:
                list_cotainers.append(container)
        else:
            list_containers = newtask_def['containerDefinitions']
        
        # extract family from arn
        family = current_task_definition.split(':')[len(current_task_definition.split(':'))-2].split('/')[-1]

        response = ecs.register_task_definition(
                family=family,
                containerDefinitions=list_containers 
                )
        print("TASK DEFINITION", response)
        
        # 5.- Finally update service with new image
        my_redis.set(task_id, TASK_UPDATE_SERVICE)
        my_redis.set(newkey,'Registering new task definition')
        
        response = ecs.update_service(
                cluster=cluster,
                service=service,
                taskDefinition="{}:{}".format(family,str(revision))
                )
        print("UPDATE SERIVCE", response)
        my_redis.set(task_id, TASK_END)
        my_redis.set(newkey,'Finished OK')

        return json.dumps({'result':'OK'})
    except Exception as e:
        my_redis.set(new_deploy_data['task_id'], TASK_END)
        newkey = "{}-{}".format(new_deploy_data['task_id'],'result')
        my_redis.set(newkey,'Error-'+str(e))
        my_redis.expire(newkey, 60*60*24)
        print("Error-", e)
        return json.dumps({'result':'ERROR'})

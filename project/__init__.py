from .app_lambda01 import lambda_function_01

def handle_01(event, context):
    return lambda_function_01(event, context)

# in the same project we can have multiple handles
# means in one project we can manage multiple lambdas
# we can improve the script to dynamicaly deploy a desired lambdas...

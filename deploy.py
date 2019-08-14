import json
import os
import sys
import getopt
from project.app_deploy import AppDeploy

if __name__ == "__main__":
    app = AppDeploy(sys.argv[1:])
    app.run()

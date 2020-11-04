import socket
import asyncio
import time
import random
import json

from walkoff_app_sdk.app_base import AppBase

class PythonPlayground(AppBase):
    __version__ = "1.0.0"
    app_name = "python_playground"  # this needs to match "name" in api.yaml

    def __init__(self, redis, logger, console_logger=None):
        """
        Each app should have this __init__ to set up Redis and logging.
        :param redis:
        :param logger:
        :param console_logger:
        """
        super().__init__(redis, logger, console_logger)

    async def List_all_subnet(self,url,username,password,app,api):
        print("1")
        import sys
        print("2")
        import warnings
        print("3")
        if not sys.warnoptions:
            warnings.simplefilter("ignore")

        from phpipam_client import PhpIpamClient

        ipam = PhpIpamClient(
            ssl_verify=False,
            url=url,
            app_id=app,
            username=username,
            password=password,
            token=api,
            user_agent='Splunk_lookup',
        )

        subnet = ipam.get('/subnets/')
        info=[]
        for line in subnet:

            if (isinstance(line['location'], list) or not line['location']):
                location = 'N/A'
            else:
                location = line['location']["name"]

            info.append([line['subnet'],str(line['mask']),str(line['vlanId']),str(line['description']),str(location)])
        return info
    # Write your data inside this function
    async def run_python_script(self, json_data, function_to_execute):
        # It comes in as a string, so needs to be set to JSON
        try:
            json_data = json.loads(json_data)
        except json.decoder.JSONDecodeError as e:
            return "Couldn't decode json: %s" % e

        # These are functions
        switcher = {
            "function_1" : self.run_me_1,
            "function_2" : self.run_me_2,
            "function_3" : self.run_me_3,
        }

        func = switcher.get(function_to_execute, lambda: "Invalid function")
        return func(json_data)

if __name__ == "__main__":
    asyncio.run(PythonPlayground.run(), debug=True)

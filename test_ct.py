import asyncio
from dotenv import load_dotenv
import os
from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.endpoints import EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *

load_dotenv()
app_id = os.getenv("CT_APP_ID")
app_secret = os.getenv("CT_APP_SECRET")

async def main():
    print(f"App ID: {app_id}")
    client = Client(EndPoints.DATACENTER_1.HOST, EndPoints.DATACENTER_1.PORT, TcpProtocol)
    await client.connect()
    
    # Send App Auth Request
    request = ProtoOAApplicationAuthReq()
    request.clientId = app_id
    request.clientSecret = app_secret
    
    try:
        response = await client.send(request)
        print("Application Auth Response:", response)
    except Exception as e:
        print("Error:", e)
    
    client.disconnect()

asyncio.run(main())

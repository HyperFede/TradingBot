import asyncio
import os
from dotenv import load_dotenv

from ctrader_open_api import Client, Protobuf, TcpProtocol
from ctrader_open_api.endpoints import EndPoints
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

load_dotenv()
app_id = os.getenv("CT_APP_ID")
app_secret = os.getenv("CT_APP_SECRET")
token = os.getenv("CT_ACCESS_TOKEN")
account_id = int(os.getenv("CT_ACCOUNT_ID", 0))

async def main():
    client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)
    
    def on_message(client, message):
        print("Received message payload type:", message)
        
    # client.set_message_received_callback(on_message) # Maybe not supported like this

    client.start()
    await asyncio.sleep(1) # wait for connection
    print("Sending APP Auth")
    req = ProtoOAApplicationAuthReq()
    req.clientId = app_id
    req.clientSecret = app_secret
    
    try:
        res = await client.send(req)
        print("Auth Response:", type(res))
    except Exception as e:
        print("Error:", e)
        
    client.stop()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

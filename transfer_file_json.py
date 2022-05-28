import os
import json
import base64

with open("./dummy.png", mode='rb') as f:
    file2send = f.read()
    text = str(base64.b64encode(file2send),encoding='utf-8')
    print(type(text))

send_message = json.dumps({
    'text': text
})
received_message = json.loads(send_message)

with open("./output.png", mode='wb') as f:
    byte_data=base64.b64decode(received_message['text'])
    f.write(byte_data)
# base64.b64decode(text)

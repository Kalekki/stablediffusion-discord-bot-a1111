import base64
import configparser
import io
import discord
import requests
from PIL import Image

## TODO:
# - img2img
#    Expose more options through the config file
# - Swapping models
# - implement slash commands to enable multiple options, like size, seed etc.

config = configparser.ConfigParser()
config.read('configuration.ini')
token = config['Bot-settings']['bot_token']
txt2img_command = config['Bot-settings']['bot_prefix']+config['Bot-settings']['txt2img_command']

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print('------')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(txt2img_command):
        #check if message has embedded image
        if len(message.attachments) > 0:
            # Img2img
            prompt = message.content.replace(txt2img_command, '')
            img = Image.open(requests.get(message.attachments[0].url, stream=True).raw)
            print(f"{message.author} used img2img with prompt: {prompt}")

            async with message.channel.typing():
                filename = img2img(img, prompt)
                await message.channel.send(message.author.mention,file=discord.File(f'images/{filename}.png'))
        else:
            # Text2img
            prompt = message.content.replace(txt2img_command, '')
            print(f"{message.author} used txt2img with prompt: {prompt}")
           
            async with message.channel.typing():
                filename = text2img(prompt)
                await message.channel.send(message.author.mention,file=discord.File(f'images/{filename}.png'))


def response_to_image(response, prompt):
    for i in response['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
        if len(prompt) > 40:
            prompt = prompt[:40]
        filename = ''.join(e for e in prompt if e.isalnum())
        if filename == '':
            filename = 'image'
        image.save(f'images/{filename}.png')
        print(f'images/{filename}.png saved')
        # save the response for debugging
        response.pop('images', None)
        response.pop('init_images', None)
        with open('response.json', 'w') as f:
            f.write(str(response))
            f.close()
        return filename

def text2img(prompt):
    req = {
        "prompt": config['SD-settings']['positive_prompt']+prompt,
        "steps": config['SD-settings']['steps'],
        "sampler": config['SD-settings']['sampler'],
        "sampler_index": config['SD-settings']['sampler'],
        "negative_prompt": config['SD-settings']['negative_prompt'],
        "cfg_scale": config['SD-settings']['cfg_scale']
    }
    response = requests.post(url=f'http://{config["SD-settings"]["address"]}/sdapi/v1/txt2img', json=req)
    filename = response_to_image(response.json(), prompt)
    return filename
                        
def img2img(img, prompt):
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
    url = f'http://{config["SD-settings"]["address"]}/sdapi/v1/img2img'
    req = {
        "init_images": ["data:image/png;base64," + img_base64],
        "prompt": prompt,
        "negative_prompt": config['SD-settings']['negative_prompt'],
        "steps": config['SD-settings']['steps'],
        "include_init_images": False,
        "sampler": config['SD-settings']['sampler'],
        "sampler_index": config['SD-settings']['sampler']
    }
    response = requests.post(url, json=req)
    filename = response_to_image(response.json(), prompt)
    return filename

client.run(token)
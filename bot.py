import base64
import configparser
import io
import discord
import requests
from PIL import Image

## TODO:
# - img2img
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
    # Text2img
    if message.content.startswith(txt2img_command):
        command_len = len(txt2img_command)
        prompt = message.content[command_len:]
        print(f"{message.author} used txt2img with prompt: {prompt}")
        req = {
            "prompt": config['SD-settings']['positive_prompt']+prompt,
            "steps": config['SD-settings']['steps'],
            "sampler": config['SD-settings']['sampler'],
            "negative_prompt": config['SD-settings']['negative_prompt'],
            "cfg_scale": config['SD-settings']['cfg_scale']
        }
        async with message.channel.typing():
            response = requests.post(url=f'http://{config["SD-settings"]["address"]}/sdapi/v1/txt2img', json=req)
            r = response.json()
            if response.status_code != 200:
                print(r['error'])
                return

            for i in r['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
                if len(prompt) > 40:
                    prompt = prompt[:40]
                prompt = ''.join(e for e in prompt if e.isalnum())
                image.save(f'images/{prompt}.png')
                print(f'images/{prompt}.png saved')
                await message.channel.send(message.author.mention,file=discord.File(f'images/{prompt}.png'))

        r.pop('images', None)
        with open('response.json', 'w') as f:
            f.write(str(r))
            f.close()

client.run(token)
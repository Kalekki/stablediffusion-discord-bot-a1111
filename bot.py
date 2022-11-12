import base64
import configparser
import io
from typing import Optional

import discord
import requests
from discord import app_commands
from PIL import Image

# TODO:
# - Swapping models
# - Restore faces
# - Error handling
# - Maybe encode pnginfo into the image, adds a bit of overhead but would enable getting parameters from pic


config = configparser.ConfigParser()
config.read('configuration.ini')
botsettings = config['Bot-settings']
sdsettings = config['SD-settings']
token = botsettings['bot_token']

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Slash commands


@tree.command(name="txt2img", description="Generate image from given prompt")
async def text2img_command(interaction: discord.Interaction,
                           prompt: str,
                           steps: Optional[app_commands.Range[int, 10, 60]],
                           negative_prompt: Optional[str],
                           cfg_scale: Optional[app_commands.Range[float, 0.1, 30.0]],
                           width: Optional[app_commands.Range[int, 256, 1024]],
                           height: Optional[app_commands.Range[int, 256, 1024]],
                           seed: Optional[app_commands.Range[int, -1, 9999999999]],
                           ):
    await interaction.response.send_message("Generating...")
    filename = text2img(prompt, negative_prompt, steps,
                        cfg_scale, width, height, seed)
    await interaction.edit_original_response(content=f"{prompt}", attachments=[discord.File(f"images/{filename}.png")])


@tree.command(name="img2img", description="Generate image from given image")
async def image2image_command(interaction: discord.Interaction,
                              prompt: str,
                              image: discord.Attachment,
                              denoising_strength: Optional[app_commands.Range[float, 0.1, 1.0]],
                              cfg_scale: Optional[app_commands.Range[float, 0.1, 30.0]],
                              steps: Optional[app_commands.Range[int, 10, 60]],
                              seed: Optional[app_commands.Range[int, -1, 9999999999]],
                              ):
    await interaction.response.send_message("Generating...")
    img = Image.open(io.BytesIO(await image.read()))
    filename = img2img(img, prompt, denoising_strength, cfg_scale, steps, seed)
    await interaction.edit_original_response(content=f"{prompt}", attachments=[discord.File(f"images/{filename}.png")])


@client.event
async def on_ready():
    getSamplers()
    print('------')
    # getModels()
    # print('------')
    print('Logged in as')
    print(client.user.name)
    # Register commands manually, uncomment if you add/change commands or parameters
    await tree.sync()


def response_to_image(response, prompt):
    for i in response['images']:
        image = Image.open(io.BytesIO(base64.b64decode(i.split(",", 1)[0])))
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


def text2img(prompt, negative_prompt=None, steps=None, cfg_scale=None, width=None, height=None, seed=None):

    # Set default values if not provided
    steps = int(sdsettings['steps']) if steps is None else steps
    cfg_scale = float(sdsettings['cfg_scale']
                      ) if cfg_scale is None else cfg_scale
    negative_prompt = sdsettings['negative_prompt'] if negative_prompt is None else negative_prompt
    # Constrict width and height to powers of 64 otherwise SD gets angry
    width = (int(sdsettings['width']) // 64) * \
        64 if width is None else (width // 64) * 64
    height = (int(sdsettings['height']) // 64) * \
        64 if height is None else (height // 64) * 64
    seed = -1 if seed is None else seed

    req = {
        "prompt": sdsettings['positive_prompt']+prompt,
        "steps": steps,
        "sampler": sdsettings['sampler'],
        "negative_prompt": negative_prompt,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "seed": seed,
    }
    response = requests.post(
        url=f'http://{sdsettings["address"]}/sdapi/v1/txt2img', json=req)
    filename = response_to_image(response.json(), prompt)
    return filename


def img2img(img, prompt, denoising_strength=None, cfg_scale=None, steps=None, seed=None):
    # Set default values if not provided
    denoising_strength = float(
        sdsettings['denoising_strength']) if denoising_strength is None else denoising_strength
    cfg_scale = float(sdsettings['cfg_scale']
                      ) if cfg_scale is None else cfg_scale
    steps = int(sdsettings['steps']) if steps is None else steps
    seed = -1 if seed is None else seed

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
    url = f'http://{sdsettings["address"]}/sdapi/v1/img2img'
    req = {
        "init_images": ["data:image/png;base64," + img_base64],
        "prompt": prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "denoising_strength": denoising_strength,
        "seed": seed,
        "include_init_images": False,
        "sampler": sdsettings['sampler'],
    }
    response = requests.post(url, json=req)
    filename = response_to_image(response.json(), prompt)
    return filename


def getSamplers():
    url = f'http://{sdsettings["address"]}/sdapi/v1/samplers'
    response = requests.get(url)
    print("Available samplers:")
    for i in response.json():
        print(i['name'])


def getModels():
    url = f'http://{sdsettings["address"]}/sdapi/v1/sd-models'
    response = requests.get(url)
    print("Available models:")
    for i in response.json():
        print(i['model_name'])


client.run(token)

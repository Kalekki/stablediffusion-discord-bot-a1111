import base64
import configparser
import datetime
import io
from typing import Optional

import discord
import requests
from discord import app_commands
from discord.ui import Button, View
from PIL import Image, PngImagePlugin

# TODO:
# - Restrict buttons to the user who requested the pic
# - Restore faces
# - Have the view be a class for reuse with img2img
#       Remove the buttons after some time.
# - Error handling
# - Clean this shit up
#       Upscale is very hacky, ideally we'd want it to only affect the embed image while keeping the parameters


config = configparser.ConfigParser()
config.read('configuration.ini')
botsettings = config['Bot-settings']
sdsettings = config['SD-settings']
token = botsettings['bot_token']
max_size = int(sdsettings['max_size'])

# Discord stuff
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
                           width: Optional[app_commands.Range[int, 256, max_size]],
                           height: Optional[app_commands.Range[int, 256, max_size]],
                           seed: Optional[app_commands.Range[int, -1, 0xFFFFFFFF]],
                           high_resolution_fix: Optional[bool]
                           ):

    await interaction.response.send_message("Generating...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = text2img(prompt, negative_prompt, steps,
                        cfg_scale, width, height, seed, enable_hr=high_resolution_fix)
    time_took = round((datetime.datetime.now(
    ) - datetime.datetime.strptime(timestamp, "%Y%m%d-%H%M%S")).total_seconds(), 2)

    # Create discord embed out of the image
    view = View()
    view.timeout = 180
    embed = create_embed(filename, prompt, time_took)

    # Regenerate
    async def regenerate_callback(interaction: discord.Interaction):
        # modify original message with new image
        await interaction.response.defer()
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        text2img(prompt, negative_prompt, steps,
                 cfg_scale, width, height, seed, enable_hr=high_resolution_fix)
        time_took = round((datetime.datetime.now(
        ) - datetime.datetime.strptime(timestamp, "%Y%m%d-%H%M%S")).total_seconds(), 2)
        # Create discord embed out of the image
        embed = create_embed(filename, prompt, time_took)
        await interaction.message.edit(embed=embed, view=view, attachments=[discord.File(f'images/{filename}.png')])

    # Variant
    async def variant_callback(interaction: discord.Interaction):
        await interaction.response.defer()
        img_from_embed = interaction.message.embeds[0].image.url
        img_from_embed = img_from_embed.split('/')[-1]
        # Get generated image and its seed
        img = Image.open(f'images/{img_from_embed}')
        img_info = read_png_info(f'images/{img_from_embed}')
        seed = int(img_info['seed'])
        negative_prompt = img_info['negative_prompt']
        full_prompt = img_info['prompt']

        # Measure how long it took to generate the image
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = img2img(img, full_prompt, negative_prompt=negative_prompt,
                           denoising_strength=sdsettings['variant_denoising_strength'], seed=int(seed)+1)
        time_took = round((datetime.datetime.now(
        ) - datetime.datetime.strptime(timestamp, "%Y%m%d-%H%M%S")).total_seconds(), 2)

        # Create discord embed out of the image
        embed = create_embed(filename, prompt, time_took)
        await interaction.message.edit(embed=embed, view=view, attachments=[discord.File(f'images/{filename}.png')])

    # Upscale
    async def upscale_callback(interaction: discord.Interaction):
        await interaction.response.defer()
        # Get generated image and its seed
        img_from_embed = interaction.message.embeds[0].image.url
        img_from_embed = img_from_embed.split('/')[-1]
        img = Image.open(f'images/{img_from_embed}')

        upscaled_file = upscale(img, prompt)
        # Follow up with the upscaled image
        await interaction.followup.send("2x Upscaled image", ephemeral=True, files=[discord.File(f'images/{upscaled_file}.png')])

    # Buttons for the view
    regenerate_button = Button(label="Regenerate", style=discord.ButtonStyle.blurple)
    variant_button = Button(label="Variant", style=discord.ButtonStyle.blurple)
    upscale_button = Button(label="Upscale", style=discord.ButtonStyle.blurple)
    regenerate_button.callback = regenerate_callback
    variant_button.callback = variant_callback
    upscale_button.callback = upscale_callback
    view.add_item(regenerate_button)
    view.add_item(variant_button)
    view.add_item(upscale_button)

    await interaction.edit_original_response(content=f"{interaction.user.mention} Your image is ready!", attachments=[discord.File(f"images/{filename}.png")], embed=embed, view=view)


@tree.command(name="img2img", description="Generate image from given image")
async def image2image_command(interaction: discord.Interaction,
                              prompt: str,
                              image: discord.Attachment,
                              negative_prompt: Optional[str],
                              denoising_strength: Optional[app_commands.Range[float, 0.1, 1.0]],
                              cfg_scale: Optional[app_commands.Range[float, 0.1, 30.0]],
                              steps: Optional[app_commands.Range[int, 10, 60]],
                              seed: Optional[app_commands.Range[int, -1, 0xFFFFFFFF]],
                              ):
    await interaction.response.send_message("Generating...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    img = Image.open(io.BytesIO(await image.read()))
    filename = img2img(img, prompt, negative_prompt,
                       denoising_strength, cfg_scale, steps, seed)
    time_took = round((datetime.datetime.now(
    ) - datetime.datetime.strptime(timestamp, "%Y%m%d-%H%M%S")).total_seconds(), 2)

    # Create discord embed out of the image
    embed = create_embed(filename, prompt, time_took)

    await interaction.edit_original_response(content=f"{interaction.user.mention} Your image is ready!",
                                             attachments=[discord.File(
                                                 f"images/{filename}.png")],
                                             embed=embed)


@client.event
async def on_ready():
    getSamplers()
    print('Logged in as')
    print(client.user.name)
    # Register commands manually, uncomment if you add/change commands or parameters
    try:
       await tree.sync()
    except Exception as e:
       print(f'Failed to sync bot commands with Discord, {e}')


def response_to_image(response, prompt):
    # if response has 'images' key, from txt2img or img2img, else its upscaled
    if 'images' in response:
        for i in response['images']:
            image = Image.open(io.BytesIO(
                base64.b64decode(i.split(",", 1)[0])))
            if len(prompt) > 40:
                prompt = prompt[:40]
            filename = ''.join(e for e in prompt if e.isalnum())
            if filename == '':
                filename = 'image'
            png_payload = {
                "image": "data:image/png;base64," + i
            }
            response2 = requests.post(
                f'http://{sdsettings["address"]}/sdapi/v1/png-info', json=png_payload)
            png_info = PngImagePlugin.PngInfo()
            png_info.add_text('parameters', response2.json().get("info"))
            image.save(f'images/{filename}.png', pnginfo=png_info)
            print(f'images/{filename}.png saved')
            # save the response for debugging
            response.pop('images', None)
            response.pop('init_images', None)
            with open('response.json', 'w') as f:
                f.write(str(response))
                f.close()

            return filename
    else:
        image = Image.open(io.BytesIO(base64.b64decode(response['image'])))
        if len(prompt) > 40:
            prompt = prompt[:40]
        filename = ''.join(e for e in prompt if e.isalnum())
        if filename == '':
            filename = 'image'
        image.save(f'images/{filename}x2.png')
        return filename+'x2'


def text2img(prompt, negative_prompt=None, steps=None, cfg_scale=None, width=None, height=None, seed=None, enable_hr=None):
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
    enable_hr = False if enable_hr is None else enable_hr

    req = {
        "enable_hr": enable_hr,
        "prompt": sdsettings['positive_prompt']+prompt,
        "steps": steps,
        "sampler_index": sdsettings['sampler'],
        "negative_prompt": negative_prompt,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "seed": seed,
    }
    response = requests.post(
        url=f'http://{sdsettings["address"]}/sdapi/v1/txt2img', json=req)
    filename = response_to_image(response.json(), prompt)
    if enable_hr:
        img = Image.open(f'images/{filename}.png')
        filename = img2img(img, prompt, negative_prompt,
                           0.7, cfg_scale, steps, seed)
    return filename


def img2img(img, prompt, negative_prompt=None, denoising_strength=None, cfg_scale=None, steps=None, seed=None):
    # Set default values if not provided
    denoising_strength = float(
        sdsettings['denoising_strength']) if denoising_strength is None else denoising_strength
    cfg_scale = float(sdsettings['cfg_scale']
                      ) if cfg_scale is None else cfg_scale
    steps = int(sdsettings['steps']) if steps is None else steps
    negative_prompt = sdsettings['negative_prompt'] if negative_prompt is None else negative_prompt
    seed = -1 if seed is None else seed

    # Resize if needed
    if img.width > max_size or img.height > max_size:
        if img.width > img.height:
            img = img.resize(
                (max_size, int(max_size * img.height / img.width)))
        else:
            img = img.resize(
                (int(max_size * img.width / img.height), max_size))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')

    width, height = img.size
    width = (width // 64) * 64
    height = (height // 64) * 64

    url = f'http://{sdsettings["address"]}/sdapi/v1/img2img'
    req = {
        "init_images": ["data:image/png;base64," + img_base64],
        "width": width,
        "height": height,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "denoising_strength": denoising_strength,
        "seed": seed,
        "include_init_images": False,
        "sampler_index": sdsettings['sampler'],
    }
    response = requests.post(url, json=req)
    filename = response_to_image(response.json(), prompt)
    return filename


def upscale(img, prompt):
    url = f'http://{sdsettings["address"]}/sdapi/v1/extra-single-image'
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
    req = {
        "image": "data:image/png;base64," + img_base64,
        "upscaling_resize": 2,
        "upscaler_1": sdsettings['upscaler'],
    }
    response = requests.post(url, json=req)
    upscaled_file = response_to_image(response.json(), prompt)
    return upscaled_file


def getSamplers():
    url = f'http://{sdsettings["address"]}/sdapi/v1/samplers'
    response = requests.get(url)
    print("Available samplers:")
    for i in response.json():
        print(f'{i["name"]}', end=', ')
    print("\n-----")


def read_png_info(filename):
    with open(filename, 'rb') as f:
        png = PngImagePlugin.PngImageFile(f)
        info = png.info.get('parameters')
        # if there is info, which is not the case with upscaled images
        if info:
            _info = info.split('\n')
            prompt = _info[0]
            if len(_info) > 2:
                negative_prompt = _info[1].split(': ')[1]
            else:
                negative_prompt = ''
            settings = _info[len(_info)-1].split(', ')
            info_obj = {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'steps': int(settings[0].split(': ')[1]),
                'sampler': settings[1].split(': ')[1],
                'cfg_scale': float(settings[2].split(': ')[1]),
                'seed': int(settings[3].split(': ')[1]),
                'size': settings[4].split(': ')[1],
                'model_hash': settings[5].split(': ')[1],
                'seed_resize_from': settings[6].split(': ')[1],
                'denoising_strength': float(settings[7].split(': ')[1]),
                'ensd': int(settings[8].split(': ')[1]),
            }
            return info_obj
        else:
            info_obj = {
                'prompt': 'Upscaled image 2x',
                'negative_prompt': '',
            }
            return info_obj


def create_embed(filename, prompt, time_took):
    # Create discord embed out of the image
    embed = discord.Embed(title=prompt, color=0xffff00)
    embed.set_image(url=f"attachment://{filename}.png")
    img_info = read_png_info(f'images/{filename}.png')
    if prompt != img_info['prompt']:
        embed.add_field(name="Full prompt",
                        value=f"{img_info['prompt']}", inline=False)
    if img_info['negative_prompt'] != '':
        embed.add_field(name="Negative prompt",
                        value=f"{img_info['negative_prompt']}", inline=False)
    embed.add_field(
        name="Settings",
        value=f"Steps: `{img_info['steps']}`, Sampler: `{img_info['sampler']}`, Size: `{img_info['size']}`, \
             CFG Scale: `{img_info['cfg_scale']}`, Seed: `{img_info['seed']}`, Denoising Strength: `{img_info['denoising_strength']}`",
        inline=True)
    embed.set_footer(text=f"Generation took: {time_took}s")
    return embed


client.run(token)

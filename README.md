# Discord bot for Stable Diffusion using AUTOMATIC1111's WebUI API
Simple to use discord bot that uses [AUTOMATIC1111's massively popular WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui/) to generate images.

## Usage instructions
- Make sure to add ```--api``` to WebUI's commandline args.  
- Configure settings in configuration.ini  
- Install requirements if needed.  
- Run WebUI  
- Run bot.py  
- Generate a picture by using prefix+txt2img_command followed by the prompt, for example:  
```kgen A bowl of fruit on a table```
where ```k``` is the prefix and ```gen``` is the txt2img_command.
![Usage sample](https://iloveur.mom/i/YCLptuTBt4.jpg)
- For now, model swapping is done through the WebUI, like you normally would.


## Configuration
Most of these are self explanatory. Don't use quotation marks.  
positive_prompt gets added to the beginning on your prompt. Negative prompt gets sent as is. Included are NovelAI defaults.  


## Troubleshooting
If you get an error about missing modules, install them using pip.  
  
For errors during image generation, check response.json  
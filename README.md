# Discord bot for Stable Diffusion using AUTOMATIC1111's WebUI API
Simple to use discord bot that uses [AUTOMATIC1111's massively popular WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui/) to generate images.

## Usage instructions
- Make sure to add ```--api``` to WebUI's commandline args.  
- Configure settings in configuration.ini  
- Install requirements if needed.  
- Run WebUI  
- Run bot.py  
- Use /txt2img or /img2img commands  

![txt2img](https://iloveur.mom/i/iD60cesdiY.jpg)
![img2img](https://iloveur.mom/i/znSRFQFbHI.jpg)




## Configuration
Most of these are self explanatory. Don't use quotation marks.  
For now, model swapping is done through the WebUI, like you normally would.  
positive_prompt gets added to the beginning on your prompt. Negative prompt gets sent separately.


## Troubleshooting
If you get an error about missing modules, install them using pip.  
  
For errors during image generation, check response.json  
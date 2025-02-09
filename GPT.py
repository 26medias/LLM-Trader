import os
import base64
import requests
import json
import requests
import imghdr
import os
import time
from openai import OpenAI
from print_color import print

api_key = os.environ.get('OPENAI_API_KEY', '')
client = OpenAI(api_key=api_key)

class GPT:
    def ask(self, sys_prompt="", prompt="", history=[], screenshot=None, model="gpt-4o", temperature=0.9):
        messages = [{"role": "system", "content": [{"type": "text", "text": sys_prompt}]}] + history

        if screenshot:
            with open(screenshot, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            })

        #print(json.dumps(messages, indent=4))
        print("Waiting for GPT...")

        response = client.chat.completions.create(
            model=model,
            #temperature=temperature,
            messages=messages,
            response_format={"type": "json_object"}
        )

        #print(response)
        try:
            msg = response.choices[0].message
            text = msg.content
            return json.loads(text)
        except:
            print("[GPT ASK ERROR]")
            print(response)
            print(response.choices)
            return None

    def getPrompt(self, filename, data={}):
        """
        Load a file and replace placeholders with values from data.
        Placeholders should be in the format {property}.
        
        Parameters:
        - filename (str): Path to the file containing the template.
        - data (dict): Dictionary with key-value pairs to replace in the file.
        
        Returns:
        - str: File content with placeholders replaced by corresponding values.
        """
        with open(filename, 'r') as file:
            content = file.read()

        for key, value in data.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))

        return content

    def generateImage(self, prompt, filename='images'):
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024", #"1792x1024",
                quality="standard", # hd
                style="vivid",
                n=1,
            )

            image_url = response.data[0].url
            return image_url
        except:
            print("Dall-E Error", tag="DallE", tag_color="red", color="white")
            return None
        # Download the image
        #filename, file_extension = self.download_image(image_url, filename)

    def moderate(self, prompt):
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=prompt,
        )

        return response["results"]
    
    def download_image(self, image_url, filename='images/downloaded'):
        # Download the image
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            # Create the images directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Determine the image extension from the content
            file_extension = None
            temp_file = f"{filename}_temp"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            # Use imghdr to detect the file extension
            file_extension = imghdr.what(temp_file)
            if file_extension is None:
                raise ValueError(f"Could not determine the image file type: {temp_file}")

            # Create a proper file name with the correct extension
            final_file_path = f"{filename}.{file_extension}"

            # Rename the temporary file to the final file
            os.rename(temp_file, final_file_path)

            print(f"Image saved as {final_file_path}")

            return final_file_path, file_extension
        else:
            print(f"Failed to download the image. Status code: {response.status_code}")
            return None

    def transcribe(self, filename, output="vtt"):
        audio_file = open(filename, "rb")

        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format=output,
            timestamp_granularities=None if output=="vtt" else ["word"]
        )
        return transcript

    def generateBFLImage(self, prompt, filename='image.png', width=768, height=1024):
        id = self.generateBFLImageRequest(prompt, width, height)
        time.sleep(2)
        url = self.checkBFLRequest(id)
        return self.download_image(url, filename)


    def generateBFLImageRequest(self, prompt, width=768, height=1024):
        url = "https://api.bfl.ml/v1/flux-pro-1.1"

        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "prompt_upsampling": False,
            "seed": 42,
            "safety_tolerance": 2,
            "output_format": "jpeg"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Key": os.getenv('BLACK_FOREST_LABS_API_KEY')
        }

        response = requests.post(url, json=payload, headers=headers)
        results = response.json()
        print(results)
        return results["id"]

    def checkBFLRequest(self, id):
        url = "https://api.bfl.ml/v1/get_result"
        querystring = {"id":id}
        response = requests.get(url, params=querystring)
        results = response.json()
        print(results)
        if results["status"] == "Ready":
            url = results["result"]["sample"]
            return url
        print("Not ready. waiting.")
        time.sleep(2)
        return self.checkBFLRequest(id)



#gpt = GPT()

#response = gpt.generateBFLImage("A high-definition, panoramic, realistic image of a sleek, futuristic alien spaceship bridge with advanced technology. The scene features a modern water cooler emitting a soft glow, surrounded by holographic displays and glowing circuitry. The atmosphere is innovative and forward-thinking, with vibrant and appealing colors. No text or lettering.", "./test/spaceship", width=1440, height=1024)

#print(json.dumps(gpt.moderate("A modern healthcare setting depicting a pediatric clinic focused on opioid pain management. In the foreground, a diverse group of healthcare professionals, including a pediatrician, anesthesiologist, and surgeon, are discussing with a diverse family about opioid overdose prevention. The healthcare providers are showing pamphlets about warning signs of overdose and safe disposal methods for unused medication. In the background, a digital display emphasizes multimodal pain management strategies. The scene is bright and welcoming, with vibrant colors and a clean, professional look, showcasing inclusivity and the importance of community health education. Aspect ratio 16:9."), indent=4))
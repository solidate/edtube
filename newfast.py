from fastapi import FastAPI,Request, WebSocket
import json
import re
from pyyoutube import Api
import asyncio
from async_google_trans_new import AsyncTranslator
from ast import literal_eval
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from yake import KeywordExtractor
from fastapi.responses import HTMLResponse

app = FastAPI()
global api,pattern,g,ques,sid_obj,kw_extractor


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                const obj = JSON.parse(event.data);
                var content = document.createTextNode(JSON.stringify(obj))
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""



@app.on_event("startup")
async def startup_event():
    global api,pattern,g,ques,sid_obj,kw_extractor
    api = Api(api_key='AIzaSyDjxOyPM37gm_CxhqCi84UWdza9Sz4V07w')
    pattern = re.compile("v=([a-zA-Z0-9\_\-]+)&?")
    g = AsyncTranslator()
    ques = re.compile("(^|(?<=[.?!]))\s*[A-Za-z,;'\"\s]+\?")
    sid_obj = SentimentIntensityAnalyzer()
    kw_extractor = KeywordExtractor(lan="en", n=2, top=1)



async def is_question(texts):
    async def _is_question(text):
        qu = list(map(lambda x: int(len(x)>=0),re.findall(ques,text)))
        return qu
    gathers = []
    for text in texts:
        gathers.append(_is_question(text))
    
    return await asyncio.gather(*gathers)



async def keyphrase(texts):
    async def _keyphrase(text):
        kp = kw_extractor.extract_keywords(text)
        keywords = sorted(kp,key = lambda y: y[1])
        keywords = list(map(lambda x:x[0],keywords))
        return keywords
    
    gathers = []
    for text in texts:
        gathers.append(_keyphrase(text))
    
    return await asyncio.gather(*gathers)


async def sentiment(texts):
    async def _sentiment(text):
        sentiment_dict = sid_obj.polarity_scores(text)
        if sentiment_dict['compound'] >= 0.05 :
            return 1
        elif sentiment_dict['compound'] <= - 0.05 :
            return -1
        else :
            return 0

    gathers = []
    for text in texts:
        gathers.append(_sentiment(text))
    
    return await asyncio.gather(*gathers)
    

async def translate(texts):
    global g
    gathers = []
    for text in texts:
    	  gathers.append(g.translate(text, "en"))
    return await asyncio.gather(*gathers)
    


async def correct(texts):
    async def correction(text):
        try:
            return " ".join(literal_eval(text))
        except:
            return ""

    gathers = []
    for text in texts:
        gathers.append(correction(text))
    
    return await asyncio.gather(*gathers)



async def load_comments(match):
    text = []
    for item in match["items"]:
        comment = item["snippet"]["topLevelComment"]
        text.append(re.sub('["]+','',comment["snippet"]["textDisplay"]).strip('\'').split(' '))
    return text

async def _get_comments(url, websocket):
    link = re.findall(pattern,url)[0]
    text = []
    count = 0
    next_page_token = ''
    try:
        while next_page_token is not None and count <= 80:
            print(link)
            match = api.get_comment_threads(video_id=link, text_format='plainText', page_token = next_page_token  ).to_dict()
            next_page_token = match["nextPageToken"]
            texts = await load_comments(match)
            out_texts = await translate(texts)
            out = await correct(out_texts)

            gathers = []
            gathers.append(is_question(out))
            gathers.append(sentiment(out))
            gathers.append(keyphrase(out))
            out = await asyncio.gather(*gathers)
            out = {"ques":out[0],"senti":out[1],"phrase":out[2]}

            await websocket.send_text(json.dumps(out))

    except KeyError:
        match = api.get_comment_threads(video_id=link, text_format='plainText',  ).to_dict()
        text = load_comments(match)
        count = len(text)
        texts = await _get_comments(url)
        out_texts = await translate(texts)
        out = await correct(out_texts)

        gathers = []
        gathers.append(is_question(out))
        gathers.append(sentiment(out))
        gathers.append(keyphrase(out))
        out = await asyncio.gather(*gathers)
        out = {"ques":out[0],"senti":out[1],"phrase":out[2]}

        await websocket.send_text(json.dumps(out))



@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        url = data
        link = re.findall(pattern,url)[0]
        count = 0
        next_page_token = ''
        try:
            while next_page_token is not None and count <= 80:
                match = api.get_comment_threads(video_id=link, text_format='plainText', page_token = next_page_token  ).to_dict()
                next_page_token = match["nextPageToken"]
                texts = await load_comments(match)
                count += len(texts)
                out_texts = await translate(texts)
                out = await correct(out_texts)

                gathers = []
                gathers.append(is_question(out))
                gathers.append(sentiment(out))
                gathers.append(keyphrase(out))
                out = await asyncio.gather(*gathers)
                out = {"ques":out[0],"senti":out[1],"phrase":out[2]}
                # return await asyncio.gather(*gathers)
                await websocket.send_text(json.dumps(out))

        except KeyError:
            match = api.get_comment_threads(video_id=link, text_format='plainText',  ).to_dict()
            texts = load_comments(match)
            count += len(texts)
            out_texts = await translate(texts)
            out = await correct(out_texts)

            gathers = []
            gathers.append(is_question(out))
            gathers.append(sentiment(out))
            gathers.append(keyphrase(out))
            out = await asyncio.gather(*gathers)
            out = {"ques":out[0],"senti":out[1],"phrase":out[2]}
            # return await asyncio.gather(*gathers)
            await websocket.send_text(json.dumps(out))

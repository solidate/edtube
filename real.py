import time
import re
from pyyoutube import Api
import asyncio
from async_google_trans_new import AsyncTranslator
from ast import literal_eval
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from yake import KeywordExtractor
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

global api,pattern,g,ques,sid_obj,kw_extractor
api = Api(api_key='AIzaSyDjxOyPM37gm_CxhqCi84UWdza9Sz4V07w')
pattern = re.compile("v=([a-zA-Z0-9\_\-]+)&?")
g = AsyncTranslator()
ques = re.compile("(^|(?<=[.?!]))\s*[A-Za-z,;'\"\s]+\?")
sid_obj = SentimentIntensityAnalyzer()
kw_extractor = KeywordExtractor(lan="en", n=3, top=1)

async def _is_question(text):
    qu = re.findall(ques,text)
    return len(qu)

async def is_question(texts):
    gathers = []
    for text in texts:
        gathers.append(_is_question(text))
    
    return await asyncio.gather(*gathers)

async def _keyphrase(text):
    kp = kw_extractor.extract_keywords(text)
    keywords = sorted(kp,key = lambda y: y[1])
    keywords = list(map(lambda x:x[0],keywords))
    return keywords

async def keyphrase(texts):
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
    

async def coro(texts):
    global g
    gathers = []
    for text in texts:
    	  gathers.append(g.translate(text, "en"))
    
    return await asyncio.gather(*gathers)
    
async def correction(text):
    try:
        return " ".join(literal_eval(text))
    except:
        return ""

async def correct(texts):
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

async def _get_comments(url):
    link = re.findall(pattern,url)[0]
    text = []
    count = 0
    next_page_token = ''
    try:
        while next_page_token is not None and count <= 80:
            match = api.get_comment_threads(video_id=link, text_format='plainText', page_token = next_page_token  ).to_dict()
            next_page_token = match["nextPageToken"]
            text+=await load_comments(match)
            count = len(text)
    except KeyError:
        match = api.get_comment_threads(video_id=link, text_format='plainText',  ).to_dict()
        text+=load_comments(match)
        count = len(text)

    print('Total Fetched: ',count)
    return text

@app.post("/")
async def get_url(request:Request):
    request = await request.json()
    url = request['url']
    texts = await _get_comments(url)
    out_texts = await coro(texts)
    out = await correct(out_texts)
    # out1 = await is_question(out)
    # out2 = await sentiment(out)
    # out3 = await keyphrase(out)
    
    
    # return {'ques':out1,'senti':out2,'keyp':out3}

    gathers = []
    gathers.append(is_question(out))
    gathers.append(sentiment(out))
    gathers.append(keyphrase(out))

    return await asyncio.gather(*gathers)


@app.get("/")
async def get():
    return HTMLResponse(html)


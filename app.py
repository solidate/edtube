import pandas as pd
import streamlit as st
import re
import json
import ast
from pyyoutube import Api
import numpy as np
from googletrans import Translator
from allennlp.predictors.predictor import Predictor
import allennlp_models.tagging
from yake import KeywordExtractor
import time

translator = Translator(service_urls=[
      'translate.google.com',
      'translate.google.co.in',
    ])

predictor = Predictor.from_path('https://storage.googleapis.com/allennlp-public-models/basic_stanford_sentiment_treebank-2020.06.09.tar.gz')

kw_extractor = KeywordExtractor(lan="en", n=3, top=5)

ques = re.compile("(^|(?<=[.?!]))\s*[A-Za-z,;'\"\s]+\?")

def load_comments(match,text=[]):
    for item in match["items"]:
        comment = item["snippet"]["topLevelComment"]
        text.extend([comment["snippet"]["textDisplay"]])
    
    return text

@np.vectorize
def clean(sentence):
    cleaned = re.sub('["]+','',sentence)
    return cleaned

@np.vectorize
def tran(sentence):
    out = translator.translate(json.dumps(sentence.split()), dest='en').text
    return ' '.join(ast.literal_eval(out))


def sentiment(sentence):
    senti = predictor.predict(sentence)
    return senti['label']

@np.vectorize
def is_question(sentence):
    qu = re.findall(ques,sentence)
    qu = len(qu)
    return qu

@np.vectorize
def keyphrase(article):
    kp = kw_extractor.extract_keywords(text=article)
    keywords = sorted(kp,key = lambda y: y[1])
    kp = [x for x,y in kp[:3]]
    return kp

api = Api(api_key='AIzaSyDjxOyPM37gm_CxhqCi84UWdza9Sz4V07w')

title = "Advanced Youtube Dash"
st.markdown(f"<h1 style='text-align: center; color: red;'>{title}</h1>", unsafe_allow_html=True)

st.markdown('## Paste the video link below')
url = st.text_input("Youtube link or video id")
st.markdown("Check the box if comments also contains non-English comments.")
toggle = False
if st.checkbox('Translate'):
    toggle = True

click = st.button('DO IT')

pattern = re.compile("v=([a-zA-Z0-9\_\-]+)&?")


placeholder = st.empty()
placeholder1 = st.empty()
placeholder2 = st.empty()
placeholder3 = st.empty()
placeholder4 = st.empty()

text = []
if click:
    start = time.time()
    link = re.findall(pattern,url)[0]
    text = []
    
    next_page_token = ''
    try:
        while next_page_token is not None:
            match = api.get_comment_threads(video_id=link, text_format='plainText', page_token = next_page_token  ).to_dict()
            next_page_token = match["nextPageToken"]
            text.extend(load_comments(match,text=text))
    except KeyError:
        match = api.get_comment_threads(video_id=link, text_format='plainText',  ).to_dict()
        text.append(load_comments(match,text=text))
    
    t1 = time.time() - start
    placeholder1.write('TIME TAKEN FOR FETCHING COMMENTS: '+ str(t1))
    com = pd.DataFrame({'Comments':text})
    
    com['Cleaned'] = com.Comments.apply(clean)
    
    t2 = time.time() - start
    placeholder2.write('TIME TAKEN FOR CLEANING COMMENTS: '+ str(t2))
    
    com['Trans'] = com.Cleaned.apply(tran)
    t3 = time.time()-start
    placeholder3.write('TIME TAKEN FOR TRANSLATION: '+ str(t3))
    com['senti'] = com.Trans.apply(sentiment)
    t4 = time.time() - start
    placeholder4.write('TIME TAKEN FOR SENTIMENT ANAL: '+ str(t4))
    com['ques'] = com.Trans.apply(is_question)
    placeholder.write(com)
    com['keys'] = com.Trans.apply(keyphrase)
    placeholder.write(com)

st.write('done')
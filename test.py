import asyncio
from async_google_trans_new import AsyncTranslator

 
async def coro():
    g = AsyncTranslator()
    texts = [["Kya" ,"haal" ,"hai?"]]*10
    gathers = []
    for text in texts:
    	  gathers.append(g.translate(text, "en"))
    
    print(await asyncio.gather(*gathers))
    # return await asyncio.gather(*gathers)

loop = asyncio.get_event_loop() 
loop.run_until_complete(coro())
# print(gathers)

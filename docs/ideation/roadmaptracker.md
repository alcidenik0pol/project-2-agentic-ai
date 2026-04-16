```
    _                    _   _            _    ___ 
   / \   __ _  ___ _ __ | |_(_) ___      / \  |_ _|
  / _ \ / _` |/ _ \ '_ \| __| |/ __|    / _ \  | | 
 / ___ \ (_| |  __/ | | | |_| | (__    / ___ \ | | 
/_/   \_\__, |\___|_| |_|\__|_|\___|  /_/   \_\___|
        |___/                                       

 ____            _           _     ____  
|  _ \ _ __ ___ (_) ___  ___| |_  |___ \ 
| |_) | '__/ _ \| |/ _ \/ __| __|   __) |
|  __/| | | (_) | |  __/ (__| |_   / __/ 
|_|   |_|  \___// |\___|\___|\__| |_____|
              |__/                        
```


This is a user maintained document to track which features they want to implement next

# Scraper Engine

[x] basic version done = make 1 query

## building our sources
[x] check redditstats.com by subscriber count => search my domain
[x] subredditstats.com same
[] r/findareddit — a meta-subreddit where people ask "where do I complain about X?" The answers are crowdsourced and usually accurate. Search it for your domains.
[x] LLM bootstrap — ask Claude or GPT: "give me 20 subreddits where people describe personal frustrations or problems related to [domain]." The output is imperfect but gives you a starting list to manually filter down. Confidence ~70% on quality, but good enough to start from.
[x] run the api from reddit -> make sure the throttling works
[x] try the api on 2-3 subreddits
[x] lets target 100 subreddits for now
[] caching!! see api.md file = cache popular reddit niches

## AI engine
[x] setup gcloud and project properly
[x] replace LM studio with gcloud
[x] round 1 free tags -> but improve or make them more detailed
[x] round 2 embeddings + k-means as tool
[] perform an audit of the full agent process = each step

### Report
[] why is the pain point truncated

# Frontend

## Main
[x] fix chatbar
[] curated logs
[] add time completion
[x] add EDA result
[] fix reddit api indicator


## Results


[] 
[] 
[] 
[] 

src:
https://claude.ai/chat/aa9a6106-ae5c-4847-9296-d1b208b15f87
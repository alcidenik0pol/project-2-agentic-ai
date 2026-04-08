1. Verify Reddit API access works
Before designing anything. Get a token, make one call, see real data. This takes 30 minutes and can kill the whole plan if it fails.
2. Define your two agents
You need at least two with distinct jobs. The obvious split:

Agent 1: Data collector. Knows how to query Reddit, pull posts, return raw data.
Agent 2: Analyst. Takes raw data, finds complaint clusters, forms the hypothesis.

3. Pick your agent framework
LangGraph, OpenAI Agents SDK, CrewAI. Pick one you can actually use, not the coolest one. This decision affects everything downstream.
4. Build the pipeline skeleton first, fake data second
Get the agents talking to each other with dummy data before touching the Reddit API. This isolates bugs.
5. Plug in real Reddit data
Replace dummy data with live calls. Verify the output changes based on different user inputs.
6. Build EDA tools
Frequency counting, complaint clustering, upvote weighting. This is what separates a real pipeline from a chatbot wrapper.
7. Build the frontend last
It's worth 2 points. Don't build it first.
8. Deploy
Also worth 2 points and always takes longer than expected. Don't leave it for the last hour.

https://claude.ai/chat/fea8c565-859b-47a1-aa21-0297b5887f45
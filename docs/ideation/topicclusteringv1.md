Step 1: Embed each unique theme label
Take your 98 unique theme strings and convert each one into a vector using an embedding model. An embedding is just a list of numbers that represents the semantic meaning of the text. "workplace frustration" and "workplace dissatisfaction" will have very similar vectors because they mean similar things.
You use text-embedding-3-small from OpenAI or voyage-3 from Voyage AI. Both are cheap — 98 short strings costs fractions of a cent.

Step 2: Run k-means on the vectors
K-means groups the 98 vectors into k clusters by finding which ones are geometrically close to each other. You pick k somewhere between 8 and 15. Posts that mean similar things end up in the same cluster.
The output is: each of your 98 labels gets assigned a cluster ID (0 through k-1).

Step 3: Name each cluster
You have a cluster of labels but no name for it yet. Send the labels in each cluster to Claude and ask: "what is the single best name for a cluster containing these themes?" It comes back with "toxic management" or "financial system failures" etc.

Step 4: Map back to posts
Each post already has a freeform label. That label now belongs to a cluster. So every post gets a cluster name. Now you can count: 34 posts about "toxic management", 18 about "financial stress", etc. That's your EDA output.


---

For embeddings specifically, you use "Embeddings for Text" — that's the one listed under the Embeddings models section. In the API it's called text-embedding-004. It's Google's equivalent of OpenAI's text-embedding-3-small.
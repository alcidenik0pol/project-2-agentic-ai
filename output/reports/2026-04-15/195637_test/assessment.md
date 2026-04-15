Pipeline Assessment: Quality & Efficiency
                                                                                
  Based on run 195637_live (30 posts, ~10.5 minutes total)
                                                                                       
  ---
  STEP 1: Subreddit Selection (Call 8)                                                 
                                                    
  ┌────────────┬────────────────────────────────────────────────────────────────────┐  
  │   Aspect   │                               Status                               │  
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │ Quality    │ ⚠️ CANNOT ASSESS - Test mode used sample data instead of live      │
  │            │ Reddit                                                             │
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │ Efficiency │ N/A - skipped in test mode                                         │
  └────────────┴────────────────────────────────────────────────────────────────────┘

  ---
  STEP 2: Data Fetching (Call 1 - Orchestrator)

  ┌────────────┬────────────────────────────────────────────────┐
  │   Aspect   │                     Status                     │
  ├────────────┼────────────────────────────────────────────────┤
  │ Quality    │ ⚠️ CANNOT ASSESS - Used data/sample_posts.json │
  ├────────────┼────────────────────────────────────────────────┤
  │ Efficiency │ N/A - 0.0s because it loaded local file        │
  └────────────┴────────────────────────────────────────────────┘

  ---
  STEP 3: Classification (Call 4)

  ┌────────────┬───────────────────────────────────────────────────────────────────┐
  │   Aspect   │                            Assessment                             │
  ├────────────┼───────────────────────────────────────────────────────────────────┤
  │            │ ❌ PROBLEM - Classifier returning meta-labels like "No complaint" │
  │ Quality    │  (3x), "Not a complaint" (2x) as themes. These aren't complaint   │
  │            │ themes - they're classification outputs masquerading as themes.   │
  │            │ Either filter non-complaints OR extract actual topic.             │
  ├────────────┼───────────────────────────────────────────────────────────────────┤
  │            │ ❌ TOO SLOW - 445s for 30 posts = 14.8s/post. Scaled to 500 posts │
  │ Efficiency │  = 2+ hours. 30 sequential LLM calls with no                      │
  │            │ batching/parallelization.                                         │
  ├────────────┼───────────────────────────────────────────────────────────────────┤
  │ Success    │ 93.3% (28/30) - acceptable                                        │
  │ Rate       │                                                                   │
  └────────────┴───────────────────────────────────────────────────────────────────┘

  ---
  STEP 4: Clustering (Calls 5, 6)

  4a. Theme Expansion (Call 5)

  ┌────────────┬──────────────────────────────────────────────────────────────┐
  │   Aspect   │                          Assessment                          │
  ├────────────┼──────────────────────────────────────────────────────────────┤
  │ Quality    │ ✅ Works - expands 25 themes into longer descriptions        │
  ├────────────┼──────────────────────────────────────────────────────────────┤
  │ Efficiency │ ⚠️ SLOW - 72.6s for batch expansion (60% of clustering time) │
  └────────────┴──────────────────────────────────────────────────────────────┘

  4b. Cluster Naming (Call 6)

  ┌────────────┬────────────────────────────────────────────────────────────────────┐
  │   Aspect   │                             Assessment                             │
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │            │ ❌ PROBLEM - Cluster names are TRUNCATED: "Concerns about",        │
  │ Quality    │ "Difficulty managing", "Uncertainty". The prompt explicitly warns  │
  │            │ against this but max_tokens=64 is still cutting off responses.     │
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │ Efficiency │ ⚠️ SLOW - 31.6s for 8 clusters = ~4s/cluster. Could batch name     │
  │            │ generation.                                                        │
  └────────────┴────────────────────────────────────────────────────────────────────┘

  Overall Clustering: 121s total. Embedding + KMeans = 16.7s (efficient). LLM steps =
  104s (85% of time).

  ---
  STEP 5: Hypothesis Generation (Call 7)

  ┌────────────┬────────────────────────────────────────────────────────────────────┐
  │   Aspect   │                             Assessment                             │
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │ Quality    │ ✅ GOOD - 5 specific ideas with: revenue models, pricing, first    │
  │            │ user step, evidence linkage. Strong output.                        │
  ├────────────┼────────────────────────────────────────────────────────────────────┤
  │ Efficiency │ ⚠️ OK - 66.3s for single call is acceptable for output quality     │
  └────────────┴────────────────────────────────────────────────────────────────────┘

  ---
  Summary

  ┌─────────────────────┬─────────┬────────────┬───────────────────────────────────┐
  │        Step         │ Quality │ Efficiency │            Bottleneck             │
  ├─────────────────────┼─────────┼────────────┼───────────────────────────────────┤
  │ Subreddit Selection │ ?       │ ?          │ Test mode - not assessed          │
  ├─────────────────────┼─────────┼────────────┼───────────────────────────────────┤
  │ Data Fetching       │ ?       │ ?          │ Test mode - not assessed          │
  ├─────────────────────┼─────────┼────────────┼───────────────────────────────────┤
  │ Classification      │ ❌      │ ❌         │ Sequential LLM calls (14.8s/post) │
  ├─────────────────────┼─────────┼────────────┼───────────────────────────────────┤
  │ Clustering          │ ⚠️      │ ⚠️         │ Truncated names, slow expansion   │
  ├─────────────────────┼─────────┼────────────┼───────────────────────────────────┤
  │ Hypothesis          │ ✅      │ ✅         │ None                              │
  └─────────────────────┴─────────┴────────────┴───────────────────────────────────┘

  ---
  Critical Issues to Fix

  1. Classification: Meta-labels ("No complaint") leaking into theme list
  2. Cluster Names: max_tokens=64 causing truncation despite prompt warning
  3. Performance: Sequential classification = 2+ hours for 500 posts. Need
  parallelization or batching.
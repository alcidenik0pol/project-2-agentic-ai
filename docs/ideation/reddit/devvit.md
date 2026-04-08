Readme
Galaxy Guide - Project Intercept Reddit Bot
A Reddit bot built with Devvit that automatically responds to Samsung product-related questions and inquiries across designated subreddits. This is an unlisted app for Project Intercept.

Overview
This bot monitors Reddit posts and comments for Samsung product discussions, using intelligent keyword matching to identify relevant questions. When a match is found, the bot provides AI-powered responses to help users with Samsung product information and support.

How It Works
The bot uses a sophisticated keyword matching system that looks for:

Product Keywords: Samsung device and product names
Feature Keywords: Product features and specifications
Intent Keywords: Purchase intentions and comparisons
Inquiry Keywords: Question indicators and help requests
A response is triggered when the bot detects:

Samsung product mentions combined with questions (containing "?") or intent/feature keywords
Feature or inquiry keywords paired with intent indicators
Purpose
Designed to enhance Samsung product discussions on Reddit by providing timely, accurate information to users seeking help with Samsung devices and services.

Developer Guide
Bot Account Credentials
Reddit Bot Account:

Username: Thin-Resource5495
Password: Contact Platform Development Team
App Page: https://developers.reddit.com/apps/galaxy-guide (requires authenticated access with bot account)
⚠️ Note: The Galaxy Guide app page is only visible when logged in with the bot account credentials.

Prerequisites
Node.js (v18 or higher recommended)
Devvit CLI installed globally
A Reddit account with developer access
Access to the Nucleus AI API (dev and prod endpoints)
Getting Started
1. Install Devvit CLI
npm install -g devvit
2. Authenticate with Reddit
devvit login
Follow the prompts to authenticate with your Reddit account.

3. Clone and Install Dependencies
git clone <repository-url>
cd nucleus-reddit-bot
npm install
4. Configure Environment Variables
This app uses Devvit's settings system for configuration. You'll need to set up the following secrets:

environment: Select 'Development' or 'Production'
ai-api-key-dev: API key for the development Nucleus AI endpoint
ai-api-key-prod: API key for the production Nucleus AI endpoint
Note: Since this is an unlisted app, settings are configured through the Devvit CLI or Reddit's Developer Platform after installation.

Development Workflow
Local Development & Testing
Devvit provides a local testing environment called "Playtest":

# Start local development server
devvit playtest <subreddit-name>
This uploads your app to a test subreddit where you can interact with it in real-time. The playtest session will automatically reload when you make changes to your code.

Testing Tips:

Use a test subreddit you have moderator access to
Create test posts/comments with Samsung product keywords to trigger the bot
Check the Devvit logs in your terminal for debugging output
Use console.log() statements for debugging - they appear in the playtest logs
Building the App
# Compile TypeScript
npm run build
Or use the Devvit CLI:

devvit build
Adding the Bot to a New Subreddit
Since this is an unlisted app, installation requires coordination with the subreddit moderators. Follow these steps:

Step 1: Get Moderator Access
The subreddit moderator must add the bot account as a moderator:

Ask the subreddit moderator to invite u/Thin-Resource5495 as a moderator
The bot account needs at least "Manage Posts and Comments" permissions
Accept the moderator invitation by logging in as Thin-Resource5495
Step 2: Install the Bot via Developer Platform
Recommended Method - Use the web interface:

Log in to Reddit as Thin-Resource5495
Navigate to the Galaxy Guide App Page
Click "Install" or "Add to Subreddit"
Select the target subreddit from the dropdown
Confirm the installation
Step 3: Configure App Settings / Environmental Variables
If you prefer using the command line:

# Make sure you're authenticated as the bot account
devvit login

# Install on target subreddit
devvit install <subreddit-name>

# Configure settings via CLI
devvit settings set <subreddit-name> environment <dev|prod>
devvit settings set <subreddit-name> ai-api-key-dev <your-dev-key>
devvit settings set <subreddit-name> ai-api-key-prod <your-prod-key>
Deployment
Since this is an unlisted app, it won't appear in the Reddit App Directory. Installation is done manually via the methods above.

Publishing a New Version
Update Version: Increment the version in devvit.yaml

Upload to Reddit:

devvit upload
Upgrade Existing Installations:

Log in to the Galaxy Guide App Page as Thin-Resource5495
Find the subreddit installation and click "Upgrade"
Or use CLI:

devvit install <subreddit-name> --upgrade
Updating an Existing Installation
# Upload new version
devvit upload

# Upgrade the app on a subreddit
devvit install <subreddit-name> --upgrade
Project Structure
nucleus-reddit-bot/
├── devvit.yaml           # App manifest and version
├── package.json          # Node dependencies
├── tsconfig.json         # TypeScript configuration
├── src/
│   └── main.tsx          # Main bot logic
└── README.md
Key Files
devvit.yaml: App configuration, name (Galaxy-Guide), and version
src/main.tsx: Main application code including:
Trigger logic for post/comment monitoring
Keyword matching system
AI API integration
Response generation
API Endpoints
The bot integrates with the Nucleus AI API:

Dev: https://nucleus-api-dev-920865761320.us-central1.run.app/ai/searches
Prod: https://nucleus-api-920865761320.us-central1.run.app/ai/searches
Useful Devvit Commands
# View logs for a subreddit installation
devvit logs <subreddit-name>

# List all installed apps on a subreddit
devvit list installs <subreddit-name>

# View app details
devvit info

# Uninstall from a subreddit
devvit uninstall <subreddit-name>

# Check your uploaded app versions
devvit list versions
Documentation & Resources
Devvit Documentation: https://developers.reddit.com/docs/0.11/
Devvit Quickstart: https://developers.reddit.com/docs/0.11/quickstart
Devvit Playtest Guide: https://developers.reddit.com/docs/0.11/playtest
Settings & Secrets: https://developers.reddit.com/docs/0.11/capabilities/secrets-storage
Troubleshooting
Bot not responding:

Check that the app is installed and enabled on the subreddit
Verify API keys are correctly configured in settings
Check logs with devvit logs <subreddit-name>
Ensure the subreddit allows bot accounts
Playtest issues:

Make sure you're a moderator of the test subreddit
Try restarting the playtest session
Check for TypeScript compilation errors
Installation issues:

Verify you have moderator permissions on the target subreddit
Ensure the app version has been uploaded successfully
Check that all required settings are configured
Development Best Practices
Test locally using devvit playtest before uploading
Increment versions in devvit.yaml for each release
Use dev environment for testing with ai-api-key-dev
Monitor logs regularly to catch issues early
Keep secrets secure - never commit API keys to the repository

# Reddit API
Reddit API Overview
The Reddit API allows you to read and write Reddit content such as posts / comments / upvotes, in order to integrate your app's behavior with the content of the community it's installed in.

note
Unlike traditional Reddit API usage, you don't need to create an app at reddit.com/prefs/apps or manage API keys. Devvit handles authentication automatically when you enable the reddit permission in your app.

Private user data
Devvit apps cannot access certain private user data. This data is private to the logged-in user and is not exposed through the Devvit platform:

Subscribed subreddits - The list of subreddits a user is subscribed to
Upvoted and downvoted content - Posts and comments the user has voted on
Saved content - Posts and comments the user has saved
Recently viewed posts - The user's browsing history
Private profile information - Any profile data that is not publicly visible
Follows and friends - The list of users someone follows (on reddit.com) or has friended (on Old Reddit)
The Reddit client
Here's how to obtain a reference to the Reddit client

Devvit Web
Devvit Blocks / Mod Tools
devvit.json
{
  "permissions": {
    "reddit": true
  }
}

server/index.ts
import { reddit } from '@devvit/reddit';

Reddit Thing IDs
Reddit uses prefixed IDs (called "things") to identify different types of content:

Prefix	Type	Example	Description
t1_	Comment	t1_abc123	A comment on a post or reply to another comment
t2_	User	t2_xyz789	A Reddit user account
t3_	Post	t3_def456	A post
t4_	Message	t4_ghi012	A private message
t5_	Subreddit	t5_jkl345	A subreddit community
These IDs are returned by API methods and used when referencing specific content:

// Get a post by its full ID
const post = await reddit.getPostById('t3_abc123');

// Get a comment by its full ID  
const comment = await reddit.getCommentById('t1_xyz789');

// A comment's parentId can be either a post (t3_) or another comment (t1_)
const parentId = comment.parentId; // 't3_abc123' or 't1_def456'

Example usage
Submitting a post
Devvit Web
Devvit Blocks / Mod Tools
import { Devvit } from '@devvit/public-api';
import { context, reddit } from '@devvit/web/server';

export const createPost = async () => {
const { subredditName } = context;
if (!subredditName) {
  throw new Error('subredditName is required');
}

return await reddit.submitCustomPost({
  userGeneratedContent: {
    text: 'Hello there! This is a post from a Devvit app',
  },
  subredditName: subredditName,
  title: 'New Post',
  entry: 'default',
});
};

Submitting a comment
note
Auto-comments should be used to spark conversation in the post comments, but you should avoid lower-signal updates (e.g., level/progress pings).

Devvit Web
Devvit Blocks / Mod Tools
    import { context, reddit } from '@devvit/web/server';

    export const createComment = async () => {
        const { subredditName } = context;
        if (!subredditName) {
            throw new Error('subredditName is required');
        }

        reddit.submitComment({
            postId: 't3_123456', // Replace with the actual post ID
            text: 'This is a comment from a Devvit app',
            runAs: 'USER' // Optional: specify the user to run as
        });
    };
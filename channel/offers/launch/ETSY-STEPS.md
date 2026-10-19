# Etsy: what only you can do (about 20 minutes), then the agent does the rest

Etsy is not approved yet (rule 9). When you say yes:
1. etsy.com/developers/your-apps: create an app (personal access). Copy its keystring.
2. Add the redirect `https://localhost/callback` to the app.
3. Put the keystring in the environment as `ETSY_API_KEY` (never a file or a message).
4. Tell the agent. It runs `python -m faceless etsy auth` and gives you a link; open it signed in to your shop, approve, and send back the `code=` value from the address bar.
5. The agent builds a **draft** listing with the link-free edition of the planner (9 images, a silent video, the AI sentence), and you approve the price and the AI disclosure and publish by hand. Read Etsy's listing-image requirements first. The Etsy cover should be the coin cover, not the Quinton cover (decision D11 pending).

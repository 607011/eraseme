# eraseme
Collection of tools to erase traces of your internet activities

## Reddit: delete all your posts

Use `/home/runner/work/eraseme/eraseme/delete_reddit_posts.py` to delete every submission for one Reddit account.

### Requirements

1. Create a Reddit "script" app at https://www.reddit.com/prefs/apps.
2. Set credentials as environment variables:

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USERNAME="..."
export REDDIT_PASSWORD="..."
export REDDIT_USER_AGENT="eraseme-delete-reddit-posts/1.0" # optional
```

### Usage

Dry run first:

```bash
python /home/runner/work/eraseme/eraseme/delete_reddit_posts.py --dry-run
```

Delete posts:

```bash
python /home/runner/work/eraseme/eraseme/delete_reddit_posts.py
```

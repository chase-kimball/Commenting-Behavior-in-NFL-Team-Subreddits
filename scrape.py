import json
import requests
import praw
import prawcore
import numpy as np
from datetime import datetime
import pandas as pd
import argparse

# Setting up command-line argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--subreddit', type=str, required=True)
parser.add_argument('--Nposts', type=int, required=True)
parser.add_argument('--Ncomments', type=int, required=True)
parser.add_argument('--group', type=str, required=True)

def scrape_post_comments(name, N=10, sort='hot'):
    """
    Scrapes comments from a given subreddit.

    Parameters:
    - name (str): The name of the subreddit.
    - N (int): The number of posts to scrape from the subreddit 
    - sort (str): The sorting method for posts.

    Returns:
    - df (DataFrame):  DataFrame containing the scraped posts or comments and metadata.
    """
    with open('credentials.json', 'r') as f:
        creds = json.load(f)

        reddit = praw.Reddit(**creds)
        
    columns = ['author', 'body', 'created_utc', 'score', 'subreddit', 'link_id', 'author_flair_text']
    pdict = dict(zip(columns, [[] for i in range(len(columns))]))
    pdict['title'] = []
    pdict['name'] = []
    
    hub = reddit.subreddit(name)
    posts = hub.hot(limit=N) 
    
    while True:
        try:
            post = next(posts)
            print(post)
        except StopIteration:
            print('Finished iterating')
            break
        except Exception as e:
            if type(e) == prawcore.exceptions.Forbidden:
                continue

        for comment in post.comments.list():
            if type(comment) == praw.models.reddit.more.MoreComments: 
                continue
            pdict['title'].append(post.title)
            pdict['name'].append(post.name)
            for key in columns:
                pdict[key].append(getattr(comment, key))
                
    for key in pdict:
        if type(pdict[key][0]) not in (int, str, float):
            pdict[key] = [str(x) for x in pdict[key]]
            
    if 'created_utc' in pdict:
        for ii in range(len(pdict['created_utc'])):
            pdict['created_utc'][ii] = datetime.fromtimestamp(pdict['created_utc'][ii]).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    df = pd.DataFrame(pdict)
    return df
            
def scrape_posts_or_comments(name, kind='subreddit', N=10, sort='new'):
    """
    Scrapes either posts from a subreddit or comments from a user.

    Parameters:
    - name (str): The name of the subreddit or user.
    - kind (str): The kind of object to scrape ('subreddit' or 'redditor').
    - N (int): The number of posts/comments to scrape 
    - sort (str): The sorting method for the data. 

    Returns:
    - df (DataFrame): DataFrame containing the scraped posts or comments and metadata.
    """
    with open('credentials.json', 'r') as f:
        creds = json.load(f)

        reddit = praw.Reddit(**creds)
    
    if kind == 'subreddit':
        hub = reddit.subreddit(name)
        columns = ['author', 'title', 'score', 'subreddit', 'upvote_ratio', 'id']
    elif kind == 'redditor':
        hub = reddit.redditor(name).comments
        columns = ['author', 'body', 'score', 'subreddit', 'link_id', 'over_18', 'controversiality', 'author_flair_text']   
    else:
        print("kind must be either subreddit or redditor")
        return
        
    if sort == 'new':
        posts = hub.new(limit=N)
    elif sort == 'top':
        posts = hub.controversial(limit=N)
    elif sort == 'hot':
        posts = hub.hot(limit=N)
    elif sort == 'controversial':
        posts = hub.controversial(limit=N)
    else:
        print("Sort must either be by new, hot, or controversial")
        return
        
    pdict = dict(zip(columns, [[] for i in range(len(columns))]))
    pdict['created_utc'] = []
    banned = False
    
    while True:
        try:
            post = next(posts)
            if kind == 'subreddit': 
                print(post)
        except StopIteration:
            print('Finished iterating')
            break
        except prawcore.exceptions.Forbidden:
            print('Forbidden. Possibly found banned user. Continuing')
            banned = True
            break
        except prawcore.exceptions.NotFound:
            print('Comment Not Found. Continuing')
            break
            
        for key in columns:
            pdict[key].append(getattr(post, key))
            
        pdict['created_utc'].append(datetime.fromtimestamp(post.created_utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        
    if len(pdict['author']) == 0:
        df = pd.DataFrame(pdict)
        return df
        
    for key in pdict:
        if type(pdict[key][0]) not in (int, str, float):
            pdict[key] = [str(x) for x in pdict[key]]
    
    df = pd.DataFrame(pdict)
    return df

if __name__ == "__main__":
    args = parser.parse_args()
    
    # Scrape posts from the specified subreddit
    posts = scrape_posts_or_comments(args.subreddit, kind='subreddit', N=args.Nposts)
    posts.to_csv('data/' + args.group + '/posts/' + args.subreddit + '.csv')
    
    # Get unique authors from the scraped posts
    authors = np.unique(posts.author)
    
    comments = pd.DataFrame()
    
    # Scrape comments for each author
    for ii, author in enumerate(authors):
        print(ii, author)
        new_comments = scrape_posts_or_comments(author, kind='redditor', N=args.Ncomments)
        comments = comments.append(new_comments, ignore_index=True)
        
    comments.to_csv('data/' + args.group + '/comments/' + args.subreddit + '.csv')

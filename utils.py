import pandas as pd
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk import tokenize
import nltk
import datetime

with open('nfl_subs.txt','r') as f:
    subs = [s.strip() for s in f.readlines()]
with open('nfl_flairs.txt','r') as f:
    flairs = [fl.strip() for fl in f.readlines()]
with open('nfl_inits.txt','r') as f:
    inits = [i.strip() for i in f.readlines()]
df = pd.DataFrame(dict(subreddit=subs, flair=flairs, inits=inits))
teams=df
team2abbrev = dict(zip(teams.subreddit,teams.inits))
flair2team = dict(zip(teams.flair, teams.subreddit))

def filter_comments_by_subs(filename, subs):
    
    coms = pd.read_csv(filename)
    
    return coms[coms.subreddit.isin(subs.values)]


def get_division_edges(sublist):
    edges = []
    for sub in sublist:
        edges.extend(get_sub_edges(sub, sublist))
    return edges
        

def process_coms(filename, no_zero_sentiment=False):
    """
    Process comments from a CSV file, perform sentiment analysis, and calculate various metrics.

    Args:
    - filename (str): Path to the CSV file containing comments.
    - no_zero_sentiment (bool): Flag to exclude comments with zero sentiment.

    Returns:
    - coms (pd.DataFrame): Filtered comments DataFrame with sentiment scores.
    - metadata (dict): Dictionary containing various metrics about the comments.
    """

    # Extract subreddit name from filename
    subname = filename.split('/')[-1].split('.')[0]

    # List of all NFL team subreddits
    all_nfl_subs = ['nfl'] + list(teams.subreddit.values)
    all_other_team_subs = all_nfl_subs.copy()
    
    # Remove current subreddit and 'nfl' from the list of all other team subreddits
    all_other_team_subs.remove(subname)
    all_other_team_subs.remove('nfl')

    try:
        coms = pd.read_csv(filename, lineterminator='\n').dropna(subset=['author', 'body', 'author_flair_text'])
    except KeyError:
        return filename, None

    # Convert subreddit names to lowercase
    coms.subreddit = coms.subreddit.str.lower()

    # Print total number of comments 
    print('Total comments:', len(coms))

    ##### Extract subreddit users who have commented on /r/nfl with flairs #####

    # Get unique authors who have commented
    authors = np.unique(coms.author.values)
    n_auth = len(authors)  
    print('Unique authors:', n_auth)

    flairs = []
    flaired_authors = []

    # Iterate over unique authors to find flaired users
    for ii, author in enumerate(authors):
        acoms = coms[coms.author.isin([author])]  # Comments by the current author
        nfl_acoms = acoms[acoms.subreddit.isin(['nfl'])]  # Comments in /r/nfl by the current author
        
        # Skip if there are no comments by the author in /r/nfl
        if len(nfl_acoms) == 0:
            continue
            
        # Extract team flair and clean
        nfl_acom = nfl_acoms.iloc[0]  
        
        raw_flair = nfl_acom.author_flair_text.split(':')  # Split author flair text by ':'
        if len(raw_flair) < 3:
            continue
        
        flair = raw_flair[2].lower().strip()  
        
        # Skip if the flair is not in the list of team flairs
        if not flair in teams.flair.values:
            continue
        else:
            flaired_authors.append(nfl_acom.author)  # Add the author to the list of flaired authors
        
        # Iterate over comments by the author
        for jj, acom in acoms.iterrows():
            flairs.append(flair2team[flair])  # Map the flair to a team using flair2team dictionary

    # Filter comments to include only those by flaired authors and add 'flair' column
    coms = coms[coms.author.isin(flaired_authors)]
    coms['flair'] = flairs

    n_all = len(coms)  # Total number of comments after filtering by flaired authors

    # Filter comments to include only those in NFL-related subreddits and with the current subreddit flair
    coms = coms[coms.subreddit.isin(all_nfl_subs)]
    coms = coms.iloc[np.where(coms.flair == subname)[0]]  # Filter by current subreddit flair

    n_flaired_auth = len(np.unique(coms.author.values)) 
    
    ###############################################

    # Filter comments again to ensure they are in NFL-related subreddits

    coms = coms[coms.subreddit.isin(all_nfl_subs)]

    # Perform sentiment analysis on comments
    sentiments = []
    i_nonzero = []  # Indices of comments with non-zero sentiment

    izero = 0
    print(len(coms), 0)
    
    # Iterate over comments to calculate sentiment
    for ii, com in coms.iterrows():
        sentence_list = tokenize.sent_tokenize(com.body)  # Tokenize comment into sentences
        commentSentiment = 0.0
        
        # Calculate sentiment for each sentence and aggregate
        for sentence in sentence_list:
            vs = analyzer.polarity_scores(sentence)  # Perform sentiment analysis using analyzer
            commentSentiment += vs["compound"]  # Add compound sentiment score
        
        commentSentiment /= len(sentence_list)  # Calculate average sentiment score for the comment

        # Exclude comments with zero sentiment if no_zero_sentiment flag is set
        if no_zero_sentiment:
            if commentSentiment == 0.0:
                izero += 1
                continue
            else:
                sentiments.append(commentSentiment)
                i_nonzero.append(ii)
        else:
            sentiments.append(commentSentiment)
            i_nonzero.append(ii)

    # Add sentiment scores to comments DataFrame
    if no_zero_sentiment:
        coms = coms.loc[i_nonzero]

    coms['sentiment'] = sentiments
    print('Number of comments with zero sentiment:', izero)

    n_coms = len(coms)  # Number of comments after sentiment analysis
    print('Number of remaining comments:', n_coms)

    # Partition comments
    rnfl = coms[coms.subreddit.isin(['nfl'])]  # Comments in /r/nfl
    nfl = coms[coms.subreddit.isin(all_nfl_subs)]  # Comments in all NFL-related subreddits
    selfc = coms[coms.subreddit.isin([subname])]  # Comments in the current subreddit
    other = coms[coms.subreddit.isin(all_other_team_subs)]  # Comments in other NFL team subreddits

    # Calculate summary stats for each subset
    n_rnfl = len(rnfl)
    n_nfl = len(nfl)
    n_self = len(selfc)
    n_other = len(other)
    
    perc_rnfl_related = n_rnfl / n_coms
    perc_nfl_related = n_nfl / n_all
    perc_self_related = n_self / n_coms
    perc_other_related = n_other / n_coms
    perc_flaired_auth = n_flaired_auth / n_auth

    # Calculate average sentiment and controversiality for each subset
    avg_rnfl_sent = [rnfl.sentiment.mean(), rnfl.controversiality.sum() / len(rnfl)]
    avg_nfl_sent = [nfl.sentiment.mean(), nfl.controversiality.sum() / len(nfl)]
    avg_self_sent = [selfc.sentiment.mean(), selfc.controversiality.sum() / len(selfc)]
    avg_other_sent = [other.sentiment.mean(), other.controversiality.sum() / len(other)]

    # Construct metadata dictionary with metrics
    metadata = dict(
        team=[subname],
        n_coms=[n_coms],
        perc_flaired_auth=[perc_flaired_auth],
        perc_rnfl_related=[perc_rnfl_related],
        perc_nfl_related=[perc_nfl_related],
        perc_self_related=[perc_self_related],
        perc_other_related=[perc_other_related],
        avg_rnfl_sent=[avg_rnfl_sent],
        avg_nfl_sent=[avg_nfl_sent],
        avg_self_sent=[avg_self_sent],
        avg_other_sent=[avg_other_sent]
    )

    return coms, metadata

def filter_processed_coms_by_date(filename, start, stop):
    """
    Filters and processes comments from a CSV file within a specified date range and returns the filtered comments along with metadata.

    Parameters:
    filename (str): The path to the CSV file containing comments data.
    start (datetime): The start date for filtering comments.
    stop (datetime): The end date for filtering comments.

    Returns:
    tuple: A tuple containing:
        - coms (DataFrame): A pandas DataFrame with the filtered comments.
        - metadata (dict): A dictionary containing metadata about the filtered comments.
    """
    subname = filename.split('/')[-1].split('.')[0]
    
    print(subname)
    
    # List of NFL-related subreddits
    all_nfl_subs = ['nfl'] + list(teams.subreddit.values)
    all_other_team_subs = all_nfl_subs.copy()
    all_other_team_subs.remove(subname)
    all_other_team_subs.remove('nfl')    

    inew = []  # List to store indices of comments within the date range
    
    # Load the comments 
    coms = pd.read_csv(filename, lineterminator='\n').dropna(subset=['author', 'body', 'author_flair_text'])

    # Filter comments by the specified date range
    for ii, com in coms.iterrows():
        try:
            date = datetime.datetime.fromisoformat(com.created_utc.split('T')[0])
            if date > start and date < stop:
                inew.append(ii)
        except AttributeError:
            print('bad comment')  
            continue
    
    coms = coms.loc[inew]
    print(len(coms))
    

    n_coms = len(coms)  
    n_all = n_coms
    n_auth = len(np.unique(coms.author)) 
    n_flaired_auth = n_auth  
    
    # Categorize comments i
    rnfl = coms[coms.subreddit.isin(['nfl'])]  # Comments in the 'nfl' subreddit
    nfl = coms[coms.subreddit.isin(all_nfl_subs)]  # Comments in all NFL-related subreddits
    selfc = coms[coms.subreddit.isin([subname])]  # Comments in the current team's subreddit
    other = coms[coms.subreddit.isin(all_other_team_subs)]  # Comments in all other teams' subreddits
    
    n_rnfl = len(rnfl)
    n_nfl = len(nfl)
    n_self = len(selfc)
    n_other = len(other)
    
    # Ensure no division by zero by setting default values
    if n_all == 0: n_all = 1
    if n_coms == 0: n_coms = 1
    if n_auth == 0: n_auth = 1

    # Calculate the percentage of comments related to various categories
    perc_rnfl_related = n_rnfl / n_coms
    perc_nfl_related = n_nfl / n_all
    perc_self_related = n_self / n_coms
    perc_other_related = n_other / n_coms
    perc_flaired_auth = n_flaired_auth / n_auth
    
    # Calculate the average sentiment and controversiality for each subset
    avg_rnfl_sent = [rnfl.sentiment.mean(), rnfl.controversiality.sum() / len(rnfl)]
    avg_nfl_sent = [nfl.sentiment.mean(), nfl.controversiality.sum() / len(nfl)]
    avg_self_sent = [selfc.sentiment.mean(), selfc.controversiality.sum() / len(selfc)]
    avg_other_sent = [other.sentiment.mean(), other.controversiality.sum() / len(other)]
    
    # Create a metadata dictionary with the calculated metrics
    metadata = dict(
        team=[subname],
        n_coms=[n_coms],
        perc_flaired_auth=[perc_flaired_auth],
        perc_rnfl_related=[perc_rnfl_related],
        perc_nfl_related=[perc_nfl_related],
        perc_self_related=[perc_self_related],
        perc_other_related=[perc_other_related],
        avg_rnfl_sent=[avg_rnfl_sent],
        avg_nfl_sent=[avg_nfl_sent],
        avg_self_sent=[avg_self_sent],
        avg_other_sent=[avg_other_sent]
    )
    
    return coms, metadata

def get_sub_edges(filename, sublist):
    """
    Construct edges between a given team subreddit and other subreddits based off of user interactions.

    Args:
    - filename (str): Path to the CSV file containing comments.
    - sublist (list): List of subreddit names to consider for relationships.

    Returns:
    - edges (list): List of tuples representing edges between subreddits in sublist.
                   Each tuple contains (source_subreddit, target_subreddit, *normalized metrics).
    """

    # Extract subname from the filename
    subname = filename.split('/')[-1].split('.')[0].split('_')[0]
    print(subname)
    # Dictionary to store edge information
    sub_edge_dict = dict()


    # Read comments
    coms = pd.read_csv(filename, lineterminator='\n').dropna(subset=['subreddit', 'body'])
    print('Number of comments:', len(coms))

    # Convert subreddit names to lowercase
    coms.subreddit = coms.subreddit.str.lower()

    # Filter comments to include only those in the specified sublist of subreddits
    coms = coms[coms.subreddit.isin(sublist)]

    # Create edges between subreddits in coms
    sub_edges = [(subname, com.subreddit) for ii, com in coms.iterrows()]

    # Populate sub_edge_dict with edge information
    for ii, edge in enumerate(sub_edges):
        if edge not in sub_edge_dict:
            # Initialize edge metrics if the edge is encountered for the first time
            sub_edge_dict[edge] = [1, coms.sentiment.iloc[ii], coms.controversiality.iloc[ii], coms.score.iloc[ii]]
        else:
            # increment metrics if the edge has been encountered before
            sub_edge_dict[edge][0] += 1
            sub_edge_dict[edge][1] += coms.sentiment.iloc[ii]
            sub_edge_dict[edge][2] += coms.controversiality.iloc[ii]
            sub_edge_dict[edge][3] += coms.score.iloc[ii]

    # Normalize based on how users interact on their own team's subreddit
    norm = sub_edge_dict[(subname, subname)][0] # volume of posts on own subreddit
    scorenorm = sub_edge_dict[(subname, subname)][3] # sentiment of posts on own subreddit

    edges = []

    # Compile normalized edge statistics
    for edge in sub_edge_dict:
        edges.append((
            edge[0],  # Source subreddit (subname)
            edge[1],  # Target subreddit
            sub_edge_dict[edge][0] / norm,  # Normalized frequency of interactions
            sub_edge_dict[edge][1] / sub_edge_dict[edge][0],  # Normalized average sentiment
            sub_edge_dict[edge][2] / sub_edge_dict[edge][0],  # Normalized average controversiality
            sub_edge_dict[edge][3] / (sub_edge_dict[edge][0] * scorenorm)  # Normalized average score
        ))

    return edges

def get_division_edges(sublist):
    """
    Generates the list of edges for a graph based on a list of sub-elements.

    Parameters:
    sublist (list): A list of elements (typically representing teams or divisions).

    Returns:
    edges (list): A list of edges where each edge is represented as a tuple 
                  containing information about the connection between two elements.
    """
    edges = []
    for sub in sublist:
        edges.extend(get_sub_edges(sub, sublist))
    return edges


def get_rivalry_graph(sublist, output='plots/tmp.png', ink_scale=1, norm_scale=3):
    """
    Generates a rivalry graph from a list of edges describing commenting traffic in NFL team subreddits.

    Parameters:
    sublist (list): A list of team subreddits
    output (str): Output path
    ink_scale (float): Scale factor for the ink used in rendering the graph. Default is 1.
    norm_scale (float): Normalization scale factor applied to edge weights. Default is 3.

    Returns:
    tuple: A tuple containing the graph-tool module (gt) and the rendered image.
    """
    # Generate raw edges from the sublist
    raw_edges = get_division_edges(sublist)

    # Normalize the edge weights based on the maximum weight
    norm = max([e[2] for e in raw_edges])

    # Map sub-elements to unique IDs
    sub2id = dict(zip(sublist, range(len(sublist))))
    id2sub = {v: k for k, v in sub2id.items()}

    # Create a list of edges with normalized weights
    edges = [(sub2id[e[0]], sub2id[e[1]], norm_scale * e[2] / norm, e[3]) for e in raw_edges]

    # Initialize a directed graph using graph-tool
    ug = gt.Graph(directed=True)
    eweight = ug.new_ep('double')  # Edge weight property
    sweight = ug.new_ep('double')  # Edge color property

    # Add edges to the graph and assign properties
    ug.add_edge_list(edges, eprops=[eweight, sweight])
    vname = ug.new_vertex_property("string")

    # Assign vertex names based on sublist
    ug.vp.vname = vname
    for k, name in sorted(id2sub.items()):
        v = ug.vertex(k)
        ug.vp.vname[v] = team2abbrev[name]

    # Draw the graph and save it as an image
    image = gt.graph_draw(
        ug,
        vertex_text=ug.vp.vname,
        edge_color=sweight,
        edge_pen_width=eweight,
        ink_scale=ink_scale,
        output=f'plots/{output}.png'
    )

    return gt, image

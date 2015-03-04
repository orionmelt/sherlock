# -*- coding: utf-8 -*-

import csv
import urllib2

# Feel free to use this CSV file. If running locally, change below 
# line to point to local file.
file_url = "https://www.dropbox.com/s/82c1ex12h1njtpv/subreddits.csv?dl=1"

subreddits = []
subreddits_file = urllib2.urlopen(file_url)

"""
CSV file has the following columns:
name            - Subreddit name
topic           - A maximum of 3 leveled topic. 
                  For instance, Entertainment > TV Shows > Sherlock.
topic_level1    - Level 1 topic. For instance, Entertainment.
topic_level2    - Level 2 topic. For instance, TV Shows.
topic_level3    - Level 2 topic. For instance, Sherlock.
default         - Y if default sub, blank otherwise.
ignore_text     - Y if text in sub needs to be ignored, blank otherwise.
sub_attribute   - An attribute we can derive from this subreddit. 
                  For instance, gender, religion, gadget, etc.
sub_value       - Value for the above attribute. 
                  For instance, male, atheism, iPhone, etc.

Currently, the CSV file has only data for the top ~2500 subreddits. 
All others will be classified under "Other".
"""

for (
    name, topic, topic_level1, topic_level2, topic_level3, 
    default, ignore_text, sub_attribute, sub_value
) in csv.reader(subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE):
    subreddit = {
        "name" : name,
        "topic_level1" : topic_level1,
        "topic_level2" : topic_level2,
        "topic_level3" : topic_level3,
        "default" : default,
        "ignore_text" : ignore_text,
        "attribute" : sub_attribute.lower(),
        "value" : sub_value.lower()
    }
    subreddits.append(subreddit)

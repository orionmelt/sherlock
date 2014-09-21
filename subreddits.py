# -*- coding: utf-8 -*-

import csv

subreddits=[]
with open("subreddits.csv") as subreddits_file:
	for rank, name, subscribers, interest, i1, i2, i3, default, autotagged, ignore_interest, ignore_comments, attribute, value in csv.reader(subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE):
		subreddit = {
			"name": name.lower(),
			"i1":i1,
			"i2":i2,
			"i3":i3,
			"default":default,
			"ignore_interest":ignore_interest,
			"ignore_comments":ignore_comments,
			"attribute":attribute.lower(),
			"value":value.lower()
		}
		subreddits.append(subreddit)
ignore_comments_subs 	= [s["name"] for s in subreddits if s["ignore_comments"]=="Y"]
default_subs 			= [s["name"] for s in subreddits if s["default"]=="Y"]
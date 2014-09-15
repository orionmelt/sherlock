# -*- coding: utf-8 -*-

import csv

ignore_subs = ['writingprompts','jokes','nosleep','photoshopbattles','circlejerk','adviceanimals']
subreddits=[]
with open("subreddits.csv") as subreddits_file:
	for rank, name, subscribers, interest, i1, i2, i3, autotagged, ignore_interest, ignore_comments, attribute, value in csv.reader(subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE):
		subreddit = {
			"name": name.lower(),
			"i1":i1,
			"i2":i2,
			"i3":i3,
			"ignore_interest":ignore_interest,
			"attribute":attribute.lower(),
			"value":value.lower()
		}
		subreddits.append(subreddit)

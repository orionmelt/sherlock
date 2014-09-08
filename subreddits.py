# -*- coding: utf-8 -*-

import csv

ignore_subs = ['writingprompts','jokes','nosleep','photoshopbattles','circlejerk','adviceanimals']
subreddits=[]
with open("subreddits.csv") as subreddits_file:
	for rank, name, subscribers, i1, i2, i3, ignore, pdk1, pdv1 in csv.reader(subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE):
		subreddit = {
			"name": name.lower(),
			"i1":i1,
			"i2":i2,
			"i3":i3,
			"pdk1":pdk1.lower(),
			"pdv1":pdv1.lower()
		}
		subreddits.append(subreddit)

# -*- coding: utf-8 -*-

import csv, urllib2

file_url = "https://www.dropbox.com/s/82c1ex12h1njtpv/subreddits.csv?dl=1"

subreddits=[]
subreddits_file = urllib2.urlopen(file_url)
for rank, name, subscribers, topic, topic_level1, topic_level2, topic_level3, default, autotagged, ignore_topic, ignore_text, attribute, value \
	in csv.reader(subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE):
	subreddit = {
		"name": name.lower(),
		"topic_level1":topic_level1,
		"topic_level2":topic_level2,
		"topic_level3":topic_level3,
		"default":default,
		"ignore_topic":ignore_topic,
		"ignore_text":ignore_text,
		"attribute":attribute.lower(),
		"value":value.lower()
	}
	subreddits.append(subreddit)
ignore_text_subs = [s["name"] for s in subreddits if s["ignore_text"]=="Y"]
default_subs = [s["name"] for s in subreddits if s["default"]=="Y"]

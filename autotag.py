import requests, json, sys, time, re, csv
from collections import Counter
from subreddits import subreddits

"""
Given a CSV file with topics for subreddits already seeded, attempts to automatically derive topics for the rest of the subreddits.
Some manual correction/more seeding may be required.

"""

if len(sys.argv) < 1:
	sys.exit("Usage: python autotags.py subreddits.csv")

headers = {
    'User-Agent': 'Categorize Subreddits v0.2 by /u/orionmelt'
}

input_subreddits_file=open(sys.argv[1])
output_subreddits_file=open(sys.argv[1]+".autotagged.csv", "wb")
input_subreddits_csv = csv.reader(input_subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE)
output_subreddits_csv = csv.writer(output_subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE)

for row in input_subreddits_csv:
	name, topic, t1, t2, t3, default, autotagged, ignore_topic, ignore_text, sub_attribute, sub_value = row
	if topic:
		# Already classified, just write to output file
		output_subreddits_csv.writerow(row)
	else:
		# Not yet classified
		topics = []
		related_subreddits = []
		time.sleep(2)
		url = r"http://www.reddit.com/r/%s/about.json" % name
		request = requests.get(url,headers=headers)
		response = request.json()

		print "Processing %s" % name
		
		description = None
		try:
			description = response["data"]["description_html"]
		except KeyError:
			pass
		if description:
			linked_subs = re.findall("/r/([a-zA-Z0-9]+)",description,flags=re.I)
			for l in set(linked_subs):
				classified_subreddit = ([s for s in subreddits if (s["name"]==l.lower())] or [None])[0]
				if classified_subreddit and classified_subreddit["topic_level1"]:
					topics.append(" > ".join([classified_subreddit["topic_level1"],classified_subreddit["topic_level2"]]))
			most_common_topic, times_mentioned = Counter(topics).most_common(1)[0] if Counter(topics).most_common(1) else (None,0)
			if times_mentioned>=3: # Tweak this number if necessary
				print "%s: %s (matched %d times)" % (name,most_common_topic,times_mentioned)
				add_topic="y" # For manual verification, uncomment following lines
				#add_topic = raw_input("Assign? ").lower()
				if add_topic=="y":
					topic = most_common_topic
					autotagged = "Y"
		row = (name, topic, t1, t2, t3, autotagged, ignore_topic, ignore_text, sub_attribute, sub_value)
		output_subreddits_csv.writerow(row)
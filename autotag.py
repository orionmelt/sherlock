import requests, json, sys, time, re, csv
from collections import Counter
from subreddits import subreddits

headers = {
    'User-Agent': 'Categorize Subreddits v0.2 by /u/orionmelt'
}

input_subreddits_file=open("subreddits.csv")
output_subreddits_file=open("subreddits_autotagged.csv", "wb")
input_subreddits_csv = csv.reader(input_subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE)
output_subreddits_csv = csv.writer(output_subreddits_file, delimiter=',', quoting=csv.QUOTE_NONE)

for row in input_subreddits_csv:
	rank, name, subscribers, interest, i1, i2, i3, autotagged, ignore_interest, ignore_comments, attribute, value = row
	if interest:
		# Already classified, just write to output file
		output_subreddits_csv.writerow(row)
	else:
		# Not yet classified
		interests = []
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
				if classified_subreddit and classified_subreddit["i1"]:
					interests.append(" > ".join([classified_subreddit["i1"],classified_subreddit["i2"]]))
			most_common_interest, times_mentioned = Counter(interests).most_common(1)[0] if Counter(interests).most_common(1) else (None,0)
			if times_mentioned>=1:
				print "%s: %s (matched %d times)" % (name,most_common_interest,times_mentioned)
				add_interest="y" # For manual verification, uncomment following lines
				#add = raw_input("Assign? ").lower()
				if add_interest=="y":
					interest = most_common_interest
					#level3 = raw_input("Level 3: ")
					#i3 = level3
					autotagged = "True"
		row = (rank, name, subscribers, interest, i1, i2, i3, autotagged, ignore_interest, ignore_comments, attribute, value)
		output_subreddits_csv.writerow(row)
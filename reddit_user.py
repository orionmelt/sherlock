# -*- coding: utf-8 -*-

import csv, datetime, re, requests, json, time
from subreddits import ignore_subs, subreddits
from collections import Counter
from data_extractor import DataExtractor

extractor = DataExtractor()

headers = {
    'User-Agent': 'Sherlock v0.1 by /u/orionmelt'
}

def printable_counter(sequence):
	return ["%s/%s" % (v,c) for v,c in Counter([v for v,s in sequence]).most_common()]

class RedditUser:
	username=None
	
	genders = []
	ages = []
	orientations = []
	family_members = []
	relationship_partners = []
	locations = []
	pets = []
	live_in = []
	grew_up_in = []
	tv_shows = []
	hobbies = []
	loves = []

	other_attributes = []	
	other_possessions = []
	other_actions = []

	commented_subreddits = []
	interests = []


	def __init__(self,username):
		self.username = username

	def __str__(self):
		text_rep =  "-"*80 + "\n"
		text_rep += "/u/%s:\n" % self.username
		text_rep += "-"*80 + "\n"
		text_rep += "gender: %s\n" % self.gender()
		text_rep += "age: %s\n" % str(printable_counter(self.ages))
		text_rep += "has lived in: %s\n" % str(printable_counter(self.live_in))
		text_rep += "grew up in: %s\n" % str(printable_counter(self.grew_up_in))
		text_rep += "orientation: %s\n" % str(printable_counter(self.orientations))
		text_rep += "family_members: %s\n" % str(printable_counter(self.family_members))
		text_rep += "relationship_partners: %s\n" % str(printable_counter(self.relationship_partners))
		text_rep += "locations: %s\n" % str(printable_counter(self.locations))
		text_rep += "pets: %s\n" % str(printable_counter(self.pets))
		text_rep += "hobbies: %s\n" % str(printable_counter(self.hobbies))
		text_rep += "tv shows: %s\n" % str(printable_counter(self.tv_shows))
		text_rep += "loves: %s\n" % str(printable_counter(self.loves))
		text_rep += "\n" + "-"*80 + "\n"
		text_rep += "info that may be useful but hasn't been processed yet\n"
		text_rep += "-"*80 + "\n"
		text_rep += "other attributes:\n%s\n\n" % str(printable_counter(self.other_attributes))
		text_rep += "other possessions:\n%s\n\n" % str(printable_counter(self.other_possessions))
		text_rep += "other actions:\n%s\n\n" % str(printable_counter(self.other_actions))
		
		text_rep += "commented subreddits: %s\n\n" % str(printable_counter(self.commented_subreddits))
		text_rep += "interests: %s\n" % str(Counter(self.interests).most_common())
		text_rep += "-"*80 + "\n"
		return text_rep
		
	def sanitize_comment(self, comment):
		body = " ".join([l for l in comment["body"].split("\n") if not l.startswith("&gt;")])
		body = re.sub(r"\b\".*\"\b","",body)
		return body

	def gender(self):
		if self.genders:
			((g,_),_) = Counter(self.genders).most_common(1)[0]
			return g
		else:
			return None

	def get_comments(self,limit=None):
		comments = []
		more_comments = True
		after = None
		base_url = r"http://www.reddit.com/user/%s/comments/.json?limit=100" % self.username
		url = base_url
		while more_comments:
			request = requests.get(url,headers=headers)
			response = request.json()

			# TODO - Error handling for user not found (404) and rate limiting (429)
			
			for child in response["data"]["children"]:
				body = child["data"]["body"].encode("ascii","ignore")
				created_utc = child["data"]["created_utc"]
				subreddit = child["data"]["subreddit"].encode("ascii","ignore").lower()
				link_id = child["data"]["link_id"].encode("ascii","ignore").lower()[3:]
				comment_id = child["data"]["id"].encode("ascii","ignore")
				#permalink = "http://www.reddit.com/r/%s/comments/%s/_/%s" % (subreddit, link_id, child["data"]["id"].encode("ascii","ignore"))
				comments.append({"body":body, "created_utc":created_utc, "subreddit":subreddit, "link_id":link_id, "comment_id":comment_id})

			after = response["data"]["after"]

			if after:
				url = base_url + "&after=%s" % after
				time.sleep(3)
			else:
				more_comments = False

		return comments

	def get_submissions(self,limit=None):
		return None

	def permalink(self, comment):
		subreddit = comment["subreddit"]
		link_id = comment["link_id"]
		comment_id = comment["comment_id"]
		return "http://www.reddit.com/r/%s/comments/%s/_/%s" % (subreddit, link_id, comment_id)

	def load_attributes(self, chunk, comment):
		if chunk["kind"] == "possession" and chunk["nouns"]:
			
			noun = chunk["nouns"][0]
			adjectives = (" ".join(chunk["adjectives"])).strip()
			nouns = (" ".join(chunk["nouns"])).strip()

			pet = extractor.pet_animal(noun)
			family_member = extractor.family_member(noun)
			relationship_partner = extractor.relationship_partner(noun)

			if pet:
				self.pets.append((pet, self.permalink(comment)))
			elif family_member:
				self.family_members.append((family_member, self.permalink(comment)))
			elif relationship_partner:
				self.relationship_partners.append((relationship_partner, self.permalink(comment)))
			else:
				self.other_possessions.append(((adjectives+" "+nouns).strip(), self.permalink(comment)))

		elif chunk["kind"] == "action":
			
			# TODO - Handle negative actions (such as I am not...), but for now:
			if "not" in chunk["adverbs"]:
				return

			adjectives = (" ".join(chunk["adjectives"])).strip()
			nouns = (" ".join(chunk["nouns"]).strip()).strip()

			# I am/was ...
			if len(chunk["verbs"])==1 and "be" in chunk["verbs"] and not chunk["prepositions"] and chunk["nouns"]:
				for noun in chunk["nouns"]:
					gender = extractor.gender(noun)
					orientation = extractor.orientation(noun)
					if gender:
						self.genders.append((gender, self.permalink(comment)))
					elif orientation:
						self.orientations.append((orientation,self.permalink(comment)))					
					elif not noun.endswith("ing") and "am" in chunk["actual_verbs"]: # Ignore gerunds for now, and include only "am" phrases
						self.other_attributes.append(((adjectives+" "+nouns).strip(), self.permalink(comment)))

			# I live(d) in ...
			elif "live" in chunk["verbs"] and "in" in chunk["prepositions"] and nouns:
				self.live_in.append((nouns, self.permalink(comment)))
			
			# I grew up in ...
			elif "grow" in chunk["verbs"] and "up" in chunk["prepositions"] and "in" in chunk["prepositions"] and nouns:
				self.grew_up_in.append((nouns, self.permalink(comment)))

			elif len(chunk["verbs"])==1 and "love" in chunk["verbs"] and nouns:
				self.loves.append(((adjectives+" "+nouns).strip(), self.permalink(comment)))

			elif nouns:
				verbs = (" ".join(chunk["verbs"])).strip()
				actual_verbs = (" ".join(chunk["actual_verbs"])).strip()
				prepositions = (" ".join(chunk["prepositions"])).strip()
				#other_actions = ((actual_verbs+" "+prepositions).strip() + " " + nouns).strip()
				other_actions = verbs
				self.other_actions.append((other_actions, self.permalink(comment)))


	def derive_attributes(self):
		if not self.genders and "wife" in [v for v,s in self.relationship_partners]:
			self.genders.append(("male","derived"))
		elif not self.genders and "husband" in [v for v,s in self.relationship_partners]:
			self.genders.append(("female","derived"))

	def process_comment(self,comment):
		self.commented_subreddits.append((comment["subreddit"],self.permalink(comment)))

		subreddit = ([s for s in subreddits if s["name"]==comment["subreddit"]] or [None])[0]
		if subreddit:
			if subreddit["i1"].lower()=="location":
				self.locations.append((subreddit["i3"], "derived"))
			elif subreddit["i1"].lower()=="entertainment" and subreddit["i2"].lower()=="tv":
				self.tv_shows.append((subreddit["i3"], "derived"))
			elif subreddit["i1"].lower()=="hobbies":
				self.hobbies.append((subreddit["i3"] or subreddit["i2"], "derived"))
			else:
				self.interests.append(subreddit["i3"] or subreddit["i2"] or subreddit["i1"])

		if comment["subreddit"].lower() in ignore_subs:
			return False

		comment["body"] = self.sanitize_comment(comment)

		if not re.search(r"\b(i|my)\b",comment["body"],re.I):
			return False
		
		for chunk in extractor.extract_chunks(comment["body"]):
			self.load_attributes(chunk, comment)
		
		return True

	def process_all_comments(self):
		for comment in self.get_comments():
			self.process_comment(comment)

		self.derive_attributes()

	def save_comments_to_file(self):
		comments_file = csv.writer(open("data/comments_%s.csv" % self.username, "wb"), quoting=csv.QUOTE_ALL)

		for comment in self.get_comments():
			body = self.sanitize_comment(comment)
			comments_file.writerow([comment["subreddit"], body, comment["link_id"], comment["comment_id"], comment["created_utc"]])

	def process_comments_from_file(self):
		comments_file = csv.reader(open("data/comments_%s.csv" % self.username))
		for line in comments_file:
			(subreddit, body, link_id, comment_id, created_utc) = line
			comment = {"subreddit":subreddit.lower(), "body":body, "link_id":link_id, "comment_id":comment_id, "created_utc":created_utc}
			self.process_comment(comment)

		self.derive_attributes()

# -*- coding: utf-8 -*-

import csv, datetime, re, requests, json, time, sys, pytz
from subreddits import subreddits, ignore_comments_subs, default_subs
from collections import Counter
from itertools import groupby
from data_extractor import DataExtractor

extractor = DataExtractor()

headers = {
    'User-Agent': 'Sherlock v0.1 by /u/orionmelt'
}

def most_common(sequence):
	return "\n".join(["%s/%s" % (v,c) for v,c in Counter([v for v,s in sequence]).most_common()])


class RedditUser:
	username=None
	signup_date = None
	link_karma = 0
	comment_karma = 0

	activity_by_month = []
	activity_by_weekday = []
	activity_by_hour = []
	activity_by_subreddits = []
	
	earliest_comment = None
	latest_comment = None
	worst_comment = None
	best_comment = None

	earliest_submission = None
	latest_submission = None
	worst_submission = None
	best_submission = None

	genders = []
	ages = []
	orientations = []
	family_members = []
	relationship_partners = []
	locations = []
	pets = []
	
	
	core_places_lived = []
	more_places_lived = []

	core_places_grew = []
	more_places_grew = []
	
	tv_shows = []
	hobbies = []
	misc_favorites = []

	core_attributes = []
	more_attributes = []

	core_possessions = []
	more_possessions = []
	
	core_actions = []
	more_actions = []

	commented_subreddits = []
	comment_interests = []
	commented_subreddit_attributes = []

	submitted_subreddits = []
	submit_interests = []
	submitted_subreddit_attributes = []

	sentiments = []

	corpus = ""

	# Skip if any of these is the *only* attribute
	skip_lone_attributes = 	[
								"fan","expert"
							]

	skip_attributes = 		[
								"supporter","believer","gender","backer","sucker","chapter","passenger","super","water","sitter",
								"killer","stranger","monster","leather","holder","creeper","shower","member","wonder","hungover",
								"sniper","silver","beginner","lurker","loser","number",
								"door","liquor",
								"year","ear","liar",
								"rapist","racist",
								"satan","batman","veteran",
								"hypocrite","candidate",
							]

	include_attributes = 	[
								"geek","nerd","nurse","cook","student","consultant","mom","dad","marine","chef","sophomore","catholic",
								"person","enthusiast","fanboy","player","advocate", # These make sense only when accompanied by at least another noun
							]

	include_attribute_endings = ("er","or","ar","ist","an","ert","ese","te")
	exclude_attribute_endings = ("ing","fucker")


	def __init__(self,username):
		self.username = username
		self.signup_date, self.link_karma, self.comment_karma = self.get_about()
		
		now = datetime.datetime.now(tz=pytz.utc)
		today = now.date()

		signup_date = self.signup_date.date()

		self.activity_by_month = [{"date":(y,m), "comments":0, "submissions":0, "comment_karma":0, "submission_karma":0} \
								  for (y,m) in sorted(list(set([((today-datetime.timedelta(days=x)).year,(today-datetime.timedelta(days=x)).month) for x in range(0,(today-signup_date).days)])))]
		
		self.activity_by_hour = [{"hour":h, "comments":0, "submissions":0, "comment_karma":0, "submission_karma":0} for h in range(0,24)]

		self.activity_by_weekday = [{"weekday":w, "comments":0, "submissions":0, "comment_karma":0, "submission_karma":0} for w in range(0,7)]


	def __str__(self):
		text_rep =  "-"*80 + "\n"
		text_rep += "/u/%s:\n" % self.username
		text_rep += "-"*80 + "\n"

		tc = self.total_comments()
		tcd = self.total_default_comments()
		try:
			tcdp = tcd*100.0/tc
		except ZeroDivisionError:
			tcdp = 0.0
		text_rep += "Comment stats:\n"
		text_rep += "Total comments           : %d\n" % tc
		text_rep += "Total default comments   : %d\n" % tcd
		text_rep += "%% of default comments    : %.2f\n" % tcdp
		text_rep += "\n"


		ts = self.total_submissions()
		tsd = self.total_default_submissions()
		try:
			tsdp = tsd*100.0/ts
		except ZeroDivisionError:
			tsdp = 0.0
		text_rep += "Submission stats:\n"
		text_rep += "Total submissions         : %d\n" % ts
		text_rep += "Total default submissions : %d\n" % tsd
		text_rep += "%% of default submissions  : %.2f\n" % tsdp
		text_rep += "\n"

		text_rep += "gender: %s\n\n" % self.gender()
		if self.ages:
			text_rep += "age: %s\n\n" % most_common(self.ages)
		
		if self.core_places_lived:
			text_rep += "core places lived:\n%s\n\n" % most_common(self.core_places_lived)
		if self.more_places_lived:
			text_rep += "more places lived:\n%s\n\n" % most_common(self.more_places_lived)
		
		if self.core_places_grew:
			text_rep += "core places grew:\n%s\n\n" % most_common(self.core_places_grew)
		if self.more_places_grew:
			text_rep += "more places grew:\n%s\n\n" % most_common(self.more_places_grew)
		
		if self.orientations:
			text_rep += "orientation:\n%s\n\n" % most_common(self.orientations)
		if self.family_members:
			text_rep += "family_members:\n%s\n\n" % most_common(self.family_members)
		if self.relationship_partners:
			text_rep += "relationship_partners:\n%s\n\n" % most_common(self.relationship_partners)
		if self.locations:
			text_rep += "locations:\n%s\n\n" % most_common(self.locations)
		if self.pets:
			text_rep += "pets:\n%s\n\n" % most_common(self.pets)
		if self.hobbies:
			text_rep += "hobbies:\n%s\n\n" % most_common(self.hobbies)
		if self.tv_shows:
			text_rep += "tv shows:\n%s\n\n" % most_common(self.tv_shows)
		if self.misc_favorites:
			text_rep += "misc favorites:\n%s\n\n" % most_common(self.misc_favorites)
		
		text_rep += "\n" + "-"*80 + "\n"
		text_rep += "info that may be useful but hasn't been processed yet\n"
		text_rep += "-"*80 + "\n"
		
		if self.core_attributes:
			text_rep += "core attributes:\n%s\n\n" % most_common(self.core_attributes)
		if self.more_attributes:
			text_rep += "more attributes:\n%s\n\n" % most_common(self.more_attributes)
		if self.core_possessions:
			text_rep += "core possessions:\n%s\n\n" % most_common(self.core_possessions)	
		if self.more_possessions:
			text_rep += "more possessions:\n%s\n\n" % most_common(self.more_possessions)
		if self.core_actions:
			text_rep += "core actions:\n%s\n\n" % most_common(self.core_actions)
		if self.more_actions:
			text_rep += "more actions:\n%s\n\n" % most_common(self.more_actions)
		
		if self.commented_subreddits:
			#text_rep += "commented subreddits:\n%s\n\n" % most_common(self.commented_subreddits)
			text_rep += "comment interests:\n%s\n\n" % most_common(self.comment_interests)
			text_rep += "commented subreddit attributes:\n%s\n\n" % most_common(self.commented_subreddit_attributes)

		if self.submitted_subreddits:
			#text_rep += "submitted subreddits:\n%s\n\n" % most_common(self.submitted_subreddits)
			text_rep += "submit interests:\n%s\n\n" % most_common(self.submit_interests)
			text_rep += "submitted subreddit attributes:\n%s\n\n" % most_common(self.submitted_subreddit_attributes)
		
		text_rep += "Average sentiment: %.3f\n" % (sum(float(p) for p,_ in self.sentiments)/len(self.sentiments))
		text_rep += "-"*80 + "\n"
		
		return text_rep

		
	def sanitize_comment(self, comment):
		body = " ".join([l for l in comment["body"].split("\n") if not l.startswith("&gt;")])
		substitutions = [
			(r"\[(.*?)\]\((.*?)\)", r""), 	# Remove links from Markdown
			(r"[\"\“](.*?)[\"\”]", r""), 	# Remove text within quotes
			(r" \'(.*?)\ '", r""),			# Remove text within quotes
			(r"\.+", r"."), 				# Remove ellipses
			(r"\(.*?\)", r""), 				# Remove text within round brackets
			(r"&amp;",r"&"),				# Decode HTML entities
			(r"http.?:\S+\b",r" ")			# Remove URLs
		]
		for original, rep in substitutions:
			body = re.sub(original, rep, body, flags=re.I)
		return body


	def stats(self):
		signup_date, link_karma, comment_karma = self.get_about()

		total_comments = self.total_comments()
		total_default_comments = self.total_default_comments()
		
		total_submissions = self.total_submissions()
		total_default_submissions = self.total_default_submissions()

		print "Stats:"
		print "Total comments: %d" % total_comments
		print "Total default comments: %d" % total_default_comments
		print "Total submissions: %d" % total_submissions
		print "Total default submission: %d" % total_default_submissions
		
		activity_by_month = []
		for d in self.activity_by_month:
			activity_by_month.append({
				"date":"%d-%02d-01"%(d["date"][0],d["date"][1]), 
				"comments":d["comments"], 
				"submissions":d["submissions"],
				"comment_karma":d["comment_karma"],
				"submission_karma":d["submission_karma"]
			})

		activity_by_hour = []
		for h in self.activity_by_hour:
			activity_by_hour.append({
				"hour":h["hour"], 
				"comments":h["comments"], 
				"submissions":h["submissions"],
				"comment_karma":h["comment_karma"],
				"submission_karma":h["submission_karma"]
			})

		weekdays = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
		
		activity_by_weekday = []
		for w in self.activity_by_weekday:
			activity_by_weekday.append({
				"weekday":weekdays[w["weekday"]], 
				"comments":w["comments"], 
				"submissions":w["submissions"],
				"comment_karma":w["comment_karma"],
				"submission_karma":w["submission_karma"]
			})

		activity_by_subreddits = {"name":"All", "children":[]}
		for (name,[com,comk]) in \
			[(s,[sum(x) for x in zip(*[(1,r[2]) for r in group])]) for s, group in groupby(sorted(self.commented_subreddits, key=lambda x: x[0]),lambda x: x[0])]:
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			i1 = None
			if subreddit:
				i1 = subreddit["i1"]
			else:
				i1 = "Other"
			if activity_by_subreddits["children"] and i1 in [i["name"] for i in activity_by_subreddits["children"]]:
				for interest in activity_by_subreddits["children"]:
					if interest["name"]==i1:
						interest["children"].append({
							"name":name,
							"comments":com,
							"comment_karma":comk,
							"submissions":0,
							"submission_karma":0
						})
						break
			else:
				activity_by_subreddits["children"].append({"name":i1, "children":[{
					"name":name,
					"comments":com,
					"comment_karma":comk,
					"submissions":0,
					"submission_karma":0
				}]})

		for (name,[sub,subk]) in \
			[(s,[sum(x) for x in zip(*[(1,r[2]) for r in group])]) for s, group in groupby(sorted(self.submitted_subreddits, key=lambda x: x[0]),lambda x: x[0])]:
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			if subreddit:
				i1 = subreddit["i1"]
			else:
				i1 = "Other"
			if activity_by_subreddits["children"] and i1 in [i["name"] for i in activity_by_subreddits["children"]]:
				for interest in activity_by_subreddits["children"]:
					if interest["name"]==i1:
						for x, s in enumerate(interest["children"]):
							if s["name"] == name:
								s["submissions"]=sub
								s["submission_karma"]=subk
								interest["children"][x]=s
								break
						break
			else:
				activity_by_subreddits["children"].append({"name":i1, "children":[{
					"name":name,
					"comments":0,
					"comment_karma":0,
					"submissions":sub,
					"submission_karma":subk
				}]})

		json_data = {
			"about": {
				"signup_date": signup_date.strftime("%m/%d/%Y"),
				"link_karma": link_karma,
				"comment_karma": comment_karma,
				"comments": {
					"total": total_comments,
					"default": total_default_comments,
					"best": {
						"body":self.sanitize_comment(self.best_comment),
						"permalink":self.permalink(self.best_comment)
					},
					"worst": {
						"body":self.sanitize_comment(self.worst_comment),
						"permalink":self.permalink(self.worst_comment)
					}
				},
				"submissions": {
					"total": total_submissions,
					"default": total_default_submissions,
					"best": {
						"title":self.best_submission["title"],
						"permalink":self.best_submission["permalink"]
					},
					"worst": {
						"title":self.worst_submission["title"],
						"permalink":self.worst_submission["permalink"]
					}
				}
			},
			"activity": {
				"month": activity_by_month,
				"hour": activity_by_hour,
				"weekday": activity_by_weekday,
				"subreddits": activity_by_subreddits
			}
		}

		return json.dumps(json_data)


	def total_comments(self):
		return sum([c for _,c in Counter([v for v,_,_ in self.commented_subreddits]).most_common()])


	def total_default_comments(self):
		return sum([c for _,c in Counter([v for v,_,_ in self.commented_subreddits if v in default_subs]).most_common()])


	def total_submissions(self):
		return sum([c for _,c in Counter([v for v,_,_ in self.submitted_subreddits]).most_common()])


	def total_default_submissions(self):
		return sum([c for _,c in Counter([v for v,_,_ in self.submitted_subreddits if v in default_subs]).most_common()])


	def gender(self):
		if self.genders:
			(g,_) = Counter([g for g,_ in self.genders]).most_common(1)[0]
			return g
		else:
			return None


	def get_about(self):
		url = r"http://www.reddit.com/user/%s/about.json" % self.username
		response = requests.get(url,headers=headers)
		response_json = response.json()
		return (datetime.datetime.fromtimestamp(response_json["data"]["created_utc"],tz=pytz.utc),response_json["data"]["link_karma"],response_json["data"]["comment_karma"])


	def get_comments(self,limit=None):
		comments = []
		more_comments = True
		after = None
		base_url = r"http://www.reddit.com/user/%s/comments/.json?limit=100" % self.username
		url = base_url
		while more_comments:
			response = requests.get(url,headers=headers)
			response_json = response.json()

			# TODO - Error handling for user not found (404) and rate limiting (429)
			
			for child in response_json["data"]["children"]:
				subreddit = child["data"]["subreddit"].encode("ascii","ignore").lower()
				body = child["data"]["body"].encode("ascii","ignore")
				link_id = child["data"]["link_id"].encode("ascii","ignore").lower()[3:]
				comment_id = child["data"]["id"].encode("ascii","ignore")
				created_utc = child["data"]["created_utc"]

				# Following attributes not in batch1 files
				score = child["data"]["score"]
				edited = child["data"]["edited"]
				top_level = True if child["data"]["parent_id"].startswith("t3") else False
				
				comments.append({
					"subreddit":subreddit,
					"body":body,
					"link_id":link_id,
					"comment_id":comment_id,
					"created_utc":created_utc,
					"score":int(score),
					"edited":edited,
					"top_level":top_level
				})

			after = response_json["data"]["after"]

			if after:
				url = base_url + "&after=%s" % after
				time.sleep(2)
			else:
				more_comments = False

		return comments


	def get_submissions(self,limit=None):
		submissions = []
		more_submissions = True
		after = None
		base_url = r"http://www.reddit.com/user/%s/submitted/.json?limit=100" % self.username
		url = base_url
		while more_submissions:
			response = requests.get(url,headers=headers)
			response_json = response.json()

			# TODO - Error handling for user not found (404) and rate limiting (429)
			
			for child in response_json["data"]["children"]:
				subreddit = child["data"]["subreddit"].encode("ascii","ignore").lower()
				title = child["data"]["title"].encode("ascii","ignore")
				url = child["data"]["url"].encode("ascii","ignore").lower()
				selftext = child["data"]["selftext"].encode("ascii","ignore").lower()
				permalink = "http://www.reddit.com"+child["data"]["permalink"].encode("ascii","ignore").lower()
				created_utc = child["data"]["created_utc"]
				score = child["data"]["score"]

				submissions.append({
					"subreddit":subreddit, 
					"title":title, "url":url, 
					"selftext":selftext, 
					"permalink":permalink, 
					"created_utc":created_utc, 
					"score":int(score)
				})

			after = response_json["data"]["after"]

			if after:
				url = base_url + "&after=%s" % after
				time.sleep(2)
			else:
				more_submissions = False

		return submissions


	def permalink(self, comment):
		subreddit = comment["subreddit"]
		link_id = comment["link_id"]
		comment_id = comment["comment_id"]
		return "http://www.reddit.com/r/%s/comments/%s/_/%s" % (subreddit, link_id, comment_id)


	def load_attributes(self, chunk, comment):
		if chunk["kind"] == "possession" and chunk["noun_phrase"]:
			noun_phrase = chunk["noun_phrase"]
			noun_phrase_text = " ".join([w for w,t in noun_phrase])
			norm_nouns = " ".join([extractor.normalize(w,t) for w,t in noun_phrase if t.startswith("N")])
			
			noun = next((w for w,t in noun_phrase if t.startswith("N")),None)
			if noun:
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
					self.more_possessions.append((norm_nouns, self.permalink(comment)))

		elif chunk["kind"] == "action" and chunk["verb_phrase"]:
			verb_phrase = chunk["verb_phrase"]
			verb_phrase_text = " ".join([w for w,t in verb_phrase])

			norm_adverbs = [extractor.normalize(w,t) for w,t in verb_phrase if t.startswith("RB")]
			adverbs = [w.lower() for w,t in verb_phrase if t.startswith("RB")]

			norm_verbs = [extractor.normalize(w,t) for w,t in verb_phrase if t.startswith("V")]
			verbs = [w.lower() for w,t in verb_phrase if t.startswith("V")]

			prepositions = [w for w,t in chunk["prepositions"]]

			noun_phrase = chunk["noun_phrase"]

			noun_phrase_text = " ".join([w for w,t in noun_phrase if t not in ["DT"]])
			norm_nouns = [extractor.normalize(w,t) for w,t in noun_phrase if t.startswith("N")]
			proper_nouns = [w for w,t in noun_phrase if t=="NNP"]
			determiners = [extractor.normalize(w,t) for w,t in noun_phrase if t.startswith("DT")]

			prep_noun_phrase = chunk["prep_noun_phrase"]
			prep_noun_phrase_text = " ".join([w for w,t in prep_noun_phrase])
			pnp_prepositions = [w.lower() for w,t in prep_noun_phrase if t in ["TO","IN"]]
			pnp_norm_nouns = [extractor.normalize(w,t) for w,t in prep_noun_phrase if t.startswith("N")]
			pnp_determiners = [extractor.normalize(w,t) for w,t in prep_noun_phrase if t.startswith("DT")]

			full_noun_phrase = (noun_phrase_text + " " + prep_noun_phrase_text).strip()

			# TODO - Handle negative actions (such as I am not...), but for now:
			if any(w in ["never","no","not","nothing"] for w in norm_adverbs+determiners):
				return

			# I am/was ...
			if len(norm_verbs)==1 and "be" in norm_verbs and not prepositions and noun_phrase:
				# Ignore gerund nouns for now
				if "am" in verbs and any(n.endswith("ing") for n in norm_nouns):
					self.more_attributes.append((full_noun_phrase, self.permalink(comment)))
					return

				attribute = []
				for noun in norm_nouns:
					gender = None
					orientation = None
					if "am" in verbs:
						gender = extractor.gender(noun)
						orientation = extractor.orientation(noun)
					if gender:
						self.genders.append((gender, self.permalink(comment)))
					elif orientation:
						self.orientations.append((orientation,self.permalink(comment)))
					# Include only "am" phrases
					elif "am" in verbs: 
						attribute.append(noun)
				
				if attribute and \
					(
						(
							# Include only attributes that end in predefined list of endings...
							any(a.endswith(self.include_attribute_endings) for a in attribute)
							and
							# And exclude...
							not
							(
								# ...certain lone attributes
								(len(attribute)==1 and attribute[0] in self.skip_lone_attributes and not pnp_norm_nouns)
								or
								# ...predefined skip attributes
								any(a in attribute for a in self.skip_attributes)
								or
								# ...attributes that end in predefined list of endings
								any(a.endswith(self.exclude_attribute_endings) for a in attribute)
							)
						)
						or
						(
							# And include special attributes with different endings
							any(a in attribute for a in self.include_attributes)
						)
					):
					self.core_attributes.append((full_noun_phrase, self.permalink(comment)))
				elif attribute:
					self.more_attributes.append((full_noun_phrase, self.permalink(comment)))

			# I live(d) in ...
			elif "live" in norm_verbs and prepositions and norm_nouns:
				if any(p in ["in","near","by"] for p in prepositions) and proper_nouns:
					self.core_places_lived.append((" ".join(prepositions) + "-" + noun_phrase_text, self.permalink(comment)))
				else:
					self.more_places_lived.append((" ".join(prepositions) + "-" + noun_phrase_text, self.permalink(comment)))
			
			# I grew up in ...
			elif "grow" in norm_verbs and "up" in prepositions and norm_nouns:
				if any(p in ["in","near","by"] for p in prepositions) and proper_nouns:
					self.core_places_grew.append((" ".join(prepositions) + "-" + noun_phrase_text, self.permalink(comment)))
				else:
					self.more_places_grew.append((" ".join(prepositions) + "-" + noun_phrase_text, self.permalink(comment)))

			elif len(norm_verbs)==1 and "prefer" in norm_verbs and norm_nouns and not determiners and not prepositions:
				self.misc_favorites.append((full_noun_phrase, self.permalink(comment)))

			elif norm_nouns:
				more_actions = " ".join(norm_verbs)
				self.more_actions.append((more_actions, self.permalink(comment)))


	def derive_attributes(self):
		if not self.genders and "wife" in [v for v,s in self.relationship_partners]:
			self.genders.append(("male","derived"))
		elif not self.genders and "husband" in [v for v,s in self.relationship_partners]:
			self.genders.append(("female","derived"))


	def process_comment(self, comment):
		self.commented_subreddits.append((comment["subreddit"],self.permalink(comment),comment["score"]))
		self.corpus += comment["body"]

		comment_timestamp = datetime.datetime.fromtimestamp(comment["created_utc"],tz=pytz.utc)
		
		for i,d in enumerate(self.activity_by_month):
			if d["date"]==(comment_timestamp.date().year, comment_timestamp.date().month):
				d["comments"]+=1
				d["comment_karma"]+=comment["score"]
				self.activity_by_month[i]=d
				break

		for i,h in enumerate(self.activity_by_hour):
			if h["hour"]==comment_timestamp.hour:
				h["comments"]+=1
				h["comment_karma"]+=comment["score"]
				self.activity_by_hour[i]=h
				break

		for i,w in enumerate(self.activity_by_weekday):
			if w["weekday"]==comment_timestamp.date().weekday():
				w["comments"]+=1
				w["comment_karma"]+=comment["score"]
				self.activity_by_weekday[i]=w
				break

		if comment["score"] > self.best_comment["score"]:
			self.best_comment = comment
		elif comment["score"] < self.worst_comment["score"]:
			self.worst_comment = comment

		subreddit = ([s for s in subreddits if s["name"]==comment["subreddit"]] or [None])[0]

		if subreddit:
			if subreddit["i1"].lower()=="location":
				self.locations.append((subreddit["i3"], self.permalink(comment)))
			elif subreddit["i1"].lower()=="entertainment" and subreddit["i2"].lower()=="tv" and subreddit["i3"]:
				self.tv_shows.append((subreddit["i3"], self.permalink(comment)))
			elif subreddit["i1"].lower()=="hobbies":
				self.hobbies.append((subreddit["i3"] or subreddit["i2"], self.permalink(comment)))
			
			if subreddit["ignore_interest"]=="Y":
				self.comment_interests.append(("Ignored",self.permalink(comment)))
			else:
				self.comment_interests.append((subreddit["i1"]+">"+subreddit["i2"]+">"+subreddit["i3"], self.permalink(comment)))

			if subreddit["attribute"]:
				self.commented_subreddit_attributes.append((subreddit["attribute"]+":::"+subreddit["value"], self.permalink(comment)))
		else:
			self.comment_interests.append(("Unkown", self.permalink(comment)))

		if comment["subreddit"].lower() in ignore_comments_subs:
			return False

		comment["body"] = self.sanitize_comment(comment)		

		if not re.search(r"\b(i|my)\b",comment["body"],re.I):
			return False
		
		(chunks, sentiments) = extractor.extract_chunks(comment["body"])
		self.sentiments += sentiments

		for chunk in chunks:
			self.load_attributes(chunk, comment)
		
		return True


	def process_submission(self, submission):
		self.submitted_subreddits.append((submission["subreddit"], submission["permalink"], submission["score"]))

		submission_timestamp = datetime.datetime.fromtimestamp(submission["created_utc"],tz=pytz.utc)

		for i,d in enumerate(self.activity_by_month):
			if d["date"]==(submission_timestamp.date().year, submission_timestamp.date().month):
				d["submissions"]+=1
				d["submission_karma"]+=submission["score"]
				self.activity_by_month[i]=d
				break

		for i,h in enumerate(self.activity_by_hour):
			if h["hour"]==submission_timestamp.hour:
				h["submissions"]+=1
				h["submission_karma"]+=submission["score"]
				self.activity_by_hour[i]=h
				break

		for i,w in enumerate(self.activity_by_weekday):
			if w["weekday"]==submission_timestamp.date().weekday():
				w["submissions"]+=1
				w["submission_karma"]+=submission["score"]
				self.activity_by_weekday[i]=w
				break

		if submission["score"] > self.best_submission["score"]:
			self.best_submission = submission
		elif submission["score"] < self.worst_submission["score"]:
			self.worst_submission = submission
		
		subreddit = ([s for s in subreddits if (s["name"]==submission["subreddit"] and s["ignore_interest"]!="Ignore")] or [None])[0]

		if subreddit:
			if subreddit["i1"].lower()=="location":
				self.locations.append((subreddit["i3"], submission["permalink"]))
			elif subreddit["i1"].lower()=="entertainment" and subreddit["i2"].lower()=="tv" and subreddit["i3"]:
				self.tv_shows.append((subreddit["i3"], submission["permalink"]))
			elif subreddit["i1"].lower()=="hobbies":
				self.hobbies.append((subreddit["i3"] or subreddit["i2"], submission["permalink"]))
			else:
				self.submit_interests.append((subreddit["i1"]+">"+subreddit["i2"]+">"+subreddit["i3"], submission["permalink"]))

			if subreddit["attribute"]:
				self.submitted_subreddit_attributes.append((subreddit["attribute"]+":::"+subreddit["value"], submission["permalink"]))
		
		return True


	def process_all_comments(self):
		comments = self.get_comments()
		
		self.earliest_comment = comments[-1]
		self.latest_comment = comments[0]

		self.best_comment = comments[0]
		self.worst_comment = comments[0]

		for comment in comments:
			self.process_comment(comment)

		self.derive_attributes()


	def process_all_submissions(self):
		submissions = self.get_submissions();

		self.earliest_submission = submissions[-1]
		self.latest_submission = submissions[0]

		self.best_submission = submissions[0]
		self.worst_submission = submissions[0]

		for submission in self.get_submissions():
			self.process_submission(submission)


	def save_comments_to_file(self):
		comments_file = csv.writer(open("data/comments_%s.csv" % self.username, "wb"), quoting=csv.QUOTE_ALL)

		for comment in self.get_comments():
			body = self.sanitize_comment(comment)
			comments_file.writerow([comment["subreddit"], body, comment["link_id"], comment["comment_id"], comment["created_utc"]])


	def process_comments_from_file(self):
		c = 0
		comments_file = csv.reader(open("data/comments_%s.csv" % self.username))
		for line in comments_file:
			sys.stdout.write("\rProcessing comment # %d" % c),
			sys.stdout.flush()
			c += 1
			(subreddit, body, link_id, comment_id, created_utc) = line
			comment = {"subreddit":subreddit.lower(), "body":body, "link_id":link_id, "comment_id":comment_id, "created_utc":created_utc}
			self.process_comment(comment)

		self.derive_attributes()

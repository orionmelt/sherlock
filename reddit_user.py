# -*- coding: utf-8 -*-

import csv, datetime, re, requests, json, time, sys, pytz
from collections import Counter
from itertools import groupby
from urlparse import urlparse
try:
	from subreddits import subreddits, ignore_text_subs, default_subs
except:
	pass
try:
	from data_extractor import DataExtractor
except:
	pass

extractor = DataExtractor()


class Util:
	@staticmethod
	def sanitize_text(text):
		_text = " ".join([l for l in text.split("\n") if not l.startswith("&gt;")])
		substitutions = [
			(r"\[(.*?)\]\((.*?)\)", r""), 	# Remove links from Markdown
			(r"[\"](.*?)[\"]", r""), 		# Remove text within quotes
			(r" \'(.*?)\ '", r""),			# Remove text within quotes
			(r"\.+", r". "), 				# Remove ellipses
			(r"\(.*?\)", r""), 				# Remove text within round brackets
			(r"&amp;",r"&"),				# Decode HTML entities
			(r"http.?:\S+\b",r" ")			# Remove URLs
		]
		for pattern, replacement in substitutions:
			_text = re.sub(pattern, replacement, _text, flags=re.I)
		return _text

	@staticmethod
	def coalesce(l):
		l = [x for x in l if x.lower()!="generic"]
		return next(iter(l[::-1]), "")

	@staticmethod
	def ago(days):
		y = days/365 if days>365 else 0
		m = (days-y*365)/31 if days>30 else 0
		d = (days-m*31-y*365)
		yy = str(y) + " year" if y else ""
		if y>1:
			yy+="s"
		mm = str(m) + " month" if m else ""
		if m>1:
			mm+="s"
		dd = str(d) + " day"
		if d>1 or d==0:
			dd+="s"
		return (yy+" "+mm+" "+dd).strip()


# Base class for comments and submissions
class Post(object):
	# Post id
	id = None
	# Subreddit in which this comment or submission was posted
	subreddit = None
	# For comments, the comment body and for submissions, the self-text
	text = None
	# UTC timestamp when post was created
	created_utc = None
	# Post score
	score = 0
	# Permalink to post
	permalink = None
	# Gilded
	gilded = 0

	def __init__(self, id, subreddit, text, created_utc, score, permalink, gilded):
		self.id = id
		self.subreddit = subreddit
		self.text = text
		self.created_utc = created_utc
		self.score = score
		self.permalink = permalink
		self.gilded = gilded
		

class Comment(Post):
	# Link ID where comment was posted
	submission_id = None
	# Edited flag
	edited = False
	# Top-level flag
	top_level = False

	def __init__(self, id, subreddit, text, created_utc, score, permalink, submission_id, edited, top_level, gilded):
		super(Comment,self).__init__(id, subreddit, text, created_utc, score, permalink, gilded)
		self.submission_id = submission_id
		self.edited = edited
		self.top_level = top_level


class Submission(Post):
	# Submission link URL
	url = None
	# Submission title
	title = None
	# Self post?
	is_self = None
	# Domain
	domain = None

	def __init__(self, id, subreddit, text, created_utc, score, permalink, url, title, is_self, gilded, domain):
		super(Submission,self).__init__(id, subreddit, text, created_utc, score, permalink, gilded)
		self.url = url
		self.title = title
		self.is_self = is_self
		self.domain = domain


class RedditUser:
	# Constants
	MIN_THRESHOLD = 3
	HEADERS = {
	    'User-Agent': 'Sherlock v0.1 by /u/orionmelt'
	}

	IMAGE_DOMAINS = ["imgur.com", "flickr.com"]
	VIDEO_DOMAINS = ["youtube.com", "youtu.be", "vimeo.com", "liveleak.com"]

	IMAGE_EXTENSIONS = ["jpg", "png", "gif", "bmp"]

	# Basics
	username=None
	comments = []
	submissions = []

	# About
	signup_date = None
	first_post_date = None
	signup_date_text = None
	first_post_date_text = None
	link_karma = 0
	comment_karma = 0

	# Comment stats
	earliest_comment = None
	latest_comment = None
	best_comment = None
	worst_comment = None
	
	# Submission stats
	earliest_submission = None
	latest_submission = None
	best_submission = None
	worst_submission = None

	metrics = {
		"date": [],
		"weekday": [],
		"hour": [],
		"subreddit": [],
		"submissions": {
			"name": "All",
			"children": [
				{"name": "Self", "children":[]},
				{"name": "Image", "children":[]},
				{"name": "Video", "children":[]},
				{"name": "Other", "children":[]}
			]
		}
	}

	_genders = []
	_orientations = []
	_relationship_partners = []

	family_members = []
	pets = []

	core_places_lived = []
	more_places_lived = []

	core_places_grew_up = []
	more_places_grew_up = []

	core_attributes = []
	more_attributes = []

	core_possessions = []
	more_possessions = []
	
	core_actions = []
	more_actions = []

	favorites = []
	sentiments = []

	derived_attributes = {
		"drug": [],
		"family_members": [],
		"gadget": [],
		"gender": [],
		"location": [],
		"nationality": [],
		"orientation": [],
		"pets": [],
		"physical_characteristics": [],
		"political_view": [],
		"possession": [],
		"race": [],
		"relationship_status": [],
		"religion": []
	}

	corpus = ""
	
	commented_dates = []
	submitted_dates = []
	
	lurk_streak = None

	comments_gilded = 0
	submissions_gilded = 0
	
	def __init__(self,username):
		# Populate username and about data
		self.username = username
		self.signup_date, self.link_karma, self.comment_karma = self.get_about()

		# Retrieve comments and submissions
		self.comments = self.get_comments()
		self.submissions = self.get_submissions()

		# Initialize other properties
		today = datetime.datetime.now(tz=pytz.utc).date()

		start = self.signup_date.date()

		self.signup_date_text = Util.ago((today-start).days)

		self.metrics["date"] = [
			{"date":(year, month), "comments": 0, "submissions": 0, "comment_karma": 0, "submission_karma": 0} \
			for (year, month) in sorted(list(set([((today-datetime.timedelta(days=x)).year,(today-datetime.timedelta(days=x)).month) \
			for x in range(0,(today-start).days)])))
		]
		
		self.metrics["hour"] = [
			{"hour": hour, "comments": 0, "submissions": 0, "comment_karma": 0, "submission_karma": 0} for hour in range(0,24)
		]

		self.metrics["weekday"] = [
			{"weekday": weekday, "comments": 0, "submissions": 0, "comment_karma": 0, "submission_karma": 0} for weekday in range(0,7)
		]


	def __str__(self):
		text =  "-"*80 + "\n"
		text += "Gender: %s\n" % str(self.gender())
		text += "Orientation: %s\n" % str(self.orientation())
		text += "Relationship partner: %s\n" % str(self.relationship_partner())
		text += "Family members: %s\n" % ", ".join([relative for (relative, source) in self.family_members])
		text += "Pets: %s\n" % ", ".join([pet for (pet, source) in self.pets])
		text += "Places lived: %s\n" % ", ".join([place for (place, source) in self.core_places_lived])
		text += "Places grew up: %s\n" % ", ".join([place for (place, source) in self.core_places_grew_up])
		text += "Attributes: %s\n" % ", ".join([attribute for (attribute, source) in self.core_attributes])
		text += "Possessions: %s\n" % ", ".join([possession for (possession, source) in self.core_possessions])
		text += "Actions: %s\n" % ", ".join([action for (action, source) in self.core_actions])
		text += "Favorites: %s\n" % ", ".join([favorite for (favorite, source) in self.favorites])

		text += "Derived Attributes: %s\n" % str(self.derived_attributes)

		#text += "Commented subreddits: %s\n" % ", ".join([str(t) for t in self.commented_subreddits()])
		#text += "Submitted subreddits: %s\n" % ", ".join([str(t) for t in self.submitted_subreddits()])

		text += "Results: %s\n" % self.results()

		text +=  "-"*80 + "\n"
		return text


	def get_about(self):
		url = r"http://www.reddit.com/user/%s/about.json" % self.username
		response = requests.get(url,headers=self.HEADERS)
		response_json = response.json()
		return (datetime.datetime.fromtimestamp(response_json["data"]["created_utc"],tz=pytz.utc),response_json["data"]["link_karma"],response_json["data"]["comment_karma"])


	def get_comments(self,limit=None):
		comments = []
		more_comments = True
		after = None
		base_url = r"http://www.reddit.com/user/%s/comments/.json?limit=100" % self.username
		url = base_url
		while more_comments:
			response = requests.get(url,headers=self.HEADERS)
			response_json = response.json()

			# TODO - Error handling for user not found (404) and rate limiting (429)
			
			for child in response_json["data"]["children"]:
				id = child["data"]["id"].encode("ascii","ignore")
				subreddit = child["data"]["subreddit"].encode("ascii","ignore").lower()
				text = child["data"]["body"].encode("ascii","ignore")
				created_utc = child["data"]["created_utc"]
				score = child["data"]["score"]
				submission_id = child["data"]["link_id"].encode("ascii","ignore").lower()[3:]
				edited = child["data"]["edited"]
				top_level = True if child["data"]["parent_id"].startswith("t3") else False
				gilded = child["data"]["gilded"]
				permalink = "http://www.reddit.com/r/%s/comments/%s/_/%s" % (subreddit, submission_id, id)
				
				comment = Comment(
					id=id,
					subreddit=subreddit,
					text=text,
					created_utc=created_utc,
					score=score,
					permalink=permalink,
					submission_id=submission_id,
					edited=edited,
					top_level=top_level,
					gilded=gilded
				)
				
				comments.append(comment)

			after = response_json["data"]["after"]

			if after:
				url = base_url + "&after=%s" % after
				#time.sleep(2)
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
			response = requests.get(url,headers=self.HEADERS)
			response_json = response.json()

			# TODO - Error handling for user not found (404) and rate limiting (429)
			
			for child in response_json["data"]["children"]:
				id = child["data"]["id"].encode("ascii","ignore")
				subreddit = child["data"]["subreddit"].encode("ascii","ignore").lower()
				text = child["data"]["selftext"].encode("ascii","ignore").lower()
				created_utc = child["data"]["created_utc"]
				score = child["data"]["score"]
				permalink = "http://www.reddit.com"+child["data"]["permalink"].encode("ascii","ignore").lower()
				url = child["data"]["url"].encode("ascii","ignore").lower()
				title = child["data"]["title"].encode("ascii","ignore")
				is_self = child["data"]["is_self"]
				gilded = child["data"]["gilded"]
				domain = child["data"]["domain"]
				
				submission = Submission(
					id=id,
					subreddit=subreddit,
					text=text,
					created_utc=created_utc,
					score=score,
					permalink=permalink,
					url=url,
					title=title,
					is_self=is_self,
					gilded=gilded,
					domain=domain
				)				

				submissions.append(submission)

			after = response_json["data"]["after"]

			if after:
				url = base_url + "&after=%s" % after
				#time.sleep(2)
			else:
				more_submissions = False

		return submissions


	def process(self):
		if self.comments:
			self.process_comments()

		if self.submissions:
			self.process_submissions()
		
		if self.comments or self.submissions:
			self.derive_attributes()

	
	def process_comments(self):
		if not self.comments:
			return
		
		self.earliest_comment = self.comments[-1]
		self.latest_comment = self.comments[0]

		self.best_comment = self.comments[0]
		self.worst_comment = self.comments[0]

		for comment in self.comments:
			self.process_comment(comment)


	def process_submissions(self):
		if not self.submissions:
			return
		
		self.earliest_submission = self.submissions[-1]
		self.latest_submission = self.submissions[0]

		self.best_submission = self.submissions[0]
		self.worst_submission = self.submissions[0]

		for submission in self.submissions:
			self.process_submission(submission)


	def process_comment(self, comment):
		text = Util.sanitize_text(comment.text)
		self.corpus += text.lower()

		comment_timestamp = datetime.datetime.fromtimestamp(comment.created_utc,tz=pytz.utc)

		self.commented_dates.append(comment_timestamp.date())
		self.comments_gilded += comment.gilded
		
		for i,d in enumerate(self.metrics["date"]):
			if d["date"]==(comment_timestamp.date().year, comment_timestamp.date().month):
				d["comments"]+=1
				d["comment_karma"]+=comment.score
				self.metrics["date"][i]=d
				break

		for i,h in enumerate(self.metrics["hour"]):
			if h["hour"]==comment_timestamp.hour:
				h["comments"]+=1
				h["comment_karma"]+=comment.score
				self.metrics["hour"][i]=h
				break

		for i,w in enumerate(self.metrics["weekday"]):
			if w["weekday"]==comment_timestamp.date().weekday():
				w["comments"]+=1
				w["comment_karma"]+=comment.score
				self.metrics["weekday"][i]=w
				break

		if comment.score > self.best_comment.score:
			self.best_comment = comment
		elif comment.score < self.worst_comment.score:
			self.worst_comment = comment

		if comment.subreddit.lower() in ignore_text_subs:
			return False

		if not re.search(r"\b(i|my)\b",text,re.I):
			return False
		
		(chunks, sentiments) = extractor.extract_chunks(text)
		self.sentiments += sentiments

		for chunk in chunks:
			self.load_attributes(chunk, comment)

		return True


	def process_submission(self, submission):
		if(submission.is_self):
			text = Util.sanitize_text(submission.text)
			self.corpus += text.lower()

		submission_timestamp = datetime.datetime.fromtimestamp(submission.created_utc,tz=pytz.utc)

		self.submitted_dates.append(submission_timestamp.date())
		self.submissions_gilded += submission.gilded

		for i,d in enumerate(self.metrics["date"]):
			if d["date"]==(submission_timestamp.date().year, submission_timestamp.date().month):
				d["submissions"]+=1
				d["submission_karma"]+=submission.score
				self.metrics["date"][i]=d
				break

		for i,h in enumerate(self.metrics["hour"]):
			if h["hour"]==submission_timestamp.hour:
				h["submissions"]+=1
				h["submission_karma"]+=submission.score
				self.metrics["hour"][i]=h
				break

		for i,w in enumerate(self.metrics["weekday"]):
			if w["weekday"]==submission_timestamp.date().weekday():
				w["submissions"]+=1
				w["submission_karma"]+=submission.score
				self.metrics["weekday"][i]=w
				break

		submission_type = None
		submission_domain = None
		submission_url_path = urlparse(submission.url).path
		
		if submission.domain.startswith("self."):
			submission_type = "Self"
			submission_domain = submission.subreddit
		elif (submission_url_path.endswith(tuple(self.IMAGE_EXTENSIONS)) or submission.domain.endswith(tuple(self.IMAGE_DOMAINS))):
			submission_type = "Image"
			submission_domain = submission.domain
		elif submission.domain.endswith(tuple(self.VIDEO_DOMAINS)):
			submission_type = "Video"
			submission_domain = submission.domain
		else:
			submission_type = "Other"
			submission_domain = submission.domain
		t = [x for x in self.metrics["submissions"]["children"] if x["name"]==submission_type][0]
		d = ([x for x in t["children"] if x["name"]==submission_domain] or [None])[0]
		if d:
			#self.metrics["submisssions"][submission_type]
			d["size"] += 1
		else:
			t["children"].append({
				"name": submission_domain,
				"size": 1
			})

		if submission.score > self.best_submission.score:
			self.best_submission = submission
		elif submission.score < self.worst_submission.score:
			self.worst_submission = submission
		
		if submission.subreddit.lower() in ignore_text_subs:
			return False

		if not submission.is_self or not re.search(r"\b(i|my)\b",text,re.I):
			return False
		
		(chunks, sentiments) = extractor.extract_chunks(text)
		self.sentiments += sentiments

		for chunk in chunks:
			self.load_attributes(chunk, submission)

		return True


	def load_attributes(self, chunk, post):
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
					self.pets.append((pet, post.permalink))
				elif family_member:
					self.family_members.append((family_member, post.permalink))
				elif relationship_partner:
					self._relationship_partners.append((relationship_partner, post.permalink))
				else:
					self.more_possessions.append((norm_nouns, post.permalink))

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
					self.more_attributes.append((full_noun_phrase, post.permalink))
					return

				attribute = []
				for noun in norm_nouns:
					gender = None
					orientation = None
					if "am" in verbs:
						gender = extractor.gender(noun)
						orientation = extractor.orientation(noun)
					if gender:
						self._genders.append((gender, post.permalink))
					elif orientation:
						self._orientations.append((orientation, post.permalink))
					# Include only "am" phrases
					elif "am" in verbs: 
						attribute.append(noun)
				
				if attribute and \
					(
						(
							# Include only attributes that end in predefined list of endings...
							any(a.endswith(extractor.include_attribute_endings) for a in attribute)
							and
							# And exclude...
							not
							(
								# ...certain lone attributes
								(len(attribute)==1 and attribute[0] in extractor.skip_lone_attributes and not pnp_norm_nouns)
								or
								# ...predefined skip attributes
								any(a in attribute for a in extractor.skip_attributes)
								or
								# ...attributes that end in predefined list of endings
								any(a.endswith(extractor.exclude_attribute_endings) for a in attribute)
							)
						)
						or
						(
							# And include special attributes with different endings
							any(a in attribute for a in extractor.include_attributes)
						)
					):
					self.core_attributes.append((full_noun_phrase, post.permalink))
				elif attribute:
					self.more_attributes.append((full_noun_phrase, post.permalink))

			# I live(d) in ...
			elif "live" in norm_verbs and prepositions and norm_nouns:
				if any(p in ["in","near","by"] for p in prepositions) and proper_nouns:
					self.core_places_lived.append((" ".join(prepositions) + " " + noun_phrase_text, post.permalink))
				else:
					self.more_places_lived.append((" ".join(prepositions) + " " + noun_phrase_text, post.permalink))
			
			# I grew up in ...
			elif "grow" in norm_verbs and "up" in prepositions and norm_nouns:
				if any(p in ["in","near","by"] for p in prepositions) and proper_nouns:
					self.core_places_grew_up.append((" ".join([p for p in prepositions if p!="up"]) + " " + noun_phrase_text, post.permalink))
				else:
					self.more_places_grew_up.append((" ".join([p for p in prepositions if p!="up"]) + " " + noun_phrase_text, post.permalink))

			elif len(norm_verbs)==1 and "prefer" in norm_verbs and norm_nouns and not determiners and not prepositions:
				self.favorites.append((full_noun_phrase, post.permalink))

			elif norm_nouns:
				more_actions = " ".join(norm_verbs)
				self.more_actions.append((more_actions, post.permalink))


	def derive_attributes(self):
		for name,count in self.commented_subreddits():
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			if subreddit and subreddit["attribute"] and count>=self.MIN_THRESHOLD:
				self.derived_attributes[subreddit["attribute"]].append(subreddit["value"])

		for name,count in self.submitted_subreddits():
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			if subreddit and subreddit["attribute"] and count>=self.MIN_THRESHOLD:
				self.derived_attributes[subreddit["attribute"]].append(subreddit["value"])

		if "wife" in [v for v,s in self._relationship_partners]:
			self.derived_attributes["gender"].append("male")
		elif "husband" in [v for v,s in self._relationship_partners]:
			self.derived_attributes["gender"].append("female")

		active_dates = sorted(self.commented_dates+self.submitted_dates)

		self.first_post_date = min(active_dates)
		self.first_post_date_text = Util.ago((self.first_post_date-self.signup_date.date()).days)
		
		active_dates += [datetime.date.today()]
		lurk_streak = max([{"duration":(d2-d1).days, "date1":d1, "date2":d2} for d1,d2 in zip(active_dates[:-1], active_dates[1:])], key=lambda x:x["duration"])
		self.lurk_streak = {
			"duration":Util.ago(lurk_streak["duration"]),
			"date1": lurk_streak["date1"].strftime("%b %d, %Y"),
			"date2": lurk_streak["date2"].strftime("%b %d, %Y"),
		}

		'''
		if not self._genders and "wife" in [v for v,s in self._relationship_partners]:
			self._genders.append(("male","derived"))
		elif not self._genders and "husband" in [v for v,s in self._relationship_partners]:
			self._genders.append(("female","derived"))
		'''


	def commented_subreddits(self):
		return [(name,count) for (name,count) in Counter([comment.subreddit for comment in self.comments]).most_common()]


	def submitted_subreddits(self):
		return [(name,count) for (name,count) in Counter([submission.subreddit for submission in self.submissions]).most_common()]


	def gender(self):
		if self._genders:
			(g,_) = Counter([g for g,_ in self._genders]).most_common(1)[0]
			return g
		else:
			return None


	def orientation(self):
		if self._orientations:
			(o,_) = Counter([o for o,_ in self._orientations]).most_common(1)[0]
			return o
		else:
			return None


	def relationship_partner(self):
		if self._relationship_partners:
			(p,_) = Counter([p for p,_ in self._relationship_partners]).most_common(1)[0]
			return p
		else:
			return None


	def results(self):
		if not (self.comments or self.submissions):
			return json.dumps(None)

		metrics_date = []
		
		for d in self.metrics["date"]:
			metrics_date.append({
				"date":"%d-%02d-01"%(d["date"][0],d["date"][1]), 
				"comments":d["comments"],
				"submissions":d["submissions"],
				"posts":d["comments"]+d["submissions"],
				"comment_karma":d["comment_karma"],
				"submission_karma":d["submission_karma"],
				"karma":d["comment_karma"]+d["submission_karma"]
			})

		
		metrics_hour = []
		
		for h in self.metrics["hour"]:
			metrics_hour.append({
				"hour":h["hour"], 
				"comments":h["comments"], 
				"submissions":h["submissions"],
				"posts":h["comments"]+h["submissions"],
				"comment_karma":h["comment_karma"],
				"submission_karma":h["submission_karma"],
				"karma":h["comment_karma"]+h["submission_karma"]
			})

		weekdays = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
		
		
		metrics_weekday = []
		
		for w in self.metrics["weekday"]:
			metrics_weekday.append({
				"weekday":weekdays[w["weekday"]], 
				"comments":w["comments"], 
				"submissions":w["submissions"],
				"posts":w["comments"]+w["submissions"],
				"comment_karma":w["comment_karma"],
				"submission_karma":w["submission_karma"],
				"karma":w["comment_karma"]+w["submission_karma"]
			})
		
		metrics_subreddit = {"name":"All", "children":[]}
		
		for (name,[comments,comment_karma]) in \
			[(s,[sum(x) for x in zip(*[(1,r[1]) for r in group])]) for s, group in groupby(sorted([(p.subreddit,p.score) for p in self.comments], key=lambda x: x[0]),lambda x: x[0])]:
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			if subreddit:
				topic_level1 = subreddit["topic_level1"]
			else:
				topic_level1 = "Other"

			level1 = ([t for t in metrics_subreddit["children"] if t["name"]==topic_level1] or [None])[0]
			if level1:
				level1["children"].append({
					"name":name,
					"comments":comments,
					"submissions":0,
					"posts":comments,
					"comment_karma":comment_karma,
					"submission_karma":0,
					"karma":comment_karma
				})
			else:
				metrics_subreddit["children"].append({"name":topic_level1, "children":[{
					"name":name,
					"comments":comments,
					"submissions":0,
					"posts":comments,
					"comment_karma":comment_karma,
					"submission_karma":0,
					"karma":comment_karma
				}]})
		
		for (name,[submissions,submission_karma]) in \
			[(s,[sum(x) for x in zip(*[(1,r[1]) for r in group])]) for s, group in groupby(sorted([(p.subreddit,p.score) for p in self.submissions], key=lambda x: x[0]),lambda x: x[0])]:
			subreddit = ([s for s in subreddits if s["name"]==name] or [None])[0]
			if subreddit:
				topic_level1 = subreddit["topic_level1"]
			else:
				topic_level1 = "Other"
			level1 = ([t for t in metrics_subreddit["children"] if t["name"]==topic_level1] or [None])[0]
			if level1:
				sub_in_level1 = ([s for s in level1["children"] if s["name"]==name] or [None])[0]
				if sub_in_level1:
					sub_in_level1["submissions"]=submissions
					sub_in_level1["submission_karma"]=submission_karma
					sub_in_level1["posts"]+=submissions
					sub_in_level1["karma"]+=submission_karma
				else:
					level1["children"].append({
						"name":name,
						"comments":0,
						"submissions":submissions,
						"posts":submissions,
						"comment_karma":0,
						"submission_karma":submission_karma,
						"karma":submission_karma
					})
			else:
				metrics_subreddit["children"].append({"name":topic_level1, "children":[{
					"name":name,
					"comments":0,
					"submissions":submissions,
					"posts":submissions,
					"comment_karma":0,
					"submission_karma":submission_karma,
					"karma":submission_karma
				}]})

		
		metrics_topic = {"name":"All", "children":[]}
		
		topics = []
		
		for comment in self.comments:
			subreddit = ([s for s in subreddits if s["name"]==comment.subreddit] or [None])[0]
			if subreddit and subreddit["ignore_topic"]!="Y":
				#topic = ">".join([subreddit["topic_level1"],subreddit["topic_level2"],subreddit["topic_level3"]])
				topic = subreddit["topic_level1"]
				if subreddit["topic_level2"]:
					topic += ">"+subreddit["topic_level2"]
				else:
					topic += ">"+"Generic"
				if subreddit["topic_level3"]:
					topic += ">"+subreddit["topic_level3"]
				else:
					topic += ">"+"Generic"
				topics.append(topic)
			else:
				topics.append("Other")
		
		for submission in self.submissions:
			subreddit = ([s for s in subreddits if s["name"]==submission.subreddit] or [None])[0]
			if subreddit and subreddit["ignore_topic"]!="Y":
				#topic = ">".join([subreddit["topic_level1"],subreddit["topic_level2"],subreddit["topic_level3"]])
				topic = subreddit["topic_level1"]
				if subreddit["topic_level2"]:
					topic += ">"+subreddit["topic_level2"]
				else:
					topic += ">"+"Generic"
				if subreddit["topic_level3"]:
					topic += ">"+subreddit["topic_level3"]
				else:
					topic += ">"+"Generic"
				topics.append(topic)
			else:
				topics.append("Other")
		
		for topic, count in Counter(topics).most_common():
			level_topics = filter(None,topic.split(">"))
			current_node = metrics_topic
			for i, level_topic in enumerate(level_topics):
				children = current_node["children"]
				if i+1 < len(level_topics):
					found_child = False
					for child in children:
						if child["name"]==level_topic:
							child_node = child
							found_child = True
							break
					if not found_child:
						#child_node = {"name": level_topic, "children": []}
						child_node = {"name": level_topic, "children": []}
						children.append(child_node)
					current_node = child_node
				else:
					#child_node = {"name": level_topic, "size": count, "children":[]}
					child_node = {"name": level_topic, "size": count}
					children.append(child_node)		

		common_words = [{"text":word, "size":count} for word, count in Counter(extractor.common_words(self.corpus)).most_common(200)]
		total_word_count = extractor.total_word_count(self.corpus)
		unique_word_count = extractor.unique_word_count(self.corpus)
		hours_typed = round(total_word_count/(40.00*60.00),2)


		core_places_lived = []
		for value,count in Counter([value for value,source in self.core_places_lived]).most_common():
			sources = [s for v,s in self.core_places_lived if v==value]
			core_places_lived.append({"value":value, "count":count, "sources":sources})

		more_places_lived = []
		for value,count in Counter([value for value,source in self.more_places_lived]).most_common():
			sources = [s for v,s in self.more_places_lived if v==value]
			more_places_lived.append({"value":value, "count":count, "sources":sources})

		core_places_grew_up = []
		for value,count in Counter([value for value,source in self.core_places_grew_up]).most_common():
			sources = [s for v,s in self.core_places_grew_up if v==value]
			core_places_grew_up.append({"value":value, "count":count, "sources":sources})

		more_places_grew_up = []
		for value,count in Counter([value for value,source in self.more_places_grew_up]).most_common():
			sources = [s for v,s in self.more_places_grew_up if v==value]
			more_places_grew_up.append({"value":value, "count":count, "sources":sources})

		family_members = []
		for value,count in Counter([value for value,source in self.family_members]).most_common():
			sources = [s for v,s in self.family_members if v==value]
			family_members.append({"value":value, "count":count, "sources":sources})

		pets = []
		for value,count in Counter([value for value,source in self.pets]).most_common():
			sources = [s for v,s in self.pets if v==value]
			pets.append({"value":value, "count":count, "sources":sources})

		favorites = []
		for value,count in Counter([value for value,source in self.favorites]).most_common():
			sources = [s for v,s in self.favorites if v==value]
			favorites.append({"value":value, "count":count, "sources":sources})

		core_attributes = []
		for value,count in Counter([value for value,source in self.core_attributes]).most_common():
			sources = [s for v,s in self.core_attributes if v==value]
			core_attributes.append({"value":value, "count":count, "sources":sources})

		more_attributes = []
		for value,count in Counter([value for value,source in self.more_attributes]).most_common():
			sources = [s for v,s in self.more_attributes if v==value]
			more_attributes.append({"value":value, "count":count, "sources":sources})

		core_possessions = []
		for value,count in Counter([value for value,source in self.core_possessions]).most_common():
			sources = [s for v,s in self.core_possessions if v==value]
			core_possessions.append({"value":value, "count":count, "sources":sources})

		more_possessions = []
		for value,count in Counter([value for value,source in self.more_possessions]).most_common():
			sources = [s for v,s in self.more_possessions if v==value]
			more_possessions.append({"value":value, "count":count, "sources":sources})
				
		core_actions = []
		for value,count in Counter([value for value,source in self.core_actions]).most_common():
			sources = [s for v,s in self.core_actions if v==value]
			core_actions.append({"value":value, "count":count, "sources":sources})

		more_actions = []
		for value,count in Counter([value for value,source in self.more_actions]).most_common():
			sources = [s for v,s in self.more_actions if v==value]
			more_actions.append({"value":value, "count":count, "sources":sources})

		# "Interesting" attributes
		locations = []
		tv_shows = []
		interests = []
		games = []
		sports = []
		music = []
		drugs = []
		books = []
		celebs = []
		business = []
		entertainment = []
		science = []
		tech = []
		lifestyle = []
		others = []
		fringe_topics = ["anthropology", "architecture", "art", "history", "law", "news & politics", "philosophy", "psychology", "travel"]


		for topic, count in Counter(topics).most_common():
			level_topics = [x for x in topic.split(">") if x.lower()!="generic"]

			# Locations
			if len(level_topics)>1 and level_topics[0].lower()=="location" and count>=self.MIN_THRESHOLD:
				locations.append({"value": Util.coalesce(level_topics).lower(), "count": count})
			
			# TV shows
			if len(level_topics)>1 and level_topics[0].lower()=="entertainment" and level_topics[1].lower()=="tv shows" and count>=self.MIN_THRESHOLD:
				tv_shows.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Interests
			if len(level_topics)>1  and level_topics[0].lower()=="interests" and count>=self.MIN_THRESHOLD:
				interests.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Games
			if len(level_topics)>1 and level_topics[0].lower()=="gaming" and count>=self.MIN_THRESHOLD:
				games.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Sports
			if len(level_topics)>1 and level_topics[0].lower()=="sports" and count>=self.MIN_THRESHOLD:
				sports.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Music
			if len(level_topics)>1 and level_topics[0].lower()=="music" and count>=self.MIN_THRESHOLD:
				music.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Drugs
			if len(level_topics)>1 and level_topics[0].lower()=="lifestyle" and level_topics[1].lower()=="drugs" and count>=self.MIN_THRESHOLD:
				drugs.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Books
			if len(level_topics)>1 and level_topics[0].lower()=="entertainment" and level_topics[1].lower()=="books" and count>=self.MIN_THRESHOLD:
				books.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Celebs
			if len(level_topics)>1 and level_topics[0].lower()=="entertainment" and level_topics[1].lower()=="celebrities" and count>=self.MIN_THRESHOLD:
				celebs.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Business
			if len(level_topics)>1 and level_topics[0].lower()=="business" and count>=self.MIN_THRESHOLD:
				business.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Other Entertainment
			if len(level_topics)>1 and level_topics[0].lower()=="entertainment" and level_topics[1].lower() not in ["books", "celebrities", "tv shows"] and count>=self.MIN_THRESHOLD:
				entertainment.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Science
			if len(level_topics)>1 and level_topics[0].lower()=="science" and count>=self.MIN_THRESHOLD:
				science.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Tech
			if len(level_topics)>1 and level_topics[0].lower()=="technology" and count>=self.MIN_THRESHOLD:
				tech.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Lifestyle
			if len(level_topics)>1 and level_topics[0].lower()=="lifestyle" and level_topics[1] not in ["drugs", "religion"] and count>=self.MIN_THRESHOLD:
				lifestyle.append({"value": Util.coalesce(level_topics).lower(), "count": count})

			# Others
			if level_topics[0].lower() in fringe_topics and count>=self.MIN_THRESHOLD:
				others.append({"value": Util.coalesce(level_topics).lower(), "count": count})



		results = {
			"username": self.username,
			"about": {
				"gender": self.gender(),
				"orientation": self.orientation(),
				"relationship_partner": self.relationship_partner(),
				"places_lived": {
					"core":core_places_lived,
					"more":more_places_lived
				},
				"places_grew_up": {
					"core":core_places_grew_up,
					"more":more_places_grew_up
				},
				"family_members": family_members,			
				"pets": pets,
				"favorites": favorites,
				"attributes": {
					"core": core_attributes,
					"more": more_attributes
				},
				"possessions": {
					"core": core_possessions,
					"more": more_possessions
				},
				"locations": locations,
				"tv_shows": tv_shows,
				"interests": interests,
				"games": games,
				"sports": sports,
				"music": music,
				"drugs": drugs,
				"books": books,
				"celebs": celebs,
				"business": business,
				"entertainment": entertainment,
				"science": science,
				"tech": tech,
				"lifestyle": lifestyle,
				"others": others,
				"derived_attributes": {
					"drug":Counter(self.derived_attributes["drug"]).most_common(),
					"family_members":Counter(self.derived_attributes["family_members"]).most_common(),
					"gadget":Counter(self.derived_attributes["gadget"]).most_common(),
					"gender":Counter(self.derived_attributes["gender"]).most_common(1),
					"location":Counter(self.derived_attributes["location"]).most_common(),
					"nationality":Counter(self.derived_attributes["nationality"]).most_common(),
					"orientation":Counter(self.derived_attributes["orientation"]).most_common(),
					"pets":Counter(self.derived_attributes["pets"]).most_common(),
					"physical_characteristics":Counter(self.derived_attributes["physical_characteristics"]).most_common(),
					"political_view":Counter(self.derived_attributes["political_view"]).most_common(),
					"possession":Counter(self.derived_attributes["possession"]).most_common(),
					"race":Counter(self.derived_attributes["race"]).most_common(),
					"relationship_status":Counter(self.derived_attributes["relationship_status"]).most_common(1),
					"religion":Counter(self.derived_attributes["religion"]).most_common()
				}
			},
			"stats": {
				"basic": {
					"signup_date": self.signup_date.strftime("%b %d, %Y"),
					"signup_date_text": self.signup_date_text,
					"first_post_date": self.first_post_date.strftime("%b %d, %Y"),
					"first_post_date_text": self.first_post_date_text,
					"lurk_streak": self.lurk_streak,
					"link_karma": self.link_karma,
					"comment_karma": self.comment_karma,
					"comments": {
						"count": len(self.comments),
						"gilded": self.comments_gilded,
						"best": {
							"text":self.best_comment.text if self.best_comment else None,
							"permalink":self.best_comment.permalink if self.best_comment else None
						},
						"worst": {
							"text":self.worst_comment.text if self.worst_comment else None,
							"permalink":self.worst_comment.permalink if self.worst_comment else None
						}
					},
					"submissions": {
						"count": len(self.submissions),
						"gilded": self.submissions_gilded,
						"best": {
							"title":self.best_submission.title if self.best_submission else None,
							"permalink":self.best_submission.permalink if self.best_submission else None
						},
						"worst": {
							"title":self.worst_submission.title if self.worst_submission else None,
							"permalink":self.worst_submission.permalink if self.worst_submission else None
						}
					},
					"words_in_posts": {
						"total_word_count": total_word_count,
						"unique_word_count": unique_word_count,
						"hours_typed": hours_typed,
						"karma_per_word": round(self.comment_karma/(total_word_count*1.00),2)
					}
				},
				"metrics": {
					"date": metrics_date,
					"hour": metrics_hour,
					"weekday": metrics_weekday,
					"subreddit": metrics_subreddit,
					"topic": metrics_topic,
					"submissions": self.metrics["submissions"],
				},
				"common_words": common_words
			}
		}

		return json.dumps(results)

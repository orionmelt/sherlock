# -*- coding: utf-8 -*-

from nltk import RegexpParser
from textblob import TextBlob, Word
import re

NOUN="n"
VERB="v"
ADV="r"
ADJ="a"

class DataExtractor:
	substitutions = [
		(r"\b(im|i'm)\b", "i am"),
		(r"\b(id|i'd)\b", "i would"),
		(r"\b(i'll)\b", "i will"),
		(r"\bbf\b", "boyfriend"),
		(r"\bgf\b", "girlfriend"),
		(r"\byoure\b", "you are"),
		(r"\b(dont|don't)\b", "do not"),
		(r"\b(didnt|didn't)\b", "did not"),
		(r"\b(wasnt|wasn't)\b", "was not"),
		(r"\b(isnt|isn't)\b", "is not"),
		(r"\b(arent|aren't)\b", "are not"),
		(r"\b(werent|weren't)\b", "were not"),
		(r"\b(havent|haven't)\b", "have not"),
		(r"\b(couldnt|couldn't)\b", "could not"),
		(r"\bgotta\b", "have to"),
		(r"\bgonna\b", "going to"),
		(r"\bwanna\b", "want to"),
		(r"\b(kinda|kind of)\b", ""),
		(r"\b(sorta|sort of)\b", ""),
		(r"\b(dunno|donno)\b", "do not know"),
		(r"\b(cos|coz|cus|cuz)\b", "because"),
		(r"\bfave\b", "favorite"),
		(r"\bbtw\b", "by the way"),
		(r"\bhubby\b", "husband"),
		(r"\bheres\b", "here is"),
		(r"\btheres\b", "there is"),
		(r"\bwheres\b", "where is"),
		(r"\[(.*?)\]\((.*?)\)", r""), 	# Remove links from Markdown
		(r"[\"\“](.*?)[\"\”]", r""), 	# Remove text within quotes
		(r" \'(.*?)\ '", r""), 			# Remove text within quotes
		(r"\.+?", r". "), 				# Remove ellipses
		(r"\(.*?\)", r""), 				# Remove text within round brackets
		(r"\blike|love\b", r"prefer"), 	# Default POS tagger seems to always tag "like" (and sometimes "love") as a noun - this is a bandaid fix for now

	]

	skip_verbs 			= ["were", "think", "guess"]
	skip_prepositions 	= ["that"]
	skip_adjectives		= ["sure","glad","happy","afraid","sorry"]

	grammar = r"""
	  _VP:	
	  		{<RB.*>*<V.*>+<RB.*>*}			# adverb* verb adverb* (really think / strongly suggest / look intensely)
	  _N:
	  		{<DT>*<JJ>*<NN.*>+}				# determiner adjective noun(s) (a beautiful house / the strongest fighter)
	  _N_PREP_N:
	  		{<_N>(<TO>|<IN>)<_N>}			# to/in noun ((newcomer) to physics / (big fan) of Queen / (newbie) in gaming )
	  POSS: 
	        {<PRP\$><_N>}					# My adjective noun/s (My awesome phone)
	  ACT1:
	  		{<PRP><_VP><IN>*<_N>}			# I verb in* adjective* noun (I am a great chef / I like cute animals / I work in beautiful* New York / I live in the suburbs)
	  ACT2:
	  		{<PRP><_VP><IN>*<_N_PREP_N>}		# Above + to/in noun (I am a fan of Jaymay / I have trouble with flannel)
	"""
	chunker = RegexpParser(grammar)

	def clean_up(self, text):
		for original, rep in self.substitutions:
			text = re.sub(original, rep, text, flags=re.I)
		return text

	def normalize(self, word,kind="n"):
		return Word(word).lemmatize(kind).lower()

	def pet_animal(self, word):
		if re.match(r"\b(dog|cat|hamster|fish|pig|snake|rat|parrot)\b",word):
			return word
		else:
			return None

	def family_member(self, word):
		if re.match(r"\b(mom|mother|mum|mommy)\b",word):
			return "mother"
		elif re.match(r"\b(dad|father|pa|daddy)\b",word):
			return "father"
		elif re.match(r"\b(brother|sister|son|daughter)\b",word):
			return word
		else:
			return None

	def relationship_partner(self, word):
		if re.match(r"\b(boyfriend|girlfriend|so|wife|husband)\b",word):
			return word
		else:
			return None

	def gender(self, word):
		if re.match(r"\b(girl|woman|female|lady|she)\b",word):
			return "female"
		elif re.match(r"\b(guy|man|male|he|dude)\b",word):
			return "male"
		else:
			return None

	def orientation(self, word):
		if re.match(r"\b(gay|straight|bi|bisexual|homosexual)\b",word):
			return word
		else:
			return None

	def verb_dict(self, phrase):
		verbs = []
		unnormalized_verbs = []
		adverbs = []

		for w,t in phrase:
			if t.startswith("V"):
				verbs.append(self.normalize(w,VERB))
				unnormalized_verbs.append(w.lower())
			elif t.startswith("RB"):
				adverbs.append(self.normalize(w,ADV))
			else:
				# Something wrong - tag shouldn't be in verb phrase
				pass

		return {"verbs":verbs, "unnormalized_verbs":unnormalized_verbs, "adverbs":adverbs}

	def noun_dict(self, phrase):
		determiners = []
		adjectives = []
		nouns = []
		unnormalized_nouns = []
		proper_nouns = []

		for w,t in phrase:
			if t=="DT":
				determiners.append(w.lower())
			elif t.startswith("JJ"):
				adjectives.append(self.normalize(w,ADJ))
			elif t.startswith("NNP"):
				proper_nouns.append(w)
			elif t.startswith("N"):
				nouns.append(self.normalize(w,NOUN))
				unnormalized_nouns.append(w.lower())
			else:
				# Something wrong - tag shouldn't be in noun phrase
				pass

		return {"determiners":determiners, "adjectives":adjectives, "nouns":nouns, "unnormalized_nouns":unnormalized_nouns, "proper_nouns":proper_nouns}

	def process_noun_phrase(self, noun_tree):
		if noun_tree.label() != "_N":
			return None

		noun_phrase = self.noun_dict(noun_tree.leaves())
		return noun_phrase

	def process_npn_phrase(self, npn_tree):
		if npn_tree.label() != "_N_PREP_N":
			return None

		pri_np = []
		conn = []
		sec_np = []
		reached_connector = False
		for i in range(len(npn_tree)):
			node = npn_tree[i]
			if type(node) is tuple: # we have hit the noun connector(s)
				c,_ = node
				conn.append(c)
				reached_connector = True
			else:
				if reached_connector:
					sec_np = self.process_noun_phrase(node)
				else:
					pri_np = self.process_noun_phrase(node)
		return (pri_np, conn, sec_np)

	def process_possession(self, phrase):
		pronoun = None
		primary_noun_phrase = {}
		
		for i in range(len(phrase)):
			node = phrase[i]
			if type(node) is tuple: # word can only be pronoun
				w,t = node
				if t=="PRP$":
					pronoun = w.lower()
				else: # what could this be?
					pass
			else:
				if node.label()=="_N":
					primary_noun_phrase = self.process_noun_phrase(node)
				else: # what could this be?
					pass

		return {"kind":"possession", "primary_noun_phrase":primary_noun_phrase}

	def process_action(self, phrase):
		pronoun = None
		prepositions = []
		verb_phrase = {}
		primary_noun_phrase = {}
		noun_connectors = []
		secondary_noun_phrase = {}

		for i in range(len(phrase)):
			node = phrase[i]
			if type(node) is tuple: # word is either pronoun or preposition
				w,t = node
				if t=="PRP":
					pronoun = w.lower()
				elif t=="IN":
					prepositions.append(w.lower())
				else: # what could this be?!
					pass
			else:
				if node.label()=="_VP":
					verbs = node.leaves()
					verb_phrase = self.verb_dict(node.leaves())
				elif node.label()=="_N":
					primary_noun_phrase = self.process_noun_phrase(node)
				elif node.label()=="_N_PREP_N":
					primary_noun_phrase, noun_connectors, secondary_noun_phrase = self.process_npn_phrase(node)

		return {"kind":"action", "verb_phrase":verb_phrase, "prepositions":prepositions, "primary_noun_phrase":primary_noun_phrase, "noun_connectors":noun_connectors, "secondary_noun_phrase":secondary_noun_phrase}

	def extract_chunks(self, text):
		chunks = []
		sentiments = []
		text = self.clean_up(text)
		blob = TextBlob(text)

		for sentence in blob.sentences:
			sentiments.append((sentence.sentiment.polarity, sentence.sentiment.subjectivity))
			
			if not sentence.tags or not re.search(r"\b(i|my)\b",str(sentence),re.I):
				continue

			tree = self.chunker.parse(sentence.tags)

			for subtree in tree.subtrees(filter = lambda t: t.label() in ['POSS','ACT1','ACT2']):
				
				phrase = subtree.leaves()
				phrase_type = subtree.label()
				if not any(x in [("i","PRP"), ("my","PRP$")] for x in [(w.lower(),t) for w,t in phrase]) or \
				   (phrase_type in ["ACT1","ACT2"] and (any(word in self.skip_verbs for word in [w for w,t in phrase if t.startswith("V")]) or \
														any(word in self.skip_prepositions for word in [w for w,t in phrase if t=="IN"]) or \
														any(word in self.skip_adjectives for word in [w for w,t in phrase if t=="JJ"]))
														):
					continue

				if subtree.label() == "POSS":
					chunk = self.process_possession(subtree)
					if chunk:
						chunks.append(chunk)
				elif subtree.label() in ["ACT1","ACT2"]:
					chunk = self.process_action(subtree)
					if chunk:
						chunks.append(chunk)

		return (chunks, sentiments)

	def ngrams(self,text,n=4):
		return [" ".join(w) for w in TextBlob(text).ngrams(n=n)]

	@staticmethod
	def test_sentence(sentence):
		print TextBlob(sentence).tags
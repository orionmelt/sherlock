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
		(r"\b(dunno|donno)\b", "do not know"),
		(r"\b(cos|coz|cus|cuz)\b", "because"),
		(r"\bfave\b", "favorite"),
		(r"\bbtw\b", "by the way"),
		(r"\bhubby\b", "husband"),
		(r"\bheres\b", "here is"),
		(r"\btheres\b", "there is"),
		(r"\bwheres\b", "where is"),
		(r"\[(.*?)\]\((.*?)\)", r"\1"), # Remove links from Markdown
		(r"\"(.*?)\"", r""), # Remove text within quotes
		(r"\.+?", r". "), # Remove ellipses
	]

	skip_verbs 			= ["were", "think", "guess"]
	skip_prepositions 	= ["that"]
	skip_adjectives		= ["sure","glad","happy","afraid","sorry"]

	grammar = r"""
	  _VP:	
	  		{<RB.*>*<V.*>+<RB.*>*}			# adverb* verb adverb* (really think / strongly suggest / look intensely)
	  _N:
	  		{<DT>*<JJ>*<NN.*>+}				# determiner adjective noun(s) (a beautiful house / the strongest fighter)
	  P1: 
	        {<PRP\$><_N>}					# My adjective noun/s (My awesome phone)
	  P2:
	  		{<PRP><_VP><IN>*<_N>}			# I verb in* adjective* noun (I am a great chef / I like cute animals / I work in beautiful* New York / I live in the suburbs)
	  P:
	        {<P1>}
	        {<P2>}
	"""
	chunker = RegexpParser(grammar)

	def clean_up(self, text):
		#TODO - ignore text within quotes, remove [] and ()
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

	def extract_chunks(self, text):
		chunks = []
		text = self.clean_up(text)
		blob = TextBlob(text)

		for sentence in blob.sentences:
			
			if not sentence.tags or not re.search(r"\b(i|my)\b",str(sentence),re.I):
				continue

			tree = self.chunker.parse(sentence.tags)

			for subtree in tree.subtrees(filter = lambda t: t.node in ['P1','P2']):
				phrase = subtree.leaves()
				phrase_type = subtree.node

				if not any(x in [("i","PRP"), ("my","PRP$")] for x in [(w.lower(),t) for w,t in phrase]) or \
				   (phrase_type=="P2" and any(word in self.skip_verbs for word in [w for w,t in phrase if t.startswith("V")])) or \
				   (phrase_type=="P2" and any(word in self.skip_prepositions for word in [w for w,t in phrase if t=="IN"])) or \
				   (phrase_type=="P2" and any(word in self.skip_adjectives for word in [w for w,t in phrase if t=="JJ"])):
					continue

				pronouns = []
				verbs = []
				actual_verbs = []
				adverbs = []
				prepositions = []
				adjectives = []
				nouns = []
				cardinals = []
				# TODO - Handle proper nouns?
				# TODO - Default POS tagger tags "love" as NN, what can we do about this?

				for w,t in phrase:
					if t.startswith("PRP"):
						pronouns.append(self.normalize(w,NOUN).lower())		
					elif t.startswith("V"):
						verbs.append(self.normalize(w,VERB))
						actual_verbs.append(w.lower())
					elif t.startswith("RB"):
						adverbs.append(self.normalize(w,ADV))
					elif t == "IN":
						prepositions.append(w.lower())
					elif t == "JJ":
						adjectives.append(self.normalize(w,ADJ))
					elif t.startswith("N"):
						if phrase_type == "P1":
							nouns.append(self.normalize(w,NOUN))
						elif phrase_type == "P2":
							nouns.append(w.lower())
					elif t == "CD":
						cardinals.append(w.lower())
				
				if "my" in pronouns:
					chunks.append({
						"kind":"possession", 
						"adjectives":adjectives, 
						"nouns":nouns
					})

				if "i" in pronouns:
					chunks.append({
						"kind":"action", 
						"verbs":verbs,
						"actual_verbs":actual_verbs,
						"adverbs":adverbs, 
						"prepositions":prepositions, 
						"adjectives":adjectives, 
						"nouns":nouns,
						"cardinals":cardinals
					})
		
		return chunks

	@staticmethod
	def test_sentence(sentence):
		print TextBlob(sentence).tags
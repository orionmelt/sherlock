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
		(r"\bkinda\b", "kind of"),
		(r"\b(cos|coz|cus|cuz)\b", "because"),
		(r"\bfave\b", "favorite"),
		(r"\bbtw\b", "by the way"),
		(r"\bhubby\b", "husband"),
		(r"\bheres\b", "here is"),
		(r"\btheres\b", "there is"),
		(r"\bwheres\b", "where is"),
		(r"\[(.*?)\]\((.*?)\)", r"\1"), # Remove links from Markdown
		(r"\"(.*?)\"", r""), # Remove text within quotes
	]

	be_skip_words = ["were","sure","afraid","sorry","glad","happy","fine"]

	grammar = r"""
	  MY_ADJ_NOUN: 
	        {<PRP\$>+<JJ>*<NN.*>+}
	  I_VERB_IN_ADJ_NOUN:
	  		{<PRP>+<V.*>*<RP>*<IN>*<DT>*<RB.*>*<JJ>*(<NN.*>*|<CD>*)}
	  NP:
	        {<MY_ADJ_NOUN>}
	        {<I_VERB_IN_ADJ_NOUN>}
	"""
	chunker = RegexpParser(grammar)

	def clean_up(self, text):
		#TODO - ignore text within quotes, remove [] and ()
		for original, rep in self.substitutions:
			text = re.sub(original, rep, text, flags=re.I)
		return text

	def normalize(self, word,kind="n"):
		return Word(word).lemmatize(kind).lower()

	def leaves(self, tree):
		"""Finds NP (noun phrase) leaf nodes of a chunk tree."""
		for subtree in tree.subtrees(filter = lambda t: t.node=='NP'):
			yield subtree.leaves()

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
			
			if not sentence.tags:
				continue

			tree = self.chunker.parse(sentence.tags)

			for phrase in self.leaves(tree):
				
				if any(word in self.be_skip_words for word in [w for w,t in phrase if (t.startswith("V") or t == "JJ")]):
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

				for w,t in phrase:
					if t.startswith("PRP"):
						pronouns.append(self.normalize(w,NOUN).lower())		
					elif t.startswith("V"):
						verbs.append(self.normalize(w,VERB))
						actual_verbs.append(w.lower())
					elif t == "RP":
						adverbs.append(self.normalize(w,ADV))
					elif t == "IN":
						prepositions.append(w.lower())
					elif t == "JJ":
						adjectives.append(self.normalize(w,ADJ))
					elif t.startswith("N"):
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
# -*- coding: utf-8 -*-
"""
    The text module extracts words from text using punktuation and word tokenizers,
    rejects common stopwords, and lemmatizes each word.
    
    Example:
        >>> from text import lemma_tokenize
    
        >>> lemma_tokenize('100% of your donation funds medical care for patients around the world.')
        ['100', '%', 'donation', 'fund', 'medical', 'care', 'patient', 'around', 'world']

   Author: Dirk Neumann
"""
import nltk
import nltk.tokenize
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize.api import StringTokenizer

def lemma_tokenize(paragraph):
    lmtzr = WordNetLemmatizer()
    try:
      return [lmtzr.lemmatize(word).lower() for sentence in tokenize(paragraph) for word in sentence]
    except LookupError:
      nltk.download('wordnet')
      return [lmtzr.lemmatize(word).lower() for sentence in tokenize(paragraph) for word in sentence]

def tokenize(paragraph):
    try:
        detector = tokenize.detector
    except AttributeError:
        try:
            detector = nltk.data.load('tokenizers/punkt/english.pickle')
        except LookupError:
            nltk.download('punkt')
            detector = nltk.data.load('tokenizers/punkt/english.pickle')
        tokenize.detector = detector
        
    return [
        [
            word 
            for word in nltk.tokenize.word_tokenize(sentence)
            if word not in stopwords()
        ]
        for sentence in detector.tokenize(paragraph.strip())
    ]

def stopwords():
    try:
        stop_words = stopwords.stop_words
    except AttributeError:
        try:
            stop_words = nltk.corpus.stopwords.words('english')
        except LookupError:
            nltk.download('stopwords')
            stop_words = nltk.corpus.stopwords.words('english')
        stop_words.extend(['-', ':', '.', '\'', '\',', ',', '#', '/', '@', '.,', '(', ')', 'RT', 'I', 'I''m'])
        stopwords.stop_words = stop_words
    return stop_words


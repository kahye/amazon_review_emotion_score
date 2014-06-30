# Transform amazon review summary data
# Kahye Song
# Insight Data Engineering 2014 June

from pyspark import SparkConf, SparkContext
from flask import *
import json
import numpy as np
import os
import text_nltk
from gensim.models import Word2Vec
from gzip import GzipFile
from redis import Redis
import sys
import time

# configure spark
conf=SparkConf()
conf.setAppName("Amazon review transform")
sc = SparkContext(conf=conf,pyFiles=['word2vec.py','text_nltk.py'])

if len(sys.argv)>1:
    data_file = sys.argv[1]
else:
    raise Exception("An input file has to be provided.")

# word2vec vector model file
dic_file = "text8.model"


# fetch vectors related to each word
def vectors(x):
    try:
        v = vectors.vectors
    except AttributeError:
        # if no model has been loaded, load model
        vectors.vectors = {}
        m = Word2Vec.load(dic_file)
        for i, word in enumerate(m.vocab):
            # the vector dimention has been reduced to 25 for faster computation. According to the test, dim 25 is sufficient to tell apart different emotions
             vectors.vectors[word] = [1, ] + [float(x) for x in m[word][:25]]
        v = vectors.vectors
        # return the vector associated with the given word, if not, return the first vector - need to be fixed
    return v[x] if x in v else v.itervalues().next()

# all the emotions I am interested in finding in Amazon review text
emotion_names = ['good','like','bad','dislike','happy', 'sad', 'surprised', 'angry', 'disgusted']
num_emotions = len(emotion_names)
# calculate emotion scores by finding the normalized correlation between emotion word vectors and a given word vector
def empathy_vec(x):    
    k, v = x
    d = []
    for a_emotion in emotion_names:
        myvec= norm_vec(vectors(a_emotion)[1:])
        myvec2 = norm_vec(np.array(v[1:]))
        d.append(np.dot(myvec, myvec2))
    return (k, d)

# normalize a vector
def norm_vec(myvec):
    myvec = np.array(myvec)
    return myvec/np.linalg.norm(myvec)



def reformat_scores(x):
    return np.concatenate([np.array([x[0]]),np.array(x[1][:-1])/x[1][-1]]).tolist()



# field of interest in Amazon review either 'review/summary' or 'review/text'
text_field_name = 'review/summary'

# count the run time
begin_time = time.time()
#---------------------------------------------------------
# BEGIN the main processing
#--------------------------------------------------------
# fetch the data file and parse the field of interest and filter out those without any review words
data = sc.textFile(data_file).map(json.loads).cache()
data = data.filter(lambda x: 'review/score' in x and 'product/productId' in x and 'review/time' in x and text_field_name in x)
data = data.filter(lambda x: x[text_field_name]!=None or x['review/score']!=None)
data = data.filter(lambda x: len(x[text_field_name])>0)

# pick review text - tokenize and lammentize
article_vector = data.map(lambda x:  ( (x['product/productId'],float(x['review/score']),x['review/time']),text_nltk.lemma_tokenize(x[text_field_name])))
article_vector = article_vector.filter(lambda x: len(x[1])>0)
# calculate the mean vector of the review text words
article_vector = article_vector.map(lambda x: (x[0],np.nanmean([vectors(w) for w in x[1]],axis=0)))


# calculate the avereage emotion scores of all reviews for a given review score among 1,2,3,4,5
avg_all_review = article_vector.map(empathy_vec).map(lambda x: (x[0][1],np.array(x[1]+[1.0]))).reduceByKey(lambda a,b: a+b).sortByKey().map(reformat_scores).collect()
avg_all_review = np.array(avg_all_review)


run_time = time.time()-begin_time
print 'total run_time: '
print run_time

#---------------------------------------------------------
# BEGIN Output API
#--------------------------------------------------------
# format the api output    
def result_format(data_mat,emo_ind):
    return {'review/score': data_mat[:,0].tolist(), 'emotion_score': data_mat[:,(emo_ind+1)].tolist()}


# redis server to cache api outputs that has been querried recently
redis = Redis()


# API output: correlation between the review scores and emotion scores
app = Flask(__name__, static_folder='static')
@app.route('/amazon.json', methods=['GET', 'POST'])
def amazon():   
    # fetch emotion of interest
    emotion = request.args.get('emotion', emotion_names[0])
    emotion_ind = emotion_names.index(emotion)
    # if the emotion scores are already calculated, fetch from the server
    text = redis.hget('amazon.json', emotion)
    if not text:
        # if emotions scores are not calculated, 
        text = json.dumps(result_format(avg_all_review,emotion_ind))
        redis.hset('amazon.json', emotion, text)
    response = Response(text, mimetype='application/json')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


# running the api
app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False, threaded=True)

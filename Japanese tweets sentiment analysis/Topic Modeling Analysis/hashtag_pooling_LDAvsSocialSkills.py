#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 22:27:17 2019

@author: khan
"""
import pandas as pd
import numpy as np
import re
import sys
sys.path.insert(1, '/home/kwakaba/project/topicModels-java')
import pytm
sys.path.insert(1, '/home/kwakaba/datasets/tweets2018ja/scripts')
import twicab
import MeCab
import time
import glob
import csv
csv.field_size_limit(sys.maxsize)

max_df = 0.5

start_time = time.time()
#tagger = MeCab.Tagger("-Owakati")
tagger = twicab.TwiCab('-d /home/kwakaba/lib/mecab-ipadic-neologd/')

def removeUsernames(txt):
    return re.sub(r'@\S+', '', txt)

def removeSpecialChar(txt):
    return re.sub("\W+", '', txt)

def removeURLs(txt):
    return re.sub(r'http\S+', '', txt)

re1 = re.compile('^[a-zA-Z0-9]+$')
re2 = re.compile('^[0-9]')
stopwords = ['', 'ツイッター', 'ツイート', 'フォロー', 'フォロワー', 'リプライ', 
        'リツイート', 'フォローリツイート', 'アカウント', 'フォロバ', 
        'プロフィール', 'プロフ', 'ツイ', 'アカ']
def additional_filter(token):
    if re1.match(token):
        return False
    if re2.match(token):
        return False
    if token in stopwords:
        return False
    return True

def word_tokenization(txt, tagger):
    tokens = tagger.fukuyama_tokenize(txt)
    tokens = [t for t in tokens if additional_filter(t)]
    return ' '.join(tokens)
    #txt_ls = tagger.parse(txt).split()
    #return (" ".join(txt_ls))

#global dictonary for hashtags and tweets
All_hashtags = {}
All_hashtag_count = {}

def removeHashtags(tweet):
    ls_tweet = tweet.split()
    hashtags = []
    for word in ls_tweet:
        if word[0] == "#":
            hashtags.append(word[1:])
    if hashtags:
        for tag in hashtags:
            ls_tweet.remove("#" + tag)
    return hashtags, removeSpecialChar(" ".join(ls_tweet))

def detectHashtag(tweet):
    hashtags, new_tweet = removeHashtags(tweet)
    if hashtags:
        for tag in hashtags:
            if tag in All_hashtags.keys():
                All_hashtags[tag] = All_hashtags[tag] + " " + word_tokenization(new_tweet, tagger)
                All_hashtag_count[tag] += 1
            else:
                All_hashtags[tag] = word_tokenization(new_tweet, tagger)
                All_hashtag_count[tag] = 1

train_ls = [str(i) for i in range(6,28,1)]
for d in train_ls:
    fn = "training_tweets/{:0>2}".format(d)
    txt = ""
    with open(fn, 'r') as f:
        csv_reader = csv.reader(f, delimiter = '\t')
        for row in csv_reader:
            t = removeURLs(removeUsernames(row[3]))
            detectHashtag(t)

    print("File {} is done".format(d))

print("Total documents are", sum(All_hashtag_count.values()))

corpus = [];
for key in All_hashtags.keys():
    if All_hashtag_count[key] >= 100:
        corpus.append(All_hashtags[key])

print("Total documents are", len(corpus))

docs = pytm.DocumentSet(corpus, min_df=5, max_df=max_df)
print("Corpus Created")

#Applying LDA on our dataset
n_topics = 100
lda = pytm.SVILDA(n_topics, docs.get_n_vocab())
lda.fit(docs, n_iteration=3000, B=1000, n_inner_iteration=5, n_hyper_iteration=20, J=5)
print("LDA fitted")

topic_list = []
alphas = [lda.get_alpha(k) for k in range(n_topics)]
for k, alpha in enumerate(alphas):
    vocab = docs.get_vocab()
    phi = lda.get_phi(k)
    new_phi = np.around(list(phi), decimals = 3)
    a = sorted(zip(vocab, new_phi), key=lambda x: -x[1])[:50]
    topic_list.append(a)

print("Topics Done")
training_time = time.time() - start_time

extract_top_50 = pd.read_excel("result_sentiment_analysis.xlsx")
a = extract_top_50.loc[extract_top_50[">=50"]>=0, "通し番号"]
more_than_50_tweets_users = [int(i) for i in a if not np.isnan(i)]

corpus1 = []
idxs = []
for d in more_than_50_tweets_users:
    fn = "tweets/{}.txt".format(d)
    if fn in glob.glob('tweets/*.txt'):
        txt = ""
        with open(fn, 'r') as f:
            txt += str(removeSpecialChar(removeURLs(removeUsernames(f.read()))))
        corpus1.append(word_tokenization(txt, tagger))
        idxs.append(d)

#docs1 = pytm.DocumentSet(corpus1, min_df=5, max_df=0.5)
docs1 = docs.transform(corpus1)
theta1 = lda.get_theta(docs1)
print("Got theta values")

df1 = pd.DataFrame(theta1)
df1.insert(0, '通し番号', idxs)
df2 = pd.DataFrame([[training_time, "Seconds"]])

df0 = pd.DataFrame(topic_list)
writer = pd.ExcelWriter("Hashtag_NLP_JP100Topics65users.xlsx")
df0.to_excel(writer, 'LDA')
df1.to_excel(writer, 'ThetaValues')
df2.to_excel(writer, 'LDATime')

writer.save()
print("Job Done")

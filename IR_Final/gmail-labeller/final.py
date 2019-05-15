import itertools
import re
import math
from collections import Counter, defaultdict
from typing import Dict, List, NamedTuple

import numpy as np
from numpy.linalg import norm
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize


### File IO and processing
labels = ["forums", "personal", "promotions", "social", "updates"]

class Document(NamedTuple):
    doc_id: int
    label: int
    sender: str
    subject: List[str]
    hour: str
    text: List[str]
    vector: Dict[str, float]


    def __repr__(self):
        return (f"doc_id: {self.doc_id}\n" +
            f"  label: {labels[self.label]}\n" +
            f"  sender: {self.sender}\n" +
            f"  subject: {self.subject}\n" +
            f"  hour: {self.hour}\n" +
            f"  text: {self.text}\n" +
            f"  vector: {self.vector}\n")


def read_stopwords(file):
    with open(file) as f:
        return set([x.strip() for x in f.readlines()])

stopwords = read_stopwords('common_words')
nonsense = ["==", "--", "..", "__", "@"]
stemmer = SnowballStemmer('english')

def check_nonsense(word):
    for badWord in nonsense:
        if badWord in word:
            return False
    return True

def read_docs(file):
    '''
    Reads the corpus into a list of Documents
    '''
    docs = []  # empty 0 index
    with open(file) as f:
        i = 0
        label = ""
        sender = ""
        subject = []
        hour = ""
        for line in f:
            line = line.strip()
            if line.startswith('.I'):
                i = int(line[3:])
            elif line.startswith('.L'):
                label = int(line[3:])
            elif line.startswith('.F'):
                if "<" in line and ">" in line:
                    sender = line[3:].split("<")[1].split(">")[0]
                else:
                    sender = line[3:]
            elif line.startswith('.S'):
                for word in line[3:].split():
                    if check_nonsense(word):
                        subject.append(word.lower())
            elif line.startswith('.D'):
                hour = line[3:].split()[4][0:2]
                docs.append(Document(i, label, sender, subject, hour, [], {}))
                subject = []
            elif line != '.M':
                for word in line.split():
                    if check_nonsense(word):
                        docs[i].text.append(word.lower())

    return docs


def stem_doc(doc: Document):
    return Document(doc.doc_id, doc.label ,doc.sender, doc.subject, doc.hour, [stemmer.stem(word) for word in doc.text], {})

def stem_docs(docs: List[Document]):
    return [stem_doc(doc) for doc in docs]

def remove_stopwords_doc(doc: Document):
    return Document(doc.doc_id, doc.label, doc.sender, doc.subject, doc.hour, [word for word in doc.text if word not in stopwords], {})

def remove_stopwords(docs: List[Document]):
    return [remove_stopwords_doc(doc) for doc in docs]



### Term-Document Matrix

def compute_tf(doc: Document):
    vec = defaultdict(float)
    for word in doc.text:
        vec[word] += 1.0
    return dict(vec)  # convert back to a regular dict


def compute_custom(doc: Document):
    vec = defaultdict(float)
    for word in doc.text:
        if "http" in word:
            vec["http"] += 10.0
        elif "linkedin" in word:
            vec["linkedin"] += 10.0
        elif "subscribe" in word:
            vec["subscribe"] += 10.0
        elif "track" in word:
            vec["track"] += 10.0
        elif "mailto" in word:
            vec["mailto"] += 10.0
        else:
            vec[word] += 1.0

    for word in doc.sender:
        vec[word] += 1.0
    for word in doc.subject:
        vec[word] += 10.0
    for word in doc.hour:
        vec[word] += 20.0

    return dict(vec)




### Vector Similarity

def dictdot(x: Dict[str, float], y: Dict[str, float]):
    '''
    Computes the dot product of vectors x and y, represented as sparse dictionaries.
    '''
    keys = list(x.keys()) if len(x) < len(y) else list(y.keys())
    return sum(x.get(key, 0) * y.get(key, 0) for key in keys)

def cosine_sim(x, y):
    '''
    Computes the cosine similarity between two sparse term vectors represented as dictionaries.
    '''
    num = dictdot(x, y)
    if num == 0:
        return 0
    return num / (norm(list(x.values())) * norm(list(y.values())))

def dice_sim(x, y):
    num = dictdot(x, y) * 2
    if num == 0:
        return 0

    return num / (sum(list(x.values())) + sum(list(y.values())))

def jaccard_sim(x, y):
    num = dictdot(x, y)
    if num == 0:
        return 0
    denom = (sum(list(x.values())) + sum(list(y.values())) - num)
    if denom == 0:
        return 1
    return num / denom

def overlap_sim(x, y):
    num = dictdot(x, y)
    if num == 0:
        return 0

    return num / min(sum(list(x.values())), sum(list(y.values())))


### Search

def experiment():
    forums = read_docs('./training/forums.txt')
    personal = read_docs('./training/personal.txt')
    promotions = read_docs('./training/promotions.txt')
    social = read_docs('./training/social.txt')
    updates = read_docs('./training/updates.txt')

    training = forums + personal + promotions + social + updates
    test = read_docs('./test/test_set.txt')
    stem = False
    removestop = False

    processed_training, processed_test = process_docs_and_queries(training, test, stem, removestop, stopwords)


    train_vecs = []
    for doc in processed_training:
        train_vecs.append(Document(doc.doc_id, doc.label, doc.sender, doc.subject, doc.hour, doc.text, compute_custom(doc)))

    test_vecs = []
    for doc in processed_test:
        test_vecs.append(Document(doc.doc_id, doc.label, doc.sender, doc.subject, doc.hour, doc.text, compute_custom(doc)))

    profile_0 = defaultdict(float)
    p0_count = 0.0
    profile_1 = defaultdict(float)
    p1_count = 0.0
    profile_2 = defaultdict(float)
    p2_count = 0.0
    profile_3 = defaultdict(float)
    p3_count = 0.0
    profile_4 = defaultdict(float)
    p4_count = 0.0

    for doc in train_vecs:
        if doc.label == 0:
            p0_count += 1
            for key, value in doc.vector.items():
                profile_0[key] += value
        elif doc.label == 1:
            p1_count += 1
            for key, value in doc.vector.items():
                profile_1[key] += value
        elif doc.label == 2:
            p2_count += 1
            for key, value in doc.vector.items():
                profile_2[key] += value
        elif doc.label == 3:
            p3_count += 1
            for key, value in doc.vector.items():
                profile_3[key] += value
        elif doc.label == 4:
            p4_count += 1
            for key, value in doc.vector.items():
                profile_4[key] += value

    for key, value in profile_0.items():
        profile_0[key] = float(value) / p0_count
    for key, value in profile_1.items():
        profile_1[key] = float(value) / p1_count
    for key, value in profile_2.items():
        profile_2[key] = float(value) / p2_count
    for key, value in profile_3.items():
        profile_3[key] = float(value) / p3_count
    for key, value in profile_4.items():
        profile_4[key] = float(value) / p4_count

    correct = 0.0
    conf_matrix = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]
    for doc in test_vecs:
        sim0 = cosine_sim(doc.vector, profile_0)
        sim1 = cosine_sim(doc.vector, profile_1)
        sim2 = cosine_sim(doc.vector, profile_2)
        sim3 = cosine_sim(doc.vector, profile_3)
        sim4 = cosine_sim(doc.vector, profile_4)

        allSim = [sim0, sim1, sim2, sim3, sim4]
        '''
        print(doc.text)
        print(doc.label)
        print(allSim)
        print()
        '''
        maxSim = max(allSim)
        if sim0 == maxSim:
            conf_matrix[doc.label][0] += 1
            if doc.label == 0:
                correct += 1
            else:
                print_wrong(doc.vector, doc.label, 0, allSim)
        elif sim1 == maxSim:
            conf_matrix[doc.label][1] += 1
            if doc.label == 1:
                correct += 1
            else:
                print_wrong(doc.vector, doc.label, 1, allSim)
        elif sim2 == maxSim:
            conf_matrix[doc.label][2] += 1
            if doc.label == 2:
                correct += 1
            else:
                print_wrong(doc.vector, doc.label, 2, allSim)
        elif sim3 == maxSim:
            conf_matrix[doc.label][3] += 1
            if doc.label == 3:
                correct += 1
            else:
                print_wrong(doc.vector, doc.label, 3, allSim)
        elif sim4 == maxSim:
            conf_matrix[doc.label][4] += 1
            if doc.label == 4:
                correct += 1
            else:
                print_wrong(doc.vector, doc.label, 4, allSim)


    print("Out of " +str(len(test_vecs))+ " tests "+ str(int(correct))+ " were classified correctly")
    print("Correct: " + str(correct / len(test_vecs)))
    print("Confusion matrix is below. Prediction in each column, actual for each row")
    print("  0  1  2  3  4")
    for i in range(0, len(conf_matrix)):
        print(str(i) + str(conf_matrix[i]))
    print("Key: 0 = forums, 1 = personal, 2 = promotions, 3 = social, 4 = updates")

def print_wrong(text, label, guess, allSim):
    test = ""
    #print(text)
    #print(str(label)+ " != "+ str(guess))
    #print(allSim)

def process_docs_and_queries(docs, queries, stem, removestop, stopwords):
    processed_docs = docs
    processed_queries = queries
    if removestop:
        processed_docs = remove_stopwords(processed_docs)
        processed_queries = remove_stopwords(processed_queries)
    if stem:
        processed_docs = stem_docs(processed_docs)
        processed_queries = stem_docs(processed_queries)
    return processed_docs, processed_queries



if __name__ == '__main__':
    experiment()

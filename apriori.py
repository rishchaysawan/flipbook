# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 11:03:53 2015

@author: rishabh goel
"""
import main
from google.appengine.ext import db

def load_dataset():

    cursor=db.GqlQuery("select * from Transactions")
    dataset=[]

    for c in cursor:
        data=[]
        temp=c.transaction.split('|')
        for t in temp:
            data.append(int(t))

        dataset.append(data)

    return dataset
    
def createC1(transactions):
    c1=[]
    for transaction in transactions:
        for item in transaction:
            if not [item] in c1:
                c1.append([item])
                
    c1.sort() 

    return map(frozenset,c1) 
    
    
def scanD(transactions, candidates, min_support):
    "Returns all candidates that meets a minimum support level"
    sscnt = {}
    for tid in transactions:
        for can in candidates:
            if can.issubset(tid):
                sscnt.setdefault(can, 0)
                sscnt[can] += 1

    num_items = float(len(transactions))
    retlist = []
    support_data = {}
    for key in sscnt:
        support = sscnt[key] / num_items
        if support >= min_support:
            retlist.insert(0, key)
        support_data[key] = support
    return retlist, support_data    
    
    

def aprioriGen(freq_sets, k):
    "Generate the joint transactions from candidate sets"
    retList = []
    lenLk = len(freq_sets)
    for i in range(lenLk):
        for j in range(i + 1, lenLk):
            L1 = list(freq_sets[i])[:k - 2]
            L2 = list(freq_sets[j])[:k - 2]
            L1.sort()
            L2.sort()
            if L1 == L2:
                retList.append(freq_sets[i] | freq_sets[j])
    return retList    

def apriori(transactions, minsupport=0.5):
    "Generate a list of candidate item sets"
    C1 = createC1(transactions)
    D = map(set, transactions)
    L1, support_data = scanD(D, C1, minsupport)
    L = [L1]
    k = 2
    while (len(L[k - 2]) > 0):
        Ck = aprioriGen(L[k - 2], k)
        Lk, supK = scanD(D, Ck, minsupport)
        support_data.update(supK)
        L.append(Lk)
        k += 1

    return L, support_data
    
def generateRules(L, support_data, min_confidence=0.7):
    """Create the association rules
    L: list of frequent item sets
    support_data: support data for those itemsets
    min_confidence: minimum confidence threshold
    """
    rules = []
    for i in range(1, len(L)):
        for freqSet in L[i]:
            H1 = [frozenset([item]) for item in freqSet]
            print "freqSet", freqSet, 'H1', H1
            if (i > 1):
                rules_from_conseq(freqSet, H1, support_data, rules, min_confidence)
            else:
                calc_confidence(freqSet, H1, support_data, rules, min_confidence)
    return rules


def calc_confidence(freqSet, H, support_data, rules, min_confidence=0.7):
    "Evaluate the rule generated"
    pruned_H = []
    print "calc"
    for conseq in H:
        conf = support_data[freqSet] / support_data[freqSet - conseq]
        if conf >= min_confidence:
            print freqSet - conseq, '--->', conseq, 'conf:', conf
            rules.append((freqSet - conseq, conseq, conf))
            pruned_H.append(conseq)
    return pruned_H


def rules_from_conseq(freqSet, H, support_data, rules, min_confidence=0.7):
    "Generate a set of candidate rules"
    print "rules"    
    m = len(H[0])
    print m,freqSet
    if (len(freqSet) > (m + 1)):
        print "should not run"
        Hmp1 = aprioriGen(H, m + 1)
        Hmp1 = calc_confidence(freqSet, Hmp1,  support_data, rules, min_confidence)
        if len(Hmp1) > 1:
            rules_from_conseq(freqSet, Hmp1, support_data, rules, min_confidence)    



checkap="hello"






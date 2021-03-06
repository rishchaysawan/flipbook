import webapp2
import jinja2
import os
import hashlib
import hmac
import random
import string
import urllib2
import urllib
import json
from time import gmtime, strftime
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import users
import datetime
import apriori
import logging
from xml.dom import minidom


SECRET="qwerty"
#URL="https://www.googleapis.com/oauth2/v3/tokeninfo?id_token="
urlReview="http://sentiment.vivekn.com/api/text/"

template_dir=os.path.join(os.path.dirname(__file__),'templates')
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

IP_URL="http://api.hostip.info/?ip="

def get_coords(ip):
    #ip="4.2.2.2"
    #ip="23.24.209.141"
    url=IP_URL+ip
    try:
        content=urllib2.urlopen(url).read()
    except URLError:
        return
    if content:
        d=minidom.parseString(content)
        coords=d.getElementsByTagName('gml:coordinates')
        if coords and coords[0].childNodes[0].nodeValue:
            lon,lat=coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat,lon)

def make_salt():
    return "".join(random.choice(string.letters) for x in range (0,5))

def make_pw_hash(name,pw,salt=None):
    if not salt:
        salt=make_salt()
    h=hashlib.sha256(name+pw+salt).hexdigest()
    return "%s,%s"%(h,salt)

def hash_str(s):
    return hmac.new(SECRET,s).hexdigest()

def make_secure_val(s):
    return "%s|%s"%(s,hash_str(s))

def check_secure_val(h):
    check_value=h.split('|')
    if hash_str(check_value[0])==check_value[1]:
        return check_value[0]
    return None

def valid_pw(name,pw,h):
    salt=h.split(',')[1]
    return h==make_pw_hash(name,pw,salt)

def get_js(token):
    url=URL+token
    try:
        content=urllib2.urlopen(url).read()
    except URLError:
        return
    if content:
        dictionary=json.loads(content)
        return dictionary["name"],dictionary["email"]


class Location(db.Model):
    coords=db.GeoPtProperty()
    ip=db.StringProperty()

class Customer(db.Model):
    email=db.StringProperty(required=True)
    name=db.StringProperty(required=True)
    password=db.StringProperty(required=True)
    profilepic=db.BlobProperty()
    institution=db.StringProperty()
    friend_count=db.IntegerProperty(default=0)

class Products(db.Model):
    category=db.StringProperty(required=True)
    subcategory=db.StringProperty(required=True)
    name=db.StringProperty(required=True)
    price=db.IntegerProperty(required=True)
    brand=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    info=db.TextProperty(required=True)
    image=db.BlobProperty()
    discount=db.IntegerProperty(required=True)

class Order(db.Model):
    email=db.StringProperty(required=True)
    product_id=db.ReferenceProperty(Products)
    product_name=db.StringProperty(required=True)
    date_of_order=db.DateTimeProperty(auto_now_add=True)
    date_of_delivery=db.DateProperty(required=True)
    status=db.StringProperty(required=True)
    contact=db.StringProperty(required=True)
    address=db.TextProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    price=db.IntegerProperty(required=True)

class Cart(db.Model):
    product_id=db.ReferenceProperty(Products)
    email=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    price=db.IntegerProperty(required=True)
    product_name=db.StringProperty(required=True)
    actual_price=db.IntegerProperty(required=True)
    discount=db.IntegerProperty(required=True)
    
class Rating(db.Model):
    product_id=db.ReferenceProperty(Products)
    count=db.IntegerProperty(required=True)
    rating=db.FloatProperty(required=True)
    product_name=db.StringProperty(required=True)

class Bool_rating(db.Model):
    review_by=db.StringProperty(required=True)
    customerId=db.ReferenceProperty(Customer)
    product_id=db.ReferenceProperty(Products)
    rating=db.IntegerProperty(required=True)
    review=db.TextProperty(required=True)
    subject=db.TextProperty(required=True)
    time=db.DateTimeProperty(auto_now_add=True)
    reviewType=db.BooleanProperty()

class Query(db.Model):
    question=db.TextProperty(required=True)
    subject=db.TextProperty(required=True)
    asked_by=db.StringProperty(required=True)
    product_id=db.ReferenceProperty(Products)
    time=db.DateTimeProperty(auto_now_add=True)
    customerId=db.ReferenceProperty(Customer)
    answer_count=db.IntegerProperty (default=0)

class person(db.Model):
    email=db.StringProperty(required=True)
    friend_email=db.StringProperty(required=True)

class share(db.Model):

    email=db.StringProperty(required=True)
    name=db.StringProperty(required=True)
    profilepic=db.BlobProperty(required=True)
    shared_post=db.StringProperty(required=True)
    time=db.DateTimeProperty(auto_now_add=True) 
    shared_image=db.BlobProperty()

class sell(db.Model):

    email=db.StringProperty(required=True)
    name=db.StringProperty(required=True)
    profilepic=db.BlobProperty(required=True)
    sell_post=db.TextProperty(required=True)
    price=db.IntegerProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    sell_image=db.BlobProperty()  

class lastchecknotify(db.Model):
    email=db.StringProperty(required=True)        
    time=db.DateTimeProperty(auto_now_add=True)

class Answer(db.Model):
    answer=db.TextProperty(required=True)
    answered_by=db.StringProperty(required=True)
    question_id=db.ReferenceProperty(Query)
    time=db.DateTimeProperty(auto_now_add=True)
    customerId=db.ReferenceProperty(Customer)

class Transactions(db.Model):
    transaction=db.TextProperty(required=True)

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.write(*a,**kw)
    def render_str(self,template,**params):
        t=jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))

def load_dataset():

    cursor=db.GqlQuery("select * from Transactions")
    dataset=[]

    for c in cursor:
        data=[]
        temp=(str(c.transaction)).split('|')
        for t in temp:
            if len(t):
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




class MainHandler(Handler):
    def get(self):
        sugitems=[]
        message=""
        templist=[]
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+cust.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                identity=self.request.cookies.get('user_id')
                productidentity=self.request.cookies.get('productBought')
                cursor=db.GqlQuery("select * from Order where email = '%s' " %cust.email)
                myorder=cursor.get()
                if identity and productidentity:
                    pro=productidentity.split('|')
                    prolist=[]
                    for p in pro:
                        if len(p)!=0:
                            c=Products.get_by_id(int(p))
                            prolist.append(c)
                    for p in prolist:
                        prodname=p.name
                        prodbrand=p.brand
                        pointr=db.GqlQuery("select * from Products where brand='%(brand)s' AND name!='%(name)s'"%{'brand':prodbrand,'name':prodname})
                        for probrands in pointr:
                            if probrands.name not in templist:
                                sugitems.append(probrands)
                                templist.append(probrands.name)
                    message="suggested items on basis of your order history"
                    identity=str(identity).split('|')[0]
                    info=Customer.get_by_id(int(identity))
                    mail=info.email
                    cursor=db.GqlQuery("select * from person where email= '%s'" %mail)
                    friends=cursor.get()
                    if friends:
                        message="suggested items on basis of your and your friend's order history"
                        for friend in cursor:
                            friend_email=friend.friend_email
                            cu=db.GqlQuery("select * from Order where email = '%s' " %friend_email)
                            friendpurchase=cu.get()
                            if friendpurchase:
                                for m in cu:
                                    prodname=m.product_name
                                    pointr=db.GqlQuery("select * from Products where name='%s'" %prodname)
                                    product=pointr.get()
                                    if product.name not in templist:
                                        sugitems.append(product)
                                        templist.append(product.name)
                    l=len(sugitems)
                    self.render("indexnew.html",l=l,message=message,sugitems=sugitems,greet=greet,logout=logout)
                elif identity and myorder:
                    message="suggested items on basis of your order history"
                    identity=str(identity).split('|')[0]
                    info=Customer.get_by_id(int(identity))
                    mail=info.email
                    for m in cursor:
                        prodname=m.product_name
                        pointr=db.GqlQuery("select * from Products where name='%s'" %prodname)
                        product=pointr.get()
                        prodbrand=product.brand
                        pointr=db.GqlQuery("select * from Products where brand='%(brand)s' AND name!='%(name)s'"%{'brand':prodbrand,'name':prodname})
                        for probrands in pointr:
                            if probrands.name not in templist:
                                sugitems.append(probrands)
                                templist.append(probrands.name)
                    cursor=db.GqlQuery("select * from person where email= '%s'" %mail)
                    friends=cursor.get()
                    if friends:
                        message="suggested items on basis of your and your friend's order history"
                        for friend in cursor:
                            friend_email=friend.friend_email
                            cu=db.GqlQuery("select * from Order where email = '%s' " %friend_email)
                            friendpurchase=cu.get()
                            if friendpurchase:
                                for m in cu:
                                    prodname=m.product_name
                                    pointr=db.GqlQuery("select * from Products where name='%s'" %prodname)
                                    product=pointr.get()
                                    if product.name not in templist:
                                        sugitems.append(product)
                                        templist.append(product.name)
                    l=len(sugitems)
                    self.render("indexnew.html",l=l,message=message,sugitems=sugitems,greet=greet,logout=logout)
                elif identity:
                    message="Your friends bought items"
                    identity=str(identity).split('|')[0]
                    info=Customer.get_by_id(int(identity))
                    mail=info.email
                    cursor=db.GqlQuery("select * from person where email= '%s'" %mail)
                    friends=cursor.get()
                    if friends:
                        for friend in cursor:
                            friend_email=friend.friend_email
                            cu=db.GqlQuery("select * from Order where email = '%s'" %friend_email)
                            friendpurchase=cu.get()
                            if friendpurchase:
                                for m in cu:
                                    prodname=m.product_name
                                    pointr=db.GqlQuery("select * from Products where name='%s'" %prodname)
                                    product=pointr.get()
                                    if product.name not in templist:
                                        sugitems.append(product)
                                        templist.append(product.name)
                    l=len(sugitems)
                    self.render("indexnew.html",l=l,message=message,sugitems=sugitems,greet=greet,logout=logout)    
                else:#This case may never be used
                    message='Connect with people on flipbook to get suggestions'
                    self.render("indexnew.html",l=0,message=message,sugitems=sugitems,greet=greet,logout=logout)
            else:
                greet='<a href="/login">login/signup</a>'
                productidentity=self.request.cookies.get('productBought')
                if productidentity:
                    pro=productidentity.split('|')
                    prolist=[]
                    for p in pro:
                        if len(p)!=0:
                            c=Products.get_by_id(int(p))
                            prolist.append(c)
                    for p in prolist:
                        prodname=p.name
                        prodbrand=p.brand
                        pointr=db.GqlQuery("select * from Products where brand='%(brand)s' AND name!='%(name)s'"%{'brand':prodbrand,'name':prodname})
                        for probrands in pointr:
                            if probrands.name not in templist:
                                sugitems.append(probrands)
                                templist.append(probrands.name)
                    message="Suggested items on basis of your history"
                    l=len(sugitems)
                    self.render("indexnew.html",l=l,message=message,sugitems=sugitems,greet=greet,logout=logout)
                else:
                    message='<a href="/login">Join Flipbook</a> & connect with people on flipbook to get suggestions'
                    self.render("indexnew.html",l=-1,message=message,sugitems=sugitems,greet=greet)
        else:
            greet='<a href="/login">login/signup</a>'
            productidentity=self.request.cookies.get('productBought')
            if productidentity:
                pro=productidentity.split('|')
                prolist=[]
                for p in pro:
                    if len(p)!=0:
                        c=Products.get_by_id(int(p))
                        prolist.append(c)
                for p in prolist:
                    prodname=p.name
                    prodbrand=p.brand
                    pointr=db.GqlQuery("select * from Products where brand='%(brand)s' AND name!='%(name)s'"%{'brand':prodbrand,'name':prodname})
                    for probrands in pointr:
                        if probrands.name not in templist:
                            sugitems.append(probrands)
                            templist.append(probrands.name)
                message="Suggested items on basis of your history"
                l=len(sugitems)
                self.render("indexnew.html",l=l,message=message,sugitems=sugitems,greet=greet)
            else:
                message='<a href="/login">Join Flipbook</a> & connect with people on flipbook to get recommendations'
                self.render("indexnew.html",l=-1,message=message,sugitems=sugitems,greet=greet)

    #NO POST handler required in index page since a new search page
    def post(self):
        search=self.request.get('search')
        if search:
            #self.render("index.html",message=message,sugitems=sugitems)
            self.write("<p></p>")
            info=search.split()
            cursor=db.GqlQuery("select * from Products")
            showitems=[]
            uniqueshowitems=[]
            uniqueid=[]
            for i in range(len(info)):
                content=info[i]
                for c in cursor:
                    match=c.name.split()
                    for j in range(len(match)):
                        if content.lower()==match[j].lower():
                            showitems.append(c)
                            break   
            for item in showitems:
                if item.key().id() not in uniqueid:
                    uniqueshowitems.append(item)
                    uniqueid.append(item.key().id())    
            if uniqueshowitems:
                for showitem in uniqueshowitems:
                    self.write(showitem.name)
                    self.write("<br>")
            else:
                self.write("No Result Found <br>")

class LoginHandler(Handler):
    def get(self):
        self.render("login.html")

class LoginWithEmail(Handler):
    def write_form(self,name="",password="",userExists="",greet='<a href="/login">login/signup</a>'):
        self.render("loginWithEmail.html",name=name,password=password,UserExists=userExists,greet=greet)
    def get(self):
        self.write_form()
    def post(self):
        username=self.request.get('username')
        password=self.request.get('password')
        errorPassword=""
        username=str(username)
        password=str(password)
        cursor=db.GqlQuery("Select * from Customer  where name = '%s'"%username)
        c_value=cursor.get()
        if c_value:
            h_value=c_value.password
            if valid_pw(username,password,h_value):
                user_id=c_value.key().id()
                user_id=str(user_id)
                id_to_send=make_secure_val(user_id)
                self.response.headers.add_header('Set-Cookie','user_id=%s'%id_to_send)
                self.redirect("/")
            else:
                self.write_form(name=username,password=password,userExists="Incorrect Password")
        else:
            password=""
            self.write_form(name=username,password=password,userExists="User Does Not Exist")

class Sellers(Handler):
    def write_form(self):
        self.render("sellers.html")
    def get(self):
        self.write_form()
    def post(self):
        category=self.request.get('category')
        subcategory=self.request.get('subcategory')
        name=self.request.get('name')
        brand=self.request.get('brand')
        price=int(self.request.get('price'))
        quantity=int(self.request.get('quantity'))
        discount=int(self.request.get('discount'))
        info=self.request.get('info')
        image=self.request.get('fileToUpload')
        obj=Products(category=category,subcategory=subcategory,name=name,brand=brand,price=price,quantity=quantity,discount=discount,image=image,info=info)
        obj.put()
        self.redirect('/')

class Show(Handler):
    def get(self):
        product_id=self.request.get('pid')
        c=Products.get_by_id(int(product_id))
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.image)

class ShowFriends(Handler):
    def get(self):
        product_id=self.request.get('pid')
        c=Customer.get_by_id(int(product_id))
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.profilepic)        

class FriendPic(Handler):
    def get(self):
        emailid=self.request.get('eid')
        cursor=db.GqlQuery("select * from Customer where email ='%s'" %emailid)
        for c in cursor:
            self.response.headers['Content-Type'] = 'image/jpg'
            self.write(c.profilepic) 

class ShowsharedPosts(Handler):

    def get(self):
        postid=self.request.get('pid')
        c=share.get_by_id(int(postid))
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.shared_image) 

class ShowsellPosts(Handler):

    def get(self):
        postid=self.request.get('pid')
        self.write(postid)
        c=sell.get_by_id(int(postid))
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.sell_image)        
friendspost=[]
friendssell=[]
class NewsHandler(Handler):
    def get(self):
        fpost=[]
        fsell=[]
        error=""
        youmayknow=[]
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                user=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+user.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                if (user.institution):
                    cursor=db.GqlQuery("Select * from Customer where institution ='%(institution)s'  AND email != '%(email)s' " %{'institution':user.institution,'email':user.email})
                    check=cursor.get()
                    if check:
                        for c in cursor:
                            insemail=c.email
                            pointr=db.GqlQuery("select * from person where friend_email='%(fmail)s' AND email = '%(email)s'" %{'fmail':insemail,'email':user.email})
                            p=pointr.get()
                            if not p:
                                youmayknow.append(c)
                    else:
                        cursor=db.GqlQuery("Select * from Customer  where email != '%s' limit 10 "% user.email)
                        check=cursor.get()
                        if check:
                            for c in cursor:
                                insemail=c.email
                                pointr=db.GqlQuery("select * from person where friend_email='%(fmail)s' AND email = '%(email)s'" %{'fmail':insemail,'email':user.email})
                                p=pointr.get()
                                if not p:
                                    youmayknow.append(c)
                else:
                    error="Please add institution"
                
                cursor=db.GqlQuery("select * from person where email='%s'" %user.email)
                checkfriend=cursor.get()
                if checkfriend:
                    for friend in cursor:
                        pointr=db.GqlQuery("select * from share where email='%s'" %friend.friend_email)
                        checkfrndshare=pointr.get()
                        if checkfrndshare:
                            for purchase in pointr:
                                fpost.append(purchase)
                    for friend in cursor:
                        pointr=db.GqlQuery("select * from sell where email='%s'" %friend.friend_email)
                        checkfrndsell=pointr.get()
                        if checkfrndsell:
                            for purchase in pointr:
                                fsell.append(purchase)
                self.render("newsfeed.html",user=user,friendspost=fpost,friendssell=fsell,error=error,youmayknow=youmayknow,greet=greet,logout=logout)
            else:
                self.redirect("/login")
        else:
            self.redirect("/login")

    def post(self):
        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        email=user.email
        friend_email=self.request.get('submit')
        #friend_id=friends_id.split()
        obj=person(email=email,friend_email=friend_email)
        obj.put()
        user.friend_count+=1
        user.put()
        self.redirect('/newsfeed')

class NotifyHandler(Handler):
    def get(self):
        friendspost=[]
        friendssell=[]
        youmayknow=[]
        error=""
        yourorder=[]
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                user=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+user.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                email=user.email
                if (user.institution):
                    cursor=db.GqlQuery("Select * from Customer where institution ='%(institution)s'  AND email != '%(email)s' " %{'institution':user.institution,'email':user.email})
                    check=cursor.get()
                    if check:
                        for c in cursor:
                            insemail=c.email
                            pointr=db.GqlQuery("select * from person where friend_email='%(fmail)s' AND email = '%(email)s'" %{'fmail':insemail,'email':user.email})
                            p=pointr.get()
                            if not p:
                                youmayknow.append(c)
                    else:
                        cursor=db.GqlQuery("Select * from Customer  where email != '%s' limit 10 "% user.email)    
                        youmayknow=cursor
                else:
                    error="Please add institution"
                cursor=db.GqlQuery("select * from person where email='%s'" %user.email)
                checkfriend=cursor.get()
                if checkfriend:
                    for friend in cursor:
                        pointr=db.GqlQuery("select * from share where email='%s'" %friend.friend_email)
                        checkfrndshare=pointr.get()
                        if checkfrndshare:
                            for purchase in pointr:
                                friendspost.append(purchase)
                    for friend in cursor:
                        pointr=db.GqlQuery("select * from sell where email='%s'" %friend.friend_email)
                        checkfrndsell=pointr.get()
                        if checkfrndsell:
                            for purchase in pointr:
                                friendssell.append(purchase)  
                cursor=db.GqlQuery("select * from lastchecknotify where email = '%s'" %email)
                c=cursor.get()
                if c:
                    db.delete(c.key())
                    obj=lastchecknotify(email=email)
                    obj.put()
                else:
                    obj=lastchecknotify(email=email)
                    obj.put()
                cursor=db.GqlQuery("select * from Order where email='%s'" %email)
                c=cursor.get()
                if c:
                    for yourord in cursor:
                        yourorder.append(yourord)    

                self.render("notification.html",user=user,friendspost=friendspost,friendssell=friendssell,yourorder=yourorder,greet=greet,logout=logout)        
                        

            else:
                self.redirect("/login")
        else:
                self.redirect("/login")

class ShareHandler(Handler):
    def post(self):
        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        email=user.email
        name=user.name
        profilepic=user.profilepic
        shared_post=self.request.get('info')
        shared_image=self.request.get('fileToUpload')
        obj=share(email=email,name=name,profilepic=profilepic,shared_post=shared_post,shared_image=shared_image)
        obj.put() 
        self.redirect('/newsfeed')

class SellHandler(Handler):
    def post(self):
        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        email=user.email
        name=user.name
        profilepic=user.profilepic
        sell_post=self.request.get('info')
        price=int(self.request.get('price'))
        quantity=int(self.request.get('quantity'))
        sell_image=self.request.get('fileToUpload')
        obj=sell(email=email,name=name,profilepic=profilepic,sell_post=sell_post,price=price,quantity=quantity,sell_image=sell_image)
        obj.put() 
        self.redirect('/newsfeed')

class SignupHandler(Handler):
    def write_form(self,institution="",errorConfirm="",name="",password="",confirm="",mail="",userExists="",greet='<a href="/login">login/signup</a>'):
        self.render("signup.html",institution=institution,greet=greet,errorConfirm=errorConfirm,name=name,password=password,confirm=confirm,mail=mail,userExists=userExists)
    def get(self):
        self.write_form()
    def post(self):
        username=self.request.get('username')
        password=self.request.get('password')
        confirm_password=self.request.get('confirm_password')
        mail=self.request.get('email')
        institution=self.request.get('institution')
        profilepic=self.request.get('fileToUpload')
        errorMail=""
        errorUser=""
        errorConfirm=""
        errorPassword=""
        if confirm_password!=password:
            errorConfirm="Password didn't match"
            confirm_password=""
            password=""
        if  errorConfirm:
            self.write_form(institution=institution,errorConfirm=errorConfirm,name=username,password=password,confirm=confirm_password,mail=mail)
        else:
            username=str(username)
            password=str(password)
            mail=str(mail)
            cursor=db.GqlQuery("Select * from Customer  where email = '%s'"%mail)
            if cursor.get():
                password=""
                confirm_password=""
                self.write_form(institution,errorConfirm,username,password,confirm_password,mail,"Please enter different email")
            else:
                h_password=make_pw_hash(username,password)
                obj=Customer(name=username,password=h_password,email=mail,profilepic=profilepic,institution=institution)
                obj.put()
                user_id=obj.key().id()
                user_id=str(user_id)
                id_to_send=make_secure_val(user_id)
                self.response.headers.add_header('Set-Cookie','user_id=%s'%id_to_send)
                self.redirect("/")

class TestHandler(Handler):
    def get(self):
        self.render("test.html")

class ProductHandler(Handler):
    def get(self):
        product_id=self.request.get('pid')
        cursor=Products.get_by_id(int(product_id))
        cursorQuery=db.GqlQuery("SELECT * FROM Query")
        cursorAnswer=db.GqlQuery("SELECT * FROM Answer")
        cursorReview=db.GqlQuery("SELECT * FROM Bool_rating")
        cursorRating=db.GqlQuery("SELECT * FROM Rating WHERE product_name='%s'"%cursor.name)
        check=cursorRating.get()
        rate=""
        if check:
            rate=str(check.rating)+"/5"
        else:
            rate="No Ratings Available"
        image=cursor.image
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+cust.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                self.render("product.html",rate=rate,cursorReview=cursorReview,temp=1,greet=greet,cursorAnswer=cursorAnswer,logout=logout,quantity=1,pid=product_id,cursor=cursor,cursorQuery=cursorQuery,condition=cursor.key(),image=image)
            else:
                greet='<a href="/login">login/signup</a>'
                self.render("product.html",rate=rate,cursorReview=cursorReview,temp=0,greet=greet,cursorAnswer=cursorAnswer,quantity=1,pid=product_id,cursor=cursor,cursorQuery=cursorQuery,condition=cursor.key(),image=image)
        else:
            greet='<a href="/login">login/signup</a>'
            self.render("product.html",rate=rate,cursorReview=cursorReview,temp=0,greet=greet,cursorAnswer=cursorAnswer,quantity=1,pid=product_id,cursor=cursor,cursorQuery=cursorQuery,condition=cursor.key(),image=image)

    #Query
    def post(self):
        query=self.request.get('query')
        product_id=self.request.get('pid')
        product=Products.get_by_id(int(product_id))
        q=Query(question=query,product_id=product.key())
        q.put()
        self.redirect('/')


class ReviewHandler(Handler):
    def get(self):
        self.redirect("/")
    def post(self):
        subject=self.request.get('subject')
        review=self.request.get('review')
        rating=int(self.request.get('rating'))
        product_id=self.request.get('pid')
        url="product?pid="+product_id
        product_id=int(product_id)
        product=Products.get_by_id(product_id)
        user_id=self.request.cookies.get('user_id')
        form_fields={"txt":review}
        form_data = urllib.urlencode(form_fields)
        result = urlfetch.fetch(url=urlReview,payload=form_data,method=urlfetch.POST, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        d=json.loads(result.content)
        s=False
        if d["result"]["sentiment"]=="Negative":
            s=False
        else:
            s=True
        reviewType=s
        if user_id:
            result=check_secure_val(user_id)
            if result:
                check=db.GqlQuery("SELECT * FROM Rating WHERE product_name='%s'"%product.name)
                c=check.get()
                if c:
                    temp=(c.rating*c.count)+rating
                    c.count+=1
                    temp=temp/c.count
                    c.rating=temp
                    c.put()
                else:
                    temp=Rating(product_name=product.name,product_id=product.key(),count=1,rating=float(rating))
                    temp.put()
                cust=Customer.get_by_id(int(result))
                review_by=cust.name
                r=Bool_rating(review_by=review_by,rating=rating,review=review,subject=subject,customerId=cust.key(),product_id=product.key(),reviewType=reviewType)
                r.put()
                self.redirect("/%s"%url)
            else:
                self.redirect("/login")
        else:
            self.redirect("/login")

class showProducts(Handler):
    def get(self):
        sublist=[]
        subcategory=self.request.get('subcategory')
        cursor=db.GqlQuery("SELECT * from Products where subcategory = '%s'" %subcategory)
        c=cursor.get()
        if c:
            for c in cursor:
                sublist.append(c)
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+cust.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                self.render("showProducts.html",sublist=sublist,greet=greet,logout=logout)
            else:
                greet='<a href="/login">login/signup</a>'
                self.render("showProducts.html",sublist=sublist,greet=greet)
        else:
            greet='<a href="/login">login/signup</a>'
            self.render("showProducts.html",sublist=sublist,greet=greet)          


class BackendHandler(Handler):
    def get(self):
        token=self.request.get('token')
        name,email=get_js(token)
        self.write(name) 

class AnswerHandler(Handler):
    def get(self):
        self.redirect("/")
    def post(self):
        question_id=self.request.get('qid')
        # convert this into correct format--COMPLETE
        product_id=self.request.get('pid')
        #make url for correct redirection--COMPLETE
        url="product?pid="+product_id
        answer=self.request.get('answer')
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                #convert in correct format--DONE
                answered_by=cust.name
                q=Query.get_by_id(int(question_id))
                q.answer_count+=1
                q.put()
                a=Answer(answer=answer,answered_by=answered_by,question_id=q.key(),customerId=cust.key())
                a.put()
                self.redirect("/%s"%url)
            else:
                self.redirect("/")
        else:
            self.redirect("/")
    

class ShowCart(Handler):
    def get(self):
        user_id=self.request.cookies.get('user_id')        
        if user_id:
            result=check_secure_val(user_id)
            if result:
                user=Customer.get_by_id(int(result))
                cursor=db.GqlQuery("SELECT * FROM Cart")
                total=0
                count=0
                for c in cursor:
                    if c.email==user.email:
                        total+=c.price
                        count+=1
                greet='<a href="/profile">Hello, '+user.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                email=user.email
                cursor=db.GqlQuery("SELECT * FROM Cart WHERE email='%s'"%email)
                inputitem=[]
                for c in cursor:
                    pid=c.product_id.key().id()
                    inputitem.append(pid)
                dataset=load_dataset()    
                minsupport=0.5
                min_confidence=0.5
                l,support_data=apriori(dataset,minsupport)
                rules=generateRules(l,support_data,min_confidence)
                recommend=[]
                ch=frozenset(inputitem)
                for result in rules:
                    if result[0]==ch: 
                        for temp in list(result[1]):
                            if not temp in recommend:
                                recommend.append(temp) 
                self.render("cart.html",error="Empty Cart",count=count,greet=greet,logout=logout,cursor=cursor,user=user,total=total,recommend=recommend)
            else:
                self.redirect("/login")
        else:
            self.redirect("/login")

    def post(self):
        pid=self.request.get('pid')
        quantity=int(self.request.get('quantity'))
        product=Products.get_by_id(int(pid))
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+cust.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                if quantity>product.quantity:
                    self.render("cart.html",error="quantity Not Available",total=0,greet=greet,logout=logout)
                else:
                    user=Customer.get_by_id(int(result))
                    email=user.email
                    actual_price=product.price
                    discount=product.discount
                    price=(product.price)-(((product.discount)*product.price)/100)
                    product_id=product.key()
                    price=price*quantity
                    cart=Cart(product_name=product.name,product_id=product_id,discount=discount,actual_price=actual_price,error="",email=email,price=price,quantity=quantity)
                    cart.put()
                    self.redirect("/showcart")
                    #cursor=db.GqlQuery("SELECT * FROM Cart")
                    #total=0
                    #for c in cursor:
                        #if c.email==user.email:
                            #total+=(c.price)
                    #self.render("cart.html",cursor=cursor,user=user,total=total,greet=greet,logout=logout)
            else:
                self.redirect("/login")
        else:
            self.redirect("/login")

class Checkout(Handler):
    def get(self):
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                cust=Customer.get_by_id(int(result))
                greet='<a href="/profile">Hello, '+cust.name+'</a>'
                logout='<a href="/logout">LOGOUT</a>'
                self.render("Checkout.html",greet=greet,logout=logout)
            else:
                self.redirect("/")
        else:
            self.redirect("/")
    def post(self):
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                contact=self.request.get('contact')
                address=self.request.get('address')
                user=Customer.get_by_id(int(result))
                email=user.email
                cursor=db.GqlQuery("SELECT * FROM Cart WHERE email='%s'"%email)
                cookies=""
                for c in cursor:
                    pid=c.product_id.key().id()
                    cookies=cookies+str(pid)+"|"
                    product=Products.get_by_id(pid)
                    product.quantity=product.quantity-c.quantity
                    product.put()
                    product_id=c.product_id
                    product_name=product.name
                    date_of_delivery=datetime.date.today()+datetime.timedelta(7)
                    status="Your Order Has Been Placed. Thanks for choosing Flipbook"
                    obj=Order(price=(c.price*c.quantity),product_name=product_name,quantity=c.quantity,email=email,date_of_delivery=date_of_delivery,product_id=product_id,status=status,contact=contact,address=address)
                    obj.put()
                    c.delete()
                temp=Transactions(transaction=cookies)
                temp.put()
                self.response.set_cookie('productBought','%s'%cookies,expires=datetime.datetime.now()+datetime.timedelta(365))
                ip=str(self.request.remote_addr)
                coords=get_coords(self.request.remote_addr)
                c=db.GqlQuery("SELECT * FROM Location WHERE ip='%s'"%ip)
                check=c.get()
                if not check:
                    a=Location(coords=coords,ip=ip)
                    a.put()
                self.redirect("/")
            else:
                self.redirect("/")
        else:
            self.redirect("/")
        
class LogoutHandler(Handler):
    def get(self):
        self.response.headers.add_header("Set-Cookie","user_id=")
        self.redirect("/")

class ProfilePicHandler(Handler):
    def get(self):
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                c=Customer.get_by_id(int(result))
                self.response.headers['Content-Type'] = 'image/jpg'
                self.write(c.profilepic)
            else:
                self.redirect("/")
        else:
            self.redirect("/")

class ProfileHandler(Handler):
    def get(self):
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                c=Customer.get_by_id(int(result))
                self.response.headers['Content-Type'] = 'image/jpg'
                self.write(c.profilepic)
            else:
                self.redirect("/")
        else:
            self.redirect("/")

app = webapp2.WSGIApplication([
    ('/', MainHandler),('/login',LoginHandler),('/loginEmail',LoginWithEmail),
    ('/signup',SignupHandler),('/newsfeed',NewsHandler),('/sellers',Sellers),('/show',Show),
    ('/test',TestHandler),('/backend',BackendHandler),('/product',ProductHandler),('/sell',SellHandler),
    ('/answer',AnswerHandler),('/share',ShareHandler),('/showsharedposts',ShowsharedPosts),
    ('/showsellposts',ShowsellPosts),('/friendpic',FriendPic),('/notify',NotifyHandler),
    ('/showfriends',ShowFriends),('/showproducts',showProducts),('/showcart',ShowCart),('/checkout',Checkout),
    ('/logout',LogoutHandler),('/profile',ProfileHandler),('/showprofilepic',ProfilePicHandler),('/review',ReviewHandler)
], debug=True)

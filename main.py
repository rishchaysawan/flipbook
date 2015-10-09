import webapp2
import jinja2
import os
import hashlib
import hmac
import random
import string
import urllib2
import json

from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import users
SECRET="qwerty"
URL="https://www.googleapis.com/oauth2/v3/tokeninfo?id_token="

template_dir=os.path.join(os.path.dirname(__file__),'templates')
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

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
    date_of_production=db.DateTimeProperty(required=True)
    date_of_delivery=db.DateTimeProperty(required=True)
    status=db.StringProperty(required=True)
    contact=db.IntegerProperty(required=True)
    address=db.StringProperty(required=True)


class Cart(db.Model):
    product_id=db.ReferenceProperty(Products)
    email=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    price=db.IntegerProperty(required=True)
    

class Rating(db.Model):
    product_id=db.ReferenceProperty(Products)
    count=db.IntegerProperty(required=True)
    rating=db.IntegerProperty(required=True)


class Bool_rating(db.Model):
    email=db.StringProperty(required=True)
    product_id=db.ReferenceProperty(Products)
    rating=db.IntegerProperty(required=True)
    review=db.StringProperty(required=True)

class Query(db.Model):
    question=db.StringProperty(required=True)
    product_id=db.ReferenceProperty(Products)

class person(db.Model):
    email=db.StringProperty(required=True)
    friend_email=db.StringProperty(required=True)

class share(db.Model):
    email=db.StringProperty(required=True)
    shared_post=db.StringProperty(required=True)
    time=db.DateTimeProperty(auto_now_add=True) 
    shared_image=db.BlobProperty()

class sell(db.Model):
    email=db.StringProperty(required=True)
    sell_post=db.StringProperty(required=True)
    price=db.StringProperty(required=True)
    quantity=db.StringProperty(required=True)
    sell_image=db.BlobProperty()   

class notification(db.Model):
    product_id=db.ReferenceProperty(Products)
    notification_product=db.StringProperty(required=True)          

class Answer(db.Model):
    answer=db.StringProperty(required=True)
    question_id=db.ReferenceProperty(Query)

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.write(*a,**kw)
    def render_str(self,template,**params):
        t=jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))

message=""
sugitems=[]  

class MainHandler(Handler):

    global message
    global sugitems

    def get(self):

        identity=self.request.cookies.get('user_id')
        productidentity=self.request.cookies.get('product_id')

        if identity and productidentity:

            message="suggested items on basis of your and your's frinds history"
            identity=str(identity).split('|')[0]
            info=Customer.get_by_id(int(identity))
            mail=info.email

            cursor=db.GqlQuery("select * from Order where email = '%s' " %mail)
            myorder=cursor.get()

            if myorder:
                for myorder in cursor:
                    prodid=myorder.product_id
                    pointr=db.GqlQuery("select * from Products where product_id='%s'" %prodid)
                    product=ponter.get()
                    prodbrand=product.brand
                    pointr=db.GqlQuery("select * from products where brand='%s'" %prodbrand)

                    for probrands in pointr:
                        sugitems.append(probrands.product_id)


            cursor=db.GqlQuery("select * from person where email= '%s'" %mail)
            friends=cursor.get()

            if friends:
                for friend in friends:
                    friend_email=friend.friend_email
                    cursor=db.GqlQuery("select * from Order where email = '%s' " %friend_email)
                    friendpurchase=cursor.get()

                    if friendpurchase:
                        for items in cursor:
                            sugitems.append(items.product_id)



            self.render("index.html",sugitems=sugitems)


        elif identity:

            message="your friends bought items"
            identity=str(identity).split('|')[0]
            info=Customer.get_by_id(int(identity))
            mail=info.email

            cursor=db.GqlQuery("select * from person where email= '%s'" %mail)
            friends=cursor.get()

            if friends:
                for friend in cursor:
                    friend_email=friend.friend_email
                    cursor=db.GqlQuery("select * from Order where email = '%s' " %friend_email)
                    friendpurchase=cursor.get()

                    if friendpurchase:
                        for items in cursor:
                            sugitems.append(items.product_id)



                self.render("index.html",sugitems=sugitems)

            else:
                message="connect with friends to see what they bought"
                self.render("index.html",message=message,sugitems=sugitems)     


        else:
            
            message="create id and connect with people on flipbook to get suggestions"    

            self.render("index.html",message=message,sugitems=sugitems)
        

    def post(self):


        search=self.request.get('search')

        if search:
            self.render("index.html",message=message,sugitems=sugitems)
            #self.write(search)
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
    def write_form(self,name="",password="",userExists=""):
        self.render("loginWithEmail.html",name=name,password=password,userExists=userExists)
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
                self.redirect("/newsfeed")
        else:
            password=""
            self.write_form(username,password,"User Not Exists")

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
    def write_form(self):
        self.render("sellers.html")
    def get(self):
        product_id=self.request.get('pid')
        c=Products.get_by_id(int(product_id))
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.image)


class NewsHandler(Handler):
    def get(self):
       
        friendspost=[]
        friendssell=[]
        error=""
        youmayknow=[]

        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                
                user=Customer.get_by_id(int(result))
                self.write('<h2>Welcome</h2><br>')
                self.write(user.email)
                if (user.institution):
                    cursor=db.GqlQuery("Select * from Customer where institution ='%(institution)s'  AND email != '%(email)s' " %{'institution':user.institution,'email':user.email})
                    check=cursor.get()

                    if check:
                        for c in cursor:
                            insemail=c.email
                            pointr=db.GqlQuery("select * from person where friend_email='%s'" %insemail)
                            p=pointr.get()
                            if not p:
                                youmayknow.append(c)
                            

                    else:
                        self.write("yup")
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
                        
                        pontr=db.GqlQuery("select * from sell where email='%s'" %friend.friend_email)
                        checkfrndsell=pointr.get()
                        if checkfrndsell:
                            for purchase in pointr:
                                friendssell.append(purchase)            

                
                self.render("newsfeed.html",friendspost=friendspost,friendssell=friendssell,error=error,youmayknow=youmayknow)
            else:
                self.redirect("/")
        else:
                self.redirect("/")

    def post(self):
        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        
        email=user.email
        friends_id=self.request.get('submit')
        friend_id=friends_id.split()

        obj=person(email=email,friend_email=friend_id[1]);
        obj.put()

        self.redirect('/newsfeed')

class ShareHandler(Handler):
    def post(self):

        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        
        email=user.email
        shared_post=self.request.get('info')
        shared_image=self.request.get('fileToUpload')
        obj=share(email=email,shared_post=shared_post,shared_image=shared_image)
        obj.put() 
        self.redirect('/newsfeed')  

class SellHandler(Handler):
    def post(self):

        user_id=self.request.cookies.get('user_id')
        result=check_secure_val(user_id)
        user=Customer.get_by_id(int(result))
        
        email=user.email
        sell_post=self.request.get('info')
        price=self.request.get('price')
        quantity=self.request.get('quantity')
        sell_image=self.request.get('fileToUpload')

        obj=sell(email=email,sell_post=sell_post,price=price,quantity=quantity,sell_image=sell_image)
        obj.put() 
        self.redirect('/newsfeed') 

class SignupHandler(Handler):
    def write_form(self,errorConfirm="",name="",password="",confirm="",mail="",userExists=""):
        self.render("signup.html",errorConfirm=errorConfirm,name=name,password=password,confirm=confirm,mail=mail,userExists=userExists)
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
            self.write_form(errorConfirm=errorConfirm,name=username,password=password,confirm=confirm_password,mail=mail)
        else:
            username=str(username)
            password=str(password)
            mail=str(mail)
            cursor=db.GqlQuery("Select * from Customer  where email = '%s'"%mail)
            if cursor.get():
                password=""
                confirm_password=""
                self.write_form(errorConfirm,username,password,confirm_password,mail,"Please enter different email")
            else:
                h_password=make_pw_hash(username,password)
                obj=Customer(name=username,password=h_password,email=mail,profilepic=profilepic,institution=institution)
                obj.put()
                user_id=obj.key().id()
                user_id=str(user_id)
                id_to_send=make_secure_val(user_id)
                self.response.headers.add_header('Set-Cookie','user_id=%s'%id_to_send)
                self.redirect("/newsfeed")

class TestHandler(Handler):
    def get(self):
        self.render("test.html")

class ProductHandler(Handler):
    def get(self):
        product_id=self.request.get('pid')
        cursor=Products.get_by_id(int(product_id))

        cursorQuery=db.GqlQuery("SELECT * FROM Query")
        #self.response.headers['Content-Type']='image/png'
        #self.response.headers.add_header('Content-Type','image/png')
        image=cursor.image
        self.render("product.html",pid=product_id,cursor=cursor,cursorQuery=cursorQuery,condition=cursor.key(),image=image)
        #temp=self.request.headers.get('Content-Type')
        #self.write(temp)
    def post(self):
        query=self.request.get('query')
        product_id=self.request.get('pid')
        product=Products.get_by_id(int(product_id))
        #temp=query+product_id
        #self.write(temp)
        q=Query(question=query,product_id=product.key())
        q.put()
        self.redirect('/')

class showProducts(Handler):
    def get(self):
        sublist=[];
        subcategory=self.request.get('subcategory');
        cursor=db.GqlQuery("SELECT * from Products where subcategory = '%s'" %subcategory);

        c=cursor.get();

        if c:
            for c in cursor:
                sublist.append(c);

        self.render("showProducts.html",sublist=sublist);            

class BackendHandler(Handler):
    def get(self):
        token=self.request.get('token')
        name,email=get_js(token)
        self.write(name)
        #self.render("backend.html",token=token)
            #logging.warn(traceback.format_exc())
        #token=self.request.get('token')
        #self.render("backend.html",token=token)   

class AnswerHandler(Handler):
    def get(self):
        qid=self.request.get('qid')
        cursor=Query.get_by_id(int(qid))
        cursorQuery=db.GqlQuery("SELECT * FROM Answer")
        self.render("answer.html",cursorQuery=cursorQuery,condition=cursor.key())

    def post(self):
        answer=self.request.get('answer')
        question_id=self.request.get('qid')
        query=Query.get_by_id(int(question_id))
        a=Answer(answer=answer,question_id=query.key())
        a.put()
        self.redirect("/")
    
app = webapp2.WSGIApplication([
    ('/', MainHandler),('/login',LoginHandler),('/loginEmail',LoginWithEmail),
    ('/signup',SignupHandler),('/newsfeed',NewsHandler),('/sellers',Sellers),('/show',Show),
    ('/test',TestHandler),('/backend',BackendHandler),('/product',ProductHandler),('/sell',SellHandler),
    ('/answer',AnswerHandler),('/share',ShareHandler),('/showproducts',showProducts),
], debug=True)

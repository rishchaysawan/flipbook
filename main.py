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
    price=db.IntegerProperty(required=True)
    brand=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    info=db.StringProperty(required=True)
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


class cart(db.Model):
    product_id=db.ReferenceProperty(Products)
    email=db.StringProperty(required=True)
    quantity=db.IntegerProperty(required=True)
    price=db.IntegerProperty(required=True)
    

class Rating(db.Model):
    product_id=db.ReferenceProperty(Products)
    count=db.IntegerProperty(required=True)
    rating=db.IntegerProperty(required=True)


class bool_rating(db.Model):
    email=db.StringProperty(required=True)
    product_id=db.ReferenceProperty(Products)
    rating=db.IntegerProperty(required=True)
    review=db.StringProperty(required=True)

class query(db.Model):
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

class notification(db.Model):
    product_id=db.ReferenceProperty(Products)
    notification_product=db.StringProperty(required=True)          

class Handler(webapp2.RequestHandler):
    def write(self,*a,**kw):
        self.response.write(*a,**kw)
    def render_str(self,template,**params):
        t=jinja_env.get_template(template)
        return t.render(params)
    def render(self,template,**kw):
        self.write(self.render_str(template,**kw))

class MainHandler(Handler):
    def get(self):
        self.render("index.html")

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
        brand=self.request.get('brand')
        price=int(self.request.get('price'))
        quantity=int(self.request.get('quantity'))
        discount=int(self.request.get('discount'))
        info=self.request.get('info')
        image=self.request.get('fileToUpload')
        obj=Products(category=category,brand=brand,price=price,quantity=quantity,discount=discount,image=image,info=info)
        obj.put()
        self.redirect('/')

class Show(Handler):
    def write_form(self):
        self.render("sellers.html")
    def get(self):
        cursor=db.GqlQuery("Select * from Customer where name='admin5' ")
        #cursor=db.GqlQuery("Select * from Products where category='temp'")
        c=cursor.get()
        self.response.headers['Content-Type'] = 'image/jpg'
        self.write(c.profilepic)
        #self.write(c.image)

class NewsHandler(Handler):
    def get(self):
        error=""
        user_id=self.request.cookies.get('user_id')
        if user_id:
            result=check_secure_val(user_id)
            if result:
                user=Customer.get_by_id(int(result))
                self.write(user.email)
                if len(user.institution):
                    cursor=db.GqlQuery("Select * from Customer where institution ='%(institution)s'  AND name != '%(name)s' " %{'institution':user.institution,'name':user.name})
                    c=cursor.get()

                    if c:
                        self.render("newsfeed.html",error=error,youmayknow=cursor)

                    else:
                        cursor=db.GqlQuery("Select * from Customer limit 10 ")    
                        self.render("newsfeed.html",error=error,youmayknow=cursor)
                else:
                    error="please add institution"
                    self.render("newsfeed.html",error=error) 
            else:
                self.redirect("/")
        else:
                self.redirect("/")

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
        #self.response.headers['Content-Type']='image/png'
        #self.response.headers.add_header('Content-Type','image/png')
        self.render("product.html",cursor=cursor)

class BackendHandler(Handler):
    def get(self):
        token=self.request.get('token')
        name,email=get_js(token)
        self.write(name)
        #self.render("backend.html",token=token)
            #logging.warn(traceback.format_exc())
        #token=self.request.get('token')
        #self.render("backend.html",token=token)   

app = webapp2.WSGIApplication([
    ('/', MainHandler),('/login',LoginHandler),('/loginEmail',LoginWithEmail),
    ('/signup',SignupHandler),('/newsfeed',NewsHandler),('/sellers',Sellers),('/show',Show),
    ('/test',TestHandler),('/backend',BackendHandler),('/product',ProductHandler)
], debug=True)
